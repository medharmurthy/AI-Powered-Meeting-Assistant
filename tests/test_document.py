from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeVar
import pytest
from pydantic import BaseModel

from verbatim.document.schemas import (
    ActionsResponse,
    DecisionsResponse,
    MinutesResponse,
    RawActionItem,
    RawDecisionItem,
    RawPossibleTask,
    RawUnresolvedItem,
    SummaryResponse,
    VerifyItemResult,
    VerifyResponse,
)
from verbatim.document.stage import document_meeting
from verbatim.llm.base import LLM
from verbatim.schemas import MinutesTopic, Point, RefinedTranscript, DomainProfile
from verbatim.store import create_run, get_run_dir, load_json, save_json, save_meta

T = TypeVar("T", bound=BaseModel)


class MockDocumenterLLM:
    """Mock LLM returning deterministic structured outputs for each call."""

    def __init__(self):
        self.call_count = 0
        self.unloaded = False

    def structured(
        self,
        *,
        model: str,
        system: str,
        user: str,
        schema: type[T],
        role: str | None = None,
    ) -> T:
        self.call_count += 1

        if schema == SummaryResponse:
            return SummaryResponse(
                title="Orion Architecture & Audit Sync",
                summary="The team met to agree on session cache migration to Redis and audit prep. Database upgrade was postponed.",
                attendees=["Maya", "Priya", "Dan"],
            )

        if schema == MinutesResponse:
            return MinutesResponse(
                topics=[
                    MinutesTopic(
                        title="Session Cache",
                        points=[
                            Point(text="Agreed to migrate session cache to Redis.", segment_ids=[1, 2]),
                        ],
                    ),
                ]
            )

        if schema == DecisionsResponse:
            return DecisionsResponse(
                decisions=[
                    RawDecisionItem(
                        text="Migrate session cache from Memcached to Redis",
                        rationale="Lowers p99 latency",
                        segment_ids=[1, 2],
                        quote="Redis would fix that",
                    ),
                    RawDecisionItem(
                        text="Do not upgrade PostgreSQL to version 16 this quarter",
                        rationale="Risk too high before audit",
                        segment_ids=[5],
                        quote=None,
                    ),
                    # Hallucinated decision with invalid segment IDs
                    RawDecisionItem(
                        text="Rewrite entire backend in Rust",
                        segment_ids=[999],
                    ),
                ],
                unresolved=[
                    RawUnresolvedItem(
                        kind="deferred",
                        text="Move all internal services from REST to gRPC",
                        segment_ids=[3, 4],
                    ),
                ],
            )

        if schema == ActionsResponse:
            return ActionsResponse(
                actions=[
                    RawActionItem(
                        task="Write Terraform module for Redis cluster",
                        owner="Dan",
                        deadline="by Thursday",
                        segment_ids=[6, 7],
                    ),
                    RawActionItem(
                        task="Update OAuth scopes documentation",
                        owner="Priya",
                        deadline=None,
                        segment_ids=[8],
                    ),
                    RawActionItem(
                        task="Rotate staging database credentials",
                        owner="we",  # Generic owner -> should be converted to null
                        deadline="before the audit on the 15th",
                        segment_ids=[9],
                    ),
                ],
                possible_tasks=[
                    RawPossibleTask(
                        text="Look at Grafana dashboards",
                        segment_ids=[10],
                    ),
                ],
            )

        if schema == VerifyResponse:
            return VerifyResponse(
                results=[
                    VerifyItemResult(id="D1", verdict="agreed"),
                    VerifyItemResult(id="D2", verdict="agreed"),
                    VerifyItemResult(id="T1", verdict="committed", owner_stated=True, deadline_stated=True),
                    VerifyItemResult(id="T2", verdict="committed", owner_stated=True, deadline_stated=False),
                    VerifyItemResult(id="T3", verdict="committed", owner_stated=False, deadline_stated=True),
                ]
            )

        raise ValueError(f"Unexpected schema: {schema}")

    def unload(self, model: str) -> None:
        self.unloaded = True

    def available_models(self) -> set[str]:
        return {"gemma3:4b", "gemma3:12b"}


