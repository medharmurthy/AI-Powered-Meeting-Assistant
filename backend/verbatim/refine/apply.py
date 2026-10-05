from __future__ import annotations

import re
from typing import Any, Callable
from verbatim.schemas import Correction, Span


def apply(text: str, corrs: list[Correction]) -> tuple[str, list[Span]]:
    """Apply corrections to segment text left-to-right, skipping overlapping edits.

    Returns the refined text string and a list of Span objects with offsets into the refined text.
    """
    items: list[tuple[int, int, Correction]] = []
    for c in corrs:
        if c.status != "applied":
            continue
        i = text.find(c.original)
        if i < 0:
            i = text.lower().find(c.original.lower())
        if i >= 0:
            items.append((i, i + len(c.original), c))

    items.sort(key=lambda t: t[0])
    out: list[str] = []
    spans: list[Span] = []
    pos = 0
    cur = 0

    for s, e, c in items:
        if s < pos:
            # Overlap: skip this correction
            continue
        # Unchanged slice leading up to correction
        out.append(text[pos:s])
        cur += s - pos

        # Add span offset in refined text
        spans.append(Span(start=cur, end=cur + len(c.corrected), correction_id=c.id))

        # Append replacement
        out.append(c.corrected)
        cur += len(c.corrected)
        pos = e

    out.append(text[pos:])
    return "".join(out), spans


def propagate_corrections(
    segments: list[Any],
    accepted_corrections: list[Correction],
    validator: Callable[[Correction], tuple[bool, str | None]],
    next_id_fn: Callable[[], str],
) -> list[Correction]:
    """Find whole-word occurrences of accepted corrections in other segments and propagate them."""
    # Collect distinct (original.lower(), corrected) pairs
    distinct_pairs: dict[str, tuple[str, str]] = {}
    for c in accepted_corrections:
        if c.status == "applied":
            key = c.original.lower().strip()
            if key not in distinct_pairs:
                distinct_pairs[key] = (c.original, c.corrected)

    propagated: list[Correction] = []

    # Map existing applied corrections by segment_id
    existing_by_seg: dict[int, list[Correction]] = {}
    for c in accepted_corrections:
        existing_by_seg.setdefault(c.segment_id, []).append(c)

    for seg in segments:
        seg_id = getattr(seg, "id", None)
        seg_text = getattr(seg, "text", "")
        if seg_id is None or not seg_text:
            continue

        for orig_key, (orig_pattern, target_replacement) in distinct_pairs.items():
            # Check if this segment already has a correction for this target or original
            existing_corrs = existing_by_seg.get(seg_id, [])
            already_covered = any(
                c.original.lower() == orig_key or c.corrected.lower() == target_replacement.lower()
                for c in existing_corrs
            )
            if already_covered:
                continue

            # Look for whole-word occurrence
            pattern = re.compile(rf"\b{re.escape(orig_pattern)}\b", re.IGNORECASE)
            match = pattern.search(seg_text)
            if match:
                matched_text = match.group(0)
                # Create proposed propagated correction
                prop_corr = Correction(
                    id=next_id_fn(),
                    segment_id=seg_id,
                    original=matched_text,
                    corrected=target_replacement,
                    reason=f"Propagated term '{target_replacement}'",
                    status="applied",
                    source="propagated",
                )
                valid, reason = validator(prop_corr)
                if valid:
                    prop_corr.status = "applied"
                    prop_corr.block_reason = None
                    propagated.append(prop_corr)
                    existing_by_seg.setdefault(seg_id, []).append(prop_corr)
                else:
                    prop_corr.status = "blocked"
                    prop_corr.block_reason = reason
                    propagated.append(prop_corr)

    return propagated
