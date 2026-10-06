from __future__ import annotations

import logging
from pathlib import Path
import re
import time
from typing import Any
import jinja2

from verbatim.config import find_repo_root, get_config
from verbatim.document.grounding import (
    calculate_support,
    deduplicate_items,
    get_context_text,
    validate_deadline,
    validate_owner,
    validate_quote,
)
from verbatim.document.schemas import (
    ActionsResponse,
    DecisionsResponse,
    MinutesResponse,
    SummaryResponse,
)
from verbatim.document.verify import run_verification_pass
from verbatim.errors import PipelineError
from verbatim.llm.base import LLM
from verbatim.llm.ollama_client import OllamaClient
from verbatim.schemas import (
    ActionItem,
    Decision,
    Dropped,
    MeetingRecord,
    MinutesTopic,
    Point,
    Unresolved,
)
from verbatim.store import (
    append_event,
    load_json,
    load_meta,
    save_json,
    save_meta,
)

logger = logging.getLogger("verbatim.document")


def load_doc_template(filename: str) -> jinja2.Template:
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


def format_transcript_lines(segments: list[Any]) -> tuple[str, dict[int, str]]:
    """Format segments into [id] [mm:ss] text and return formatted block plus lookup map."""
    lines: list[str] = []
    lookup: dict[int, str] = {}
    for seg in segments:
        sid = seg.get("id") if isinstance(seg, dict) else seg.id
        start = seg.get("start", 0.0) if isinstance(seg, dict) else seg.start
        text = seg.get("text", "").strip() if isinstance(seg, dict) else seg.text.strip()

        mm = int(start // 60)
        ss = int(start % 60)
        time_str = f"{mm:02d}:{ss:02d}"

        lines.append(f"[{sid}] [{time_str}] {text}")
        lookup[sid] = text

    return "\n".join(lines), lookup


def document_meeting(
    run_id: str,
    llm_client: LLM | None = None,
) -> MeetingRecord:
    """
    Execute Phase 4 documentation stage on refined transcript for run_id:
    Call 1: Summary -> title, summary, attendees
    Call 2: Minutes -> topics and discussion points
    Call 3: Decisions -> agreed decisions and unresolved discussions
    Call 4: Actions -> committed tasks with owners and deadlines
    Call 5: Verification -> self-consistency and grounding checks
    """
    cfg = get_config()
    meta = load_meta(run_id) or {}
    participants: list[str] = meta.get("participants", [])

    # Load transcript (prefer refined_transcript.json, fallback to raw_transcript.json)
    transcript_data = load_json(run_id, "refined_transcript.json")
    if not transcript_data:
        transcript_data = load_json(run_id, "raw_transcript.json")
    if not transcript_data or "segments" not in transcript_data:
        raise PipelineError(
            code="INTERNAL",
            detail=f"No transcript found for run {run_id} to document",
        )

    segments = transcript_data["segments"]
    if not segments:
        raise PipelineError(
            code="INTERNAL",
            detail=f"Transcript for run {run_id} has 0 segments",
        )

    transcript_block, segments_by_id = format_transcript_lines(segments)
    valid_segment_ids = set(segments_by_id.keys())

    # Initialize LLM client
    if llm_client is None:
        llm_client = OllamaClient(
            host=cfg.llm.host,
            temperature=cfg.llm.temperature,
            seed=cfg.llm.seed,
            timeout_s=cfg.llm.timeout_s,
        )

    doc_model = cfg.active_profile_config.documenter.model
    append_event(
        run_id,
        "stage.started",
        {"stage": "document", "model": doc_model},
    )
    t_stage_start = time.time()

    # Load templates
    tmpl_system = load_doc_template("doc_system.v1.md")
    tmpl_summary = load_doc_template("doc_summary.v1.md")
    tmpl_minutes = load_doc_template("doc_minutes.v1.md")
    tmpl_decisions = load_doc_template("doc_decisions.v1.md")
    tmpl_actions = load_doc_template("doc_actions.v1.md")
    tmpl_verify = load_doc_template("doc_verify.v1.md")

    # Base prompt prefix shared across calls for Ollama KV caching
    system_prompt = tmpl_system.render().strip()
    prefix_prompt = f"Transcript:\n{transcript_block}\n\n"

    dropped_items: list[Dropped] = []

    # -------------------------------------------------------------
    # Call 1: Summary
    # -------------------------------------------------------------
    logger.info("Executing Call 1: Summary...")
    append_event(
        run_id,
        "stage.progress",
        {"stage": "document", "done": 1, "total": 5, "label": "Writing summary"},
    )
    task_summary = tmpl_summary.render(participants=", ".join(participants))
    user_prompt_1 = prefix_prompt + task_summary

    summary_resp: SummaryResponse = llm_client.structured(
        model=doc_model,
        system=system_prompt,
        user=user_prompt_1,
        schema=SummaryResponse,
        role="documenter",
    )
    append_event(
        run_id,
        "record.section",
        {"section": "summary", "data": summary_resp.model_dump()},
    )

    # -------------------------------------------------------------
    # Call 2: Minutes
    # -------------------------------------------------------------
    logger.info("Executing Call 2: Minutes...")
    append_event(
        run_id,
        "stage.progress",
        {"stage": "document", "done": 2, "total": 5, "label": "Writing minutes"},
    )
    task_minutes = tmpl_minutes.render()
    user_prompt_2 = prefix_prompt + task_minutes

    minutes_resp: MinutesResponse = llm_client.structured(
        model=doc_model,
        system=system_prompt,
        user=user_prompt_2,
        schema=MinutesResponse,
        role="documenter",
    )

    # Ground minutes: filter segment_ids and discard points with no valid lines
    grounded_topics: list[MinutesTopic] = []
    for topic in minutes_resp.topics:
        grounded_points: list[Point] = []
        for p in topic.points:
            valid_sids = [sid for sid in p.segment_ids if sid in valid_segment_ids]
            if not valid_sids:
                dropped_items.append(
                    Dropped(
                        section="minutes",
                        text=p.text,
                        reason="Point cited non-existent or invalid segment IDs",
                    )
                )
                continue
            grounded_points.append(Point(text=p.text, segment_ids=valid_sids))
        if grounded_points:
            grounded_topics.append(MinutesTopic(title=topic.title, points=grounded_points))

    append_event(
        run_id,
        "record.section",
        {"section": "minutes", "data": [t.model_dump() for t in grounded_topics]},
    )

    # -------------------------------------------------------------
    # Call 3: Decisions & Unresolved
    # -------------------------------------------------------------
    logger.info("Executing Call 3: Decisions...")
    append_event(
        run_id,
        "stage.progress",
        {"stage": "document", "done": 3, "total": 5, "label": "Extracting decisions"},
    )
    task_decisions = tmpl_decisions.render()
    user_prompt_3 = prefix_prompt + task_decisions

    decisions_resp: DecisionsResponse = llm_client.structured(
        model=doc_model,
        system=system_prompt,
        user=user_prompt_3,
        schema=DecisionsResponse,
        role="documenter",
    )

    # Ground decisions
    candidate_decisions: list[Decision] = []
    for idx, d in enumerate(decisions_resp.decisions):
        valid_sids = [sid for sid in d.segment_ids if sid in valid_segment_ids]
        if not valid_sids:
            dropped_items.append(
                Dropped(
                    section="decisions",
                    text=d.text,
                    reason="Decision cited no valid source lines",
                )
            )
            continue

        ctx = get_context_text(valid_sids, segments_by_id, window=1)
        support = calculate_support(d.text, ctx)
        if support < cfg.document.support_threshold:
            dropped_items.append(
                Dropped(
                    section="decisions",
                    text=d.text,
                    reason=f"Support score {support:.2f} below threshold {cfg.document.support_threshold}",
                )
            )
            continue

        validated_quote = validate_quote(d.quote, valid_sids, segments_by_id)
        candidate_decisions.append(
            Decision(
                id=f"D{idx + 1}",
                text=d.text,
                rationale=d.rationale,
                segment_ids=valid_sids,
                quote=validated_quote,
            )
        )

    # Ground unresolved
    candidate_unresolved: list[Unresolved] = []
    for idx, u in enumerate(decisions_resp.unresolved):
        valid_sids = [sid for sid in u.segment_ids if sid in valid_segment_ids]
        if not valid_sids:
            continue
        candidate_unresolved.append(
            Unresolved(
                id=f"U{idx + 1}",
                kind=u.kind,
                text=u.text,
                segment_ids=valid_sids,
            )
        )

    # Deduplicate decisions
    candidate_decisions = deduplicate_items(
        candidate_decisions,
        text_extractor=lambda x: x.text,
        segment_ids_extractor=lambda x: x.segment_ids,
    )
    # Re-index decisions stably: D1, D2...
    for i, d in enumerate(candidate_decisions):
        d.id = f"D{i + 1}"

    append_event(
        run_id,
        "record.section",
        {
            "section": "decisions",
            "data": {
                "decisions": [d.model_dump() for d in candidate_decisions],
                "unresolved": [u.model_dump() for u in candidate_unresolved],
            },
        },
    )

    # -------------------------------------------------------------
    # Call 4: Action Items & Possible Tasks
    # -------------------------------------------------------------
    logger.info("Executing Call 4: Actions...")
    append_event(
        run_id,
        "stage.progress",
        {"stage": "document", "done": 4, "total": 5, "label": "Extracting action items"},
    )
    task_actions = tmpl_actions.render()
    user_prompt_4 = prefix_prompt + task_actions

    actions_resp: ActionsResponse = llm_client.structured(
        model=doc_model,
        system=system_prompt,
        user=user_prompt_4,
        schema=ActionsResponse,
        role="documenter",
    )

    # Ground action items
    candidate_actions: list[ActionItem] = []
    for idx, a in enumerate(actions_resp.actions):
        valid_sids = [sid for sid in a.segment_ids if sid in valid_segment_ids]
        if not valid_sids:
            dropped_items.append(
                Dropped(
                    section="action_items",
                    text=a.task,
                    reason="Task cited no valid source lines",
                )
            )
            continue

        ctx = get_context_text(valid_sids, segments_by_id, window=1)
        support = calculate_support(a.task, ctx)
        if support < cfg.document.support_threshold:
            dropped_items.append(
                Dropped(
                    section="action_items",
                    text=a.task,
                    reason=f"Support score {support:.2f} below threshold {cfg.document.support_threshold}",
                )
            )
            continue

        owner_val, owner_reason = validate_owner(
            a.owner,
            valid_sids,
            segments_by_id,
            participants,
            owner_window=cfg.document.owner_window,
        )
        if a.owner and owner_reason:
            dropped_items.append(
                Dropped(
                    section="action_items",
                    text=f"Task '{a.task}': owner '{a.owner}'",
                    reason=owner_reason,
                )
            )

        deadline_val, deadline_reason = validate_deadline(
            a.deadline,
            valid_sids,
            segments_by_id,
            deadline_window=cfg.document.deadline_window,
        )
        if a.deadline and deadline_reason:
            dropped_items.append(
                Dropped(
                    section="action_items",
                    text=f"Task '{a.task}': deadline '{a.deadline}'",
                    reason=deadline_reason,
                )
            )

        validated_quote = validate_quote(a.quote, valid_sids, segments_by_id)

        candidate_actions.append(
            ActionItem(
                id=f"T{idx + 1}",
                task=a.task,
                owner=owner_val,
                deadline=deadline_val,
                segment_ids=valid_sids,
                quote=validated_quote,
            )
        )

    # Add possible tasks into unresolved
    for pt in actions_resp.possible_tasks:
        valid_sids = [sid for sid in pt.segment_ids if sid in valid_segment_ids]
        if valid_sids:
            candidate_unresolved.append(
                Unresolved(
                    id=f"U{len(candidate_unresolved) + 1}",
                    kind="possible_task",
                    text=pt.text,
                    segment_ids=valid_sids,
                )
            )

    # Deduplicate actions
    candidate_actions = deduplicate_items(
        candidate_actions,
        text_extractor=lambda x: x.task,
        segment_ids_extractor=lambda x: x.segment_ids,
    )
    for i, a in enumerate(candidate_actions):
        a.id = f"T{i + 1}"

    # -------------------------------------------------------------
    # Call 5: Verification Pass (if configured)
    # -------------------------------------------------------------
    if cfg.document.verify_pass:
        logger.info("Executing Call 5: Verification pass...")
        append_event(
            run_id,
            "stage.progress",
            {"stage": "document", "done": 5, "total": 5, "label": "Checking claims"},
        )
        candidate_decisions, candidate_actions, candidate_unresolved, dropped_items = (
            run_verification_pass(
                decisions=candidate_decisions,
                actions=candidate_actions,
                unresolved=candidate_unresolved,
                dropped=dropped_items,
                segments_by_id=segments_by_id,
                llm_client=llm_client,
                model_name=doc_model,
                render_verify_prompt_fn=tmpl_verify.render,
            )
        )

    # Re-index all IDs cleanly after verification
    for i, d in enumerate(candidate_decisions):
        d.id = f"D{i + 1}"
    for i, a in enumerate(candidate_actions):
        a.id = f"T{i + 1}"
    for i, u in enumerate(candidate_unresolved):
        u.id = f"U{i + 1}"

    # -------------------------------------------------------------
    # Assemble MeetingRecord
    # -------------------------------------------------------------
    refiner_model = meta.get("refiner_model") or cfg.active_profile_config.refiner.model
    stt_model = meta.get("stt_model") or cfg.active_profile_config.stt.model
    source_filename = meta.get("filename", "meeting_recording")

    record = MeetingRecord(
        schema_version="1.0",
        title=summary_resp.title,
        summary=summary_resp.summary,
        attendees=summary_resp.attendees,
        minutes=grounded_topics,
        decisions=candidate_decisions,
        unresolved=candidate_unresolved,
        action_items=candidate_actions,
        models={
            "stt": stt_model,
            "refiner": refiner_model,
            "documenter": doc_model,
        },
        source_file=source_filename,
        generated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        dropped=dropped_items,
    )

    # Persist meeting_record.json
    save_json(run_id, "meeting_record.json", record.model_dump())

    t_stage_elapsed = time.time() - t_stage_start
    meta["documenter_model"] = doc_model
    meta["timings"] = meta.get("timings", {})
    meta["timings"]["document"] = round(t_stage_elapsed, 2)
    save_meta(run_id, meta)

    append_event(
        run_id,
        "stage.done",
        {"stage": "document", "seconds": round(t_stage_elapsed, 2)},
    )

    # Explicit memory cleanup
    if cfg.llm.unload_after_stage:
        try:
            llm_client.unload(doc_model)
        except Exception as e:
            logger.warning("Failed to unload documenter model: %s", e)

    return record