def test_document_meeting_pipeline_flow(tmp_path):
    run_id = create_run(filename="sample_meeting.mp3")

    # Set up sample refined transcript
    refined_data = {
        "segments": [
            {"id": 1, "start": 0.0, "end": 4.0, "text": "On the session cache, Memcached latency is too high."},
            {"id": 2, "start": 4.0, "end": 8.0, "text": "Redis would fix that. It is decided: migrate to Redis."},
            {"id": 3, "start": 8.0, "end": 12.0, "text": "I suggest we move internal services to gRPC."},
            {"id": 4, "start": 12.0, "end": 16.0, "text": "Let us revisit gRPC next sprint."},
            {"id": 5, "start": 16.0, "end": 20.0, "text": "We are not going to upgrade PostgreSQL to version 16 this quarter."},
            {"id": 6, "start": 20.0, "end": 24.0, "text": "Dan, can you write the Terraform module for Redis?"},
            {"id": 7, "start": 24.0, "end": 28.0, "text": "Yes, I will have the Terraform module done by Thursday."},
            {"id": 8, "start": 28.0, "end": 32.0, "text": "Priya, can you update the OAuth scopes documentation?"},
            {"id": 9, "start": 32.0, "end": 36.0, "text": "Someone has to rotate the database credentials before the audit on the 15th."},
            {"id": 10, "start": 36.0, "end": 40.0, "text": "Maybe look at Grafana dashboards if you get time."},
        ],
        "corrections": [],
        "profile": {
            "topic": "Architecture sync",
            "domain": "infrastructure",
            "likely_terms": ["Redis", "PostgreSQL", "gRPC"],
            "names": ["Maya", "Priya", "Dan"],
        },
        "model": "qwen3:8b",
    }
    save_json(run_id, "refined_transcript.json", refined_data)
    save_meta(run_id, {
        "participants": ["Maya", "Priya", "Dan"],
        "filename": "sample_meeting.mp3",
    })

    mock_llm = MockDocumenterLLM()
    record = document_meeting(run_id=run_id, llm_client=mock_llm)

    assert record is not None
    assert record.title == "Orion Architecture & Audit Sync"
    assert "Maya" in record.attendees
    assert mock_llm.unloaded is True

    # Check decisions
    assert len(record.decisions) == 2
    assert record.decisions[0].id == "D1"
    assert "Redis" in record.decisions[0].text
    assert record.decisions[1].id == "D2"
    assert "PostgreSQL" in record.decisions[1].text

    # The Rust decision cited line 999 which did not exist -> should be in dropped
    dropped_texts = [d.text for d in record.dropped]
    assert any("Rust" in t for t in dropped_texts)

    # Check action items
    assert len(record.action_items) == 3
    t1 = [a for a in record.action_items if "Terraform" in a.task][0]
    assert t1.owner == "Dan"
    assert t1.deadline == "by Thursday"

    t2 = [a for a in record.action_items if "OAuth" in a.task][0]
    assert t2.owner == "Priya"
    assert t2.deadline is None  # Unspecified

    t3 = [a for a in record.action_items if "credentials" in a.task][0]
    assert t3.owner is None  # Generic "we" was demoted
    assert t3.deadline == "before the audit on the 15th"

    # Check unresolved
    assert len(record.unresolved) >= 2
    unresolved_texts = [u.text for u in record.unresolved]
    assert any("gRPC" in t for t in unresolved_texts)
    assert any("Grafana" in t for t in unresolved_texts)

    # Verify meeting_record.json on disk
    persisted = load_json(run_id, "meeting_record.json")
    assert persisted is not None
    assert persisted["title"] == record.title
