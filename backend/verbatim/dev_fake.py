from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
import time
from typing import Any

from verbatim.export.exporter import export_all_run_files
from verbatim.schemas import (
    ActionItem,
    Correction,
    Decision,
    DomainProfile,
    MeetingRecord,
    MinutesTopic,
    Point,
    RawTranscript,
    RefinedSegment,
    RefinedTranscript,
    Segment,
    Span,
    Unresolved,
    Word,
)
from verbatim.store import (
    append_event,
    get_run_dir,
    load_meta,
    save_json,
    save_meta,
)

logger = logging.getLogger("verbatim.dev_fake")

FAKE_RAW_SEGMENTS = [
    Segment(id=0, start=0.0, end=2.4, text="Okay, let's get started. Thanks for joining, Priya and Dan.", words=[]),
    Segment(id=1, start=2.5, end=6.8, text="Three things today: the session cache, the gRPC question, and audit prep.", words=[]),
    Segment(id=2, start=7.0, end=14.2, text="On the session cache, we're still on Memcatch, and p99 latency on login is around 340 milliseconds.", words=[]),
    Segment(id=3, start=14.5, end=18.0, text="Our SLA says under 250 milliseconds. Redis would fix that.", words=[]),
    Segment(id=4, start=18.2, end=24.0, text="In staging we saw p99 drop to about 90 milliseconds. Any objections to moving the session cache to Redis?", words=[]),
    Segment(id=5, start=24.2, end=26.0, text="None from me. Same, none.", words=[]),
    Segment(id=6, start=26.2, end=32.5, text="Okay, then it's decided. We migrate the session cache from Memcatch to Redis.", words=[]),
    Segment(id=7, start=33.0, end=39.5, text="Dan, can you write the Terraform module for the Redis cluster? Yes, I'll have the Terraform module done by Thursday.", words=[]),
    Segment(id=8, start=40.0, end=47.2, text="Great. We'll roll it out on the Kubernetes staging cluster first with a canary deployment, 5 percent of traffic.", words=[]),
    Segment(id=9, start=47.5, end=54.8, text="Sounds right. I'd also suggest we move all internal services from REST to gRPC. That would cut overhead.", words=[]),
    Segment(id=10, start=55.0, end=62.0, text="I don't want to decide that today. Let's revisit gRPC next sprint, once we have numbers. Fine by me.", words=[]),
    Segment(id=11, start=62.5, end=69.8, text="On post-GIR SQL, we are not going to upgrade to version 16 this quarter. The risk is too high before the audit.", words=[]),
    Segment(id=12, start=70.0, end=75.5, text="Agreed. Right, the upgrade waits until next quarter.", words=[]),
    Segment(id=13, start=76.0, end=82.2, text="Priya, can you update the OOFscopes documentation? Sure, I'll take that. No date yet.", words=[]),
    Segment(id=14, start=83.0, end=90.0, text="Now audit prep. The audit is on the 15th. Someone has to rotate the staging database credentials before then.", words=[]),
    Segment(id=15, start=90.5, end=96.0, text="Yeah, that needs doing. Okay, I'll leave that open for now. We need to work out who has time.", words=[]),
    Segment(id=16, start=96.5, end=102.0, text="Dan, maybe you could also look at the Grafana dashboards if you get time. We'll see.", words=[]),
    Segment(id=17, start=102.5, end=115.5, text="Last thing, we have 12,000 dollars approved for the Redis cluster, and we must not exceed that. Understood. Thanks everyone.", words=[]),
]

FAKE_CORRECTIONS = [
    Correction(
        id="c1",
        segment_id=2,
        original="Memcatch",
        corrected="Memcached",
        reason="Misheard Memcached",
        status="applied",
    ),
    Correction(
        id="c2",
        segment_id=6,
        original="Memcatch",
        corrected="Memcached",
        reason="Misheard Memcached",
        status="applied",
        source="propagated",
    ),
    Correction(
        id="c3",
        segment_id=11,
        original="post-GIR SQL",
        corrected="PostgreSQL",
        reason="Misheard PostgreSQL",
        status="applied",
    ),
    Correction(
        id="c4",
        segment_id=13,
        original="OOFscopes",
        corrected="OAuth scopes",
        reason="Misheard OAuth scopes",
        status="applied",
    ),
]

FAKE_BLOCKED = Correction(
    id="c5",
    segment_id=3,
    original="250",
    corrected="300",
    reason="Attempted number change",
    status="blocked",
    block_reason="Would change a number",
)

FAKE_PROFILE = DomainProfile(
    topic="Infrastructure architecture, database migration, and security audit readiness",
    domain="backend infrastructure",
    likely_terms=["Redis", "Memcached", "Kubernetes", "PostgreSQL", "OAuth", "Terraform", "gRPC", "Grafana", "Kafka"],
    names=["Maya", "Priya", "Dan"],
)

