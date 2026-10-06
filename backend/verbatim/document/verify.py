from __future__ import annotations

import logging
from typing import Any

from verbatim.config import get_config
from verbatim.document.schemas import VerifyItemResult, VerifyResponse
from verbatim.llm.base import LLM
from verbatim.schemas import ActionItem, Decision, Dropped, Unresolved

logger = logging.getLogger("verbatim.document.verify")


def run_verification_pass(
    decisions: list[Decision],
    actions: list[ActionItem],
    unresolved: list[Unresolved],
    dropped: list[Dropped],
    segments_by_id: dict[int, str],
    llm_client: LLM,
    model_name: str,
    render_verify_prompt_fn: Any,
) -> tuple[list[Decision], list[ActionItem], list[Unresolved], list[Dropped]]:
    """
    Execute Call 5 (doc_verify) across all candidate decisions and actions.
    Applies verdicts:
    - unsupported -> drop to dropped list
    - decision proposal_only -> move to unresolved(kind="proposal")
    - action tentative -> move to unresolved(kind="possible_task")
    - owner_stated=False -> owner = None
    - deadline_stated=False -> deadline = None
    """
    if not decisions and not actions:
        return decisions, actions, unresolved, dropped

    items_to_verify: list[dict[str, Any]] = []

    # Prepare decision items for prompt
    for d in decisions:
        expanded_lines: list[str] = []
        for sid in d.segment_ids:
            for offset in range(-2, 3):
                target_id = sid + offset
                if target_id in segments_by_id:
                    expanded_lines.append(f"[{target_id}] {segments_by_id[target_id]}")
        unique_lines = list(dict.fromkeys(expanded_lines))
        items_to_verify.append({
            "id": d.id,
            "kind": "decision",
            "text": d.text,
            "owner": None,
            "deadline": None,
            "lines": "\n".join(unique_lines),
        })

    # Prepare action items for prompt
    for a in actions:
        expanded_lines = []
        for sid in a.segment_ids:
            for offset in range(-2, 3):
                target_id = sid + offset
                if target_id in segments_by_id:
                    expanded_lines.append(f"[{target_id}] {segments_by_id[target_id]}")
        unique_lines = list(dict.fromkeys(expanded_lines))
        items_to_verify.append({
            "id": a.id,
            "kind": "task",
            "text": a.task,
            "owner": a.owner,
            "deadline": a.deadline,
            "lines": "\n".join(unique_lines),
        })

    # Render prompt
    rendered_user = render_verify_prompt_fn({"items": items_to_verify})

    try:
        verify_resp: VerifyResponse = llm_client.structured(
            model=model_name,
            system="Verify candidate decisions and tasks strictly against cited context. Return JSON only.",
            user=rendered_user,
            schema=VerifyResponse,
            role="documenter",
        )
    except Exception as e:
        logger.warning("Verification call failed; continuing with unverified candidates: %s", e)
        return decisions, actions, unresolved, dropped

    verdict_by_id = {r.id: r for r in verify_resp.results}

    verified_decisions: list[Decision] = []
    for d in decisions:
        res = verdict_by_id.get(d.id)
        if not res:
            verified_decisions.append(d)
            continue

        if res.verdict == "unsupported":
            dropped.append(
                Dropped(
                    section="decisions",
                    text=d.text,
                    reason="Verification model determined item is unsupported by cited lines",
                )
            )
        elif res.verdict == "proposal_only":
            unresolved.append(
                Unresolved(
                    id=f"U{len(unresolved) + 1}",
                    kind="proposal",
                    text=d.text,
                    segment_ids=d.segment_ids,
                )
            )
            dropped.append(
                Dropped(
                    section="decisions",
                    text=d.text,
                    reason="Verification model demoted agreed decision to proposal",
                )
            )
        else:  # "agreed"
            verified_decisions.append(d)

    verified_actions: list[ActionItem] = []
    for a in actions:
        res = verdict_by_id.get(a.id)
        if not res:
            verified_actions.append(a)
            continue

        if res.verdict == "unsupported":
            dropped.append(
                Dropped(
                    section="action_items",
                    text=a.task,
                    reason="Verification model determined task is unsupported by cited lines",
                )
            )
        elif res.verdict == "tentative":
            unresolved.append(
                Unresolved(
                    id=f"U{len(unresolved) + 1}",
                    kind="possible_task",
                    text=a.task,
                    segment_ids=a.segment_ids,
                )
            )
            dropped.append(
                Dropped(
                    section="action_items",
                    text=a.task,
                    reason="Verification model demoted task to possible_task (tentative commitment)",
                )
            )
        else:  # "committed"
            final_owner = a.owner if res.owner_stated else None
            final_deadline = a.deadline if res.deadline_stated else None
            if a.owner and not res.owner_stated:
                dropped.append(
                    Dropped(
                        section="action_items",
                        text=f"Task '{a.task}': owner '{a.owner}'",
                        reason="Verification pass determined owner was not stated in speech",
                    )
                )
            if a.deadline and not res.deadline_stated:
                dropped.append(
                    Dropped(
                        section="action_items",
                        text=f"Task '{a.task}': deadline '{a.deadline}'",
                        reason="Verification pass determined deadline was not stated in speech",
                    )
                )
            verified_actions.append(
                ActionItem(
                    id=a.id,
                    task=a.task,
                    owner=final_owner,
                    deadline=final_deadline,
                    segment_ids=a.segment_ids,
                    quote=a.quote,
                )
            )

    return verified_decisions, verified_actions, unresolved, dropped
