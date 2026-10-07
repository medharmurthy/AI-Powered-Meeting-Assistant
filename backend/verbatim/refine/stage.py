from __future__ import annotations

import logging
import math
import re
import time
from typing import Any
import jinja2

from verbatim.config import find_repo_root, get_config
from verbatim.errors import PipelineError
from verbatim.llm.base import LLM
from verbatim.llm.ollama_client import OllamaClient
from verbatim.refine.apply import apply, propagate_corrections
from verbatim.refine.guardrails import validate_proposal
from verbatim.refine.hints import hints
from verbatim.schemas import (
    Correction,
    DomainProfile,
    ProposalList,
    RawTranscript,
    RefinedSegment,
    RefinedTranscript,
)
from verbatim.store import (
    append_event,
    load_json,
    load_meta,
    save_json,
    save_meta,
)

logger = logging.getLogger("verbatim.refine")


def load_prompt_template(filename: str) -> jinja2.Template:
    """Load a Jinja2 prompt template from the prompts directory."""
    prompts_dir = find_repo_root() / "prompts"
    template_path = prompts_dir / filename
    if not template_path.exists():
        raise PipelineError(
            code="INTERNAL",
            detail=f"Prompt template '{filename}' not found at {template_path}",
        )
    with open(template_path, "r", encoding="utf-8") as f:
        return jinja2.Template(f.read())


def split_system_user_sections(rendered_text: str) -> tuple[str, str]:
    """Split rendered markdown prompt containing SYSTEM and USER blocks into system and user strings."""
    parts = re.split(r"(?:^|\n)USER\s*\n", rendered_text, maxsplit=1)
    if len(parts) == 2:
        system = re.sub(r"^SYSTEM\s*\n", "", parts[0]).strip()
        user = parts[1].strip()
        return system, user
    return "", rendered_text.strip()


def build_transcript_excerpt(segments: list[Any]) -> str:
    """Build transcript excerpt: full transcript if <= ~5k tokens, else first ~3k tokens + 4 sampled chunks."""
    all_lines = [f"[{s.id}] {s.text}" for s in segments]
    total_words = sum(len(s.text.split()) for s in segments)

    # Estimate tokens: 1 word is approximately 1.3 tokens
    if total_words * 1.3 <= 5000:
        return "\n".join(all_lines)

    # First ~2300 words
    first_chunk_lines: list[str] = []
    word_count = 0
    cutoff_idx = 0
    for idx, s in enumerate(segments):
        w = len(s.text.split())
        if word_count + w > 2300:
            cutoff_idx = idx
            break
        first_chunk_lines.append(f"[{s.id}] {s.text}")
        word_count += w

    remaining_segments = segments[cutoff_idx:]
    sample_lines: list[str] = []
    if remaining_segments:
        # Pick 4 evenly spaced 500-word blocks from remaining
        chunk_step = len(remaining_segments) // 4
        for i in range(4):
            start = i * chunk_step
            chunk = remaining_segments[start : start + min(chunk_step, 15)]
            sample_lines.extend(f"[{s.id}] {s.text}" for s in chunk)

    return "\n".join(first_chunk_lines + ["..."] + sample_lines)