FAKE_RECORD = MeetingRecord(
    schema_version="1.0",
    title="Orion payments weekly sync",
    summary="The team met to review backend latency, internal RPC proposals, and upcoming audit preparations. They confirmed migrating the session cache to Redis to address login latency, while postponing the gRPC migration and PostgreSQL 16 upgrade. Dan committed to delivering the Redis Terraform module by Thursday, while database credential rotation remains unassigned.",
    attendees=["Maya", "Priya", "Dan"],
    minutes=[
        MinutesTopic(
            title="Session Cache Migration",
            points=[
                Point(text="Current Memcached setup exhibits p99 login latency of 340ms, exceeding the 250ms SLA.", segment_ids=[2, 3]),
                Point(text="Staging tests showed Redis reduced p99 latency to 90ms.", segment_ids=[4]),
                Point(text="The group unanimously agreed to migrate the session cache from Memcached to Redis.", segment_ids=[4, 5, 6]),
            ],
        ),
        MinutesTopic(
            title="Service Architecture & Upgrades",
            points=[
                Point(text="Proposal to migrate REST services to gRPC deferred to next sprint pending metrics.", segment_ids=[9, 10]),
                Point(text="PostgreSQL 16 upgrade postponed to next quarter to mitigate pre-audit stability risk.", segment_ids=[11, 12]),
            ],
        ),
        MinutesTopic(
            title="Audit Preparation & Operations",
            points=[
                Point(text="Priya volunteered to update OAuth scopes documentation without a firm deadline.", segment_ids=[13]),
                Point(text="Staging database credentials must be rotated before the audit on the 15th.", segment_ids=[14, 15]),
            ],
        ),
    ],
    decisions=[
        Decision(
            id="D1",
            text="Migrate the session cache from Memcached to Redis",
            rationale="Reduces p99 login latency from 340ms to 90ms, meeting the 250ms SLA",
            segment_ids=[4, 5, 6],
            quote="We migrate the session cache from Memcached to Redis.",
        ),
        Decision(
            id="D2",
            text="Do not upgrade PostgreSQL to version 16 this quarter",
            rationale="High operational risk prior to the upcoming audit",
            segment_ids=[11, 12],
            quote="we are not going to upgrade to version sixteen this quarter",
        ),
    ],
    unresolved=[
        Unresolved(
            id="U1",
            kind="deferred",
            text="Migrate internal services from REST to gRPC",
            segment_ids=[9, 10],
        ),
        Unresolved(
            id="U2",
            kind="possible_task",
            text="Review Grafana dashboards",
            segment_ids=[16],
        ),
    ],
    action_items=[
        ActionItem(
            id="T1",
            task="Write Terraform module for the Redis cluster",
            owner="Dan",
            deadline="by Thursday",
            segment_ids=[7],
            quote="I'll have the Terraform module done by Thursday.",
        ),
        ActionItem(
            id="T2",
            task="Update OAuth scopes documentation",
            owner="Priya",
            deadline=None,
            segment_ids=[13],
            quote="Sure, I'll take that.",
        ),
        ActionItem(
            id="T3",
            task="Rotate staging database credentials",
            owner=None,
            deadline="before the audit on the 15th",
            segment_ids=[14, 15],
            quote="Someone has to rotate the staging database credentials before then.",
        ),
    ],
    models={"stt": "distil-large-v3", "refiner": "qwen3:8b", "documenter": "gemma3:12b"},
    source_file="sample_meeting.mp3",
    generated_at="2026-10-06T18:00:00Z",
    dropped=[],
)