def refine_transcript(
    run_id: str,
    llm_client: LLM | None = None,
) -> RefinedTranscript:
    """Execute Phase 3 refinement stage on raw transcript for run_id."""
    cfg = get_config()
    raw_data = load_json(run_id, "raw_transcript.json")
    if not raw_data:
        raise PipelineError(
            code="INTERNAL",
            detail=f"raw_transcript.json not found for run {run_id}",
        )

    raw_transcript = RawTranscript(**raw_data)
    meta = load_meta(run_id)
    glossary: list[str] = meta.get("glossary", [])
    participants: list[str] = meta.get("participants", [])

    model_name = cfg.active_profile_config.refiner.model
    append_event(
        run_id,
        "stage.started",
        {"stage": "refine", "model": model_name},
    )
    save_meta(run_id, {"stage": "refine"})
    t0 = time.time()

    llm = llm_client or OllamaClient(host=cfg.llm.host)

    try:
        # =========================================================================
        # Step A: Domain profile
        # =========================================================================
        profile_template = load_prompt_template("refine_profile.v1.md")
        excerpt_text = build_transcript_excerpt(raw_transcript.segments)

        rendered_profile_prompt = profile_template.render(
            participants=", ".join(participants) if participants else "",
            glossary=", ".join(glossary) if glossary else "",
            excerpt=excerpt_text,
        )
        sys_prof, user_prof = split_system_user_sections(rendered_profile_prompt)

        domain_profile = llm.structured(
            model=model_name,
            system=sys_prof,
            user=user_prof,
            schema=DomainProfile,
            role="refiner",
        )

        # Merge user glossary terms into likely_terms and participants into names
        existing_terms_lower = {t.lower() for t in domain_profile.likely_terms}
        for g in glossary:
            if g.lower() not in existing_terms_lower:
                domain_profile.likely_terms.append(g)
                existing_terms_lower.add(g.lower())

        existing_names_lower = {n.lower() for n in domain_profile.names}
        for p in participants:
            if p.lower() not in existing_names_lower:
                domain_profile.names.append(p)
                existing_names_lower.add(p.lower())

        append_event(run_id, "refine.profile", domain_profile.model_dump())

        # =========================================================================
        # Step B: Hints
        # =========================================================================
        candidate_hints = hints(
            raw_transcript.segments,
            domain_profile.likely_terms,
            min_score=cfg.refine.hint_min_score,
        )
        hints_by_seg: dict[int, list[Any]] = {}
        for h in candidate_hints:
            hints_by_seg.setdefault(h.segment_id, []).append(h)

        # =========================================================================
        # Step C: Windowed Corrections & Step D: Guardrails
        # =========================================================================
        corrections_template = load_prompt_template("refine_corrections.v1.md")
        segments = raw_transcript.segments
        raw_segments_map = {s.id: s.text for s in segments}

        window_size = cfg.refine.window
        context_size = cfg.refine.context
        total_chunks = max(1, math.ceil(len(segments) / window_size))

        corr_counter = 0

        def next_corr_id() -> str:
            nonlocal corr_counter
            corr_counter += 1
            return f"c{corr_counter}"

        all_corrections: list[Correction] = []

        for chunk_idx in range(total_chunks):
            start_idx = chunk_idx * window_size
            end_idx = min(len(segments), (chunk_idx + 1) * window_size)

            editable_segs = segments[start_idx:end_idx]
            editable_ids = {s.id for s in editable_segs}

            ctx_before = segments[max(0, start_idx - context_size) : start_idx]
            ctx_after = segments[end_idx : min(len(segments), end_idx + context_size)]

            # Build lines
            lines_list: list[str] = []
            window_hints: list[Any] = []

            for s in ctx_before:
                lines_list.append(f"[{s.id}] CONTEXT: {s.text}")
            for s in editable_segs:
                lines_list.append(f"[{s.id}] {s.text}")
                window_hints.extend(hints_by_seg.get(s.id, []))
            for s in ctx_after:
                lines_list.append(f"[{s.id}] CONTEXT: {s.text}")

            # Deduplicate hints for this window, prioritising highest confidence, max 15 per chunk
            seen_hint_keys = set()
            dedup_hints = []
            for h in sorted(window_hints, key=lambda x: -x.score):
                key = (h.segment_id, h.heard.lower(), h.term.lower())
                if key not in seen_hint_keys:
                    seen_hint_keys.add(key)
                    dedup_hints.append(h)
                    if len(dedup_hints) >= 15:
                        break

            rendered_corr_prompt = corrections_template.render(
                profile=domain_profile,
                terms=", ".join(domain_profile.likely_terms),
                participants=", ".join(domain_profile.names),
                hints=dedup_hints,
                lines="\n".join(lines_list),
            )
            sys_corr, user_corr = split_system_user_sections(rendered_corr_prompt)

            # Call LLM #1
            proposal_list = llm.structured(
                model=model_name,
                system=sys_corr,
                user=user_corr,
                schema=ProposalList,
                role="refiner",
            )

            # Emit stage.progress per window
            label = f"Checking terms, chunk {chunk_idx + 1} of {total_chunks}"
            append_event(
                run_id,
                "stage.progress",
                {
                    "stage": "refine",
                    "done": chunk_idx + 1,
                    "total": total_chunks,
                    "label": label,
                },
            )

            # Step D: Apply Guardrails to every proposed correction
            for prop in proposal_list.corrections:
                cid = next_corr_id()
                is_valid, block_reason = validate_proposal(
                    prop,
                    raw_segments_map=raw_segments_map,
                    editable_segment_ids=editable_ids,
                    participants=domain_profile.names,
                    max_original_words=cfg.refine.max_original_words,
                )

                status = "applied" if is_valid else "blocked"
                corr_item = Correction(
                    id=cid,
                    segment_id=prop.segment_id,
                    original=prop.original,
                    corrected=prop.corrected,
                    reason=prop.reason,
                    status=status,
                    block_reason=block_reason,
                    source="model",
                )
                all_corrections.append(corr_item)

                if is_valid:
                    append_event(run_id, "refine.correction", corr_item.model_dump())
                else:
                    append_event(run_id, "refine.blocked", corr_item.model_dump())

        # =========================================================================
        # Step F: Propagation
        # =========================================================================
        accepted_corrs = [c for c in all_corrections if c.status == "applied"]

        def prop_validator(c: Correction) -> tuple[bool, str | None]:
            return validate_proposal(
                c,
                raw_segments_map=raw_segments_map,
                editable_segment_ids=None,
                participants=domain_profile.names,
                max_original_words=cfg.refine.max_original_words,
            )

        propagated_items = propagate_corrections(
            segments=segments,
            accepted_corrections=accepted_corrs,
            validator=prop_validator,
            next_id_fn=next_corr_id,
        )

        for p_corr in propagated_items:
            all_corrections.append(p_corr)
            if p_corr.status == "applied":
                append_event(run_id, "refine.correction", p_corr.model_dump())
            else:
                append_event(run_id, "refine.blocked", p_corr.model_dump())

        # =========================================================================
        # Step E: Apply spans to segments
        # =========================================================================
        refined_segments: list[RefinedSegment] = []
        for s in segments:
            seg_corrs = [
                c for c in all_corrections if c.segment_id == s.id and c.status == "applied"
            ]
            refined_text, spans = apply(s.text, seg_corrs)
            refined_segments.append(
                RefinedSegment(
                    id=s.id,
                    start=s.start,
                    end=s.end,
                    text=refined_text,
                    spans=spans,
                )
            )

        refined_transcript = RefinedTranscript(
            segments=refined_segments,
            corrections=all_corrections,
            profile=domain_profile,
            model=model_name,
        )

        save_json(run_id, "refined_transcript.json", refined_transcript)

        elapsed = round(time.time() - t0, 2)
        timings = meta.get("timings", {})
        timings["refine"] = elapsed
        models_meta = meta.get("models", {})
        models_meta["refiner"] = model_name
        save_meta(run_id, {"timings": timings, "models": models_meta})

        append_event(
            run_id,
            "refine.done",
            {
                "segments": [s.model_dump() for s in refined_segments],
                "corrections": [c.model_dump() for c in all_corrections],
            },
        )
        append_event(
            run_id,
            "stage.done",
            {"stage": "refine", "seconds": elapsed},
        )

        return refined_transcript

    finally:
        # Ensure refiner model is explicitly unloaded from VRAM
        llm.unload(model_name)