def run_fake_pipeline(run_id: str, from_stage: str = "ingest", step_delay: float = 0.05) -> None:
    """Replay a rich, realistic pipeline run for UI development without GPU."""
    run_dir = get_run_dir(run_id, must_exist=True)
    meta = load_meta(run_id) or {}

    meta["fake"] = True
    meta["title"] = "Orion payments weekly sync"
    meta["status"] = "running"
    meta["duration"] = 115.5
    models_info = {"stt": "distil-large-v3", "refiner": "qwen3:8b", "documenter": "gemma3:12b"}
    meta["models"] = models_info
    save_meta(run_id, meta)

    append_event(run_id, "run.started", {"from_stage": from_stage, "models": models_info, "profile": "standard"})
    time.sleep(step_delay)

    # 1. Ingest
    if from_stage in ("ingest",):
        append_event(run_id, "stage.started", {"stage": "ingest"})
        peaks = [round(abs((i % 20 - 10) / 10.0), 3) for i in range(1600)]
        save_json(run_id, "peaks.json", {"duration": 115.5, "peaks": peaks})
        time.sleep(step_delay)
        append_event(run_id, "audio.ready", {
            "duration": 115.5,
            "audio_url": f"/api/runs/{run_id}/audio",
            "peaks_url": f"/api/runs/{run_id}/peaks",
        })
        append_event(run_id, "stage.done", {"stage": "ingest", "seconds": 0.45})

    # 2. Transcribe
    if from_stage in ("ingest", "transcribe"):
        append_event(run_id, "stage.started", {"stage": "transcribe", "model": "distil-large-v3"})
        for seg in FAKE_RAW_SEGMENTS:
            append_event(run_id, "transcript.segment", seg.model_dump())
            append_event(run_id, "stage.progress", {
                "stage": "transcribe",
                "done": seg.end,
                "total": 115.5,
                "label": f"Listening {int(seg.end//60):02d}:{int(seg.end%60):02d} of 01:55",
            })
            time.sleep(step_delay * 0.4)

        raw_transcript = RawTranscript(
            segments=FAKE_RAW_SEGMENTS,
            duration=115.5,
            language="en",
            model="distil-large-v3",
            device="cpu",
        )
        save_json(run_id, "raw_transcript.json", raw_transcript)
        append_event(run_id, "stage.done", {"stage": "transcribe", "seconds": 4.12})

    # 3. Refine
    if from_stage in ("ingest", "transcribe", "refine"):
        append_event(run_id, "stage.started", {"stage": "refine", "model": "qwen3:8b"})
        time.sleep(step_delay)
        append_event(run_id, "refine.profile", FAKE_PROFILE.model_dump())

        for corr in FAKE_CORRECTIONS:
            append_event(run_id, "refine.correction", corr.model_dump())
            time.sleep(step_delay * 0.5)

        append_event(run_id, "refine.blocked", FAKE_BLOCKED.model_dump())

        # Construct refined segments
        refined_segs = []
        for s in FAKE_RAW_SEGMENTS:
            text = s.text
            spans = []
            if s.id == 2:
                text = text.replace("Memcatch", "Memcached")
                idx = text.find("Memcached")
                spans.append(Span(start=idx, end=idx + len("Memcached"), correction_id="c1"))
            elif s.id == 6:
                text = text.replace("Memcatch", "Memcached")
                idx = text.find("Memcached")
                spans.append(Span(start=idx, end=idx + len("Memcached"), correction_id="c2"))
            elif s.id == 11:
                text = text.replace("post-GIR SQL", "PostgreSQL")
                idx = text.find("PostgreSQL")
                spans.append(Span(start=idx, end=idx + len("PostgreSQL"), correction_id="c3"))
            elif s.id == 13:
                text = text.replace("OOFscopes", "OAuth scopes")
                idx = text.find("OAuth scopes")
                spans.append(Span(start=idx, end=idx + len("OAuth scopes"), correction_id="c4"))

            refined_segs.append(RefinedSegment(
                id=s.id,
                start=s.start,
                end=s.end,
                text=text,
                spans=spans,
            ))

        refined_transcript = RefinedTranscript(
            segments=refined_segs,
            corrections=FAKE_CORRECTIONS + [FAKE_BLOCKED],
            profile=FAKE_PROFILE,
            model="qwen3:8b",
        )
        save_json(run_id, "refined_transcript.json", refined_transcript)
        append_event(run_id, "refine.done", {
            "segments": [rs.model_dump() for rs in refined_segs],
            "corrections": [c.model_dump() for c in (FAKE_CORRECTIONS + [FAKE_BLOCKED])],
        })
        append_event(run_id, "stage.done", {"stage": "refine", "seconds": 3.84})

    # 4. Document
    if from_stage in ("ingest", "transcribe", "refine", "document"):
        append_event(run_id, "stage.started", {"stage": "document", "model": "gemma3:12b"})
        time.sleep(step_delay)
        append_event(run_id, "record.section", {"section": "summary", "data": {"title": FAKE_RECORD.title, "summary": FAKE_RECORD.summary, "attendees": FAKE_RECORD.attendees}})
        time.sleep(step_delay)
        append_event(run_id, "record.section", {"section": "minutes", "data": {"topics": [m.model_dump() for m in FAKE_RECORD.minutes]}})
        time.sleep(step_delay)
        append_event(run_id, "record.section", {"section": "decisions", "data": {"decisions": [d.model_dump() for d in FAKE_RECORD.decisions], "unresolved": [u.model_dump() for u in FAKE_RECORD.unresolved]}})
        time.sleep(step_delay)
        append_event(run_id, "record.section", {"section": "actions", "data": {"action_items": [a.model_dump() for a in FAKE_RECORD.action_items]}})
        time.sleep(step_delay)
        append_event(run_id, "record.section", {"section": "verified", "data": {"status": "verified"}})

        save_json(run_id, "meeting_record.json", FAKE_RECORD)
        append_event(run_id, "stage.done", {"stage": "document", "seconds": 6.22})

    # 5. Export
    append_event(run_id, "stage.started", {"stage": "export"})
    export_all_run_files(run_id)
    append_event(run_id, "stage.done", {"stage": "export", "seconds": 0.25})

    meta = load_meta(run_id) or {}
    meta["status"] = "done"
    meta["stage"] = None
    meta["title"] = FAKE_RECORD.title
    save_meta(run_id, meta)

    append_event(run_id, "run.done", {})
    logger.info("Fake pipeline execution for %s completed successfully.", run_id)
