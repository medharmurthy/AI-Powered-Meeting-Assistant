from __future__ import annotations

import pytest
from verbatim.document.grounding import (
    calculate_support,
    crude_stem,
    deduplicate_items,
    extract_content_tokens,
    get_context_text,
    validate_deadline,
    validate_owner,
    validate_quote,
)
from verbatim.schemas import ActionItem, Decision


def test_crude_stem_and_tokens():
    tokens = extract_content_tokens("Upgrading databases and migrating clusters quickly!")
    assert "upgrad" in tokens or "upgrad" in [crude_stem(t) for t in tokens]
    assert "migrat" in tokens or "migrat" in [crude_stem(t) for t in tokens]
    assert "cluster" in tokens or "cluster" in [crude_stem(t) for t in tokens]
    # Stopwords like "and" should be excluded
    assert "and" not in tokens


def test_generic_owner_demoted():
    segments = {1: "Someone should check the Redis servers.", 2: "We will handle it."}
    participants = ["Maya", "Dan", "Priya"]

    # "we" -> None
    owner, reason = validate_owner("we", [1, 2], segments, participants)
    assert owner is None
    assert "generic" in reason.lower()

    # "team" -> None
    owner, reason = validate_owner("team", [1, 2], segments, participants)
    assert owner is None
    assert "generic" in reason.lower()

    # "SPEAKER_01" -> None
    owner, reason = validate_owner("SPEAKER_01", [1, 2], segments, participants)
    assert owner is None
    assert "speaker" in reason.lower()

    # "someone" -> None
    owner, reason = validate_owner("someone", [1, 2], segments, participants)
    assert owner is None


def test_hallucinated_owner_demoted():
    segments = {
        10: "Dan, can you write the Terraform module for the Redis cluster?",
        11: "Yes, I'll have the Terraform module done by Thursday.",
    }
    participants = ["Maya", "Dan", "Priya"]

    # "Alice" was not in participants and never spoken in cited lines
    owner, reason = validate_owner("Alice", [10, 11], segments, participants)
    assert owner is None
    assert "not stated" in reason.lower()


def test_valid_owner_accepted():
    segments = {
        10: "Dan, can you write the Terraform module for the Redis cluster?",
        11: "Yes, I'll have the Terraform module done by Thursday.",
    }
    participants = ["Maya", "Dan", "Priya"]

    # Dan is in participants and cited in line 10
    owner, reason = validate_owner("Dan", [10, 11], segments, participants)
    assert owner == "Dan"
    assert reason is None

    # Priya is in participants list
    owner, reason = validate_owner("Priya", [10, 11], segments, participants)
    assert owner == "Priya"
    assert reason is None


def test_hallucinated_deadline_demoted():
    segments = {
        10: "Dan, can you write the Terraform module?",
        11: "Yes, I'll have the module done by Thursday.",
    }

    # "by October 15th 2026" was never spoken
    deadline, reason = validate_deadline("October 15th 2026", [10, 11], segments)
    assert deadline is None
    assert "not stated" in reason.lower()


def test_valid_deadline_preserved_verbatim():
    segments = {
        10: "Dan, can you write the Terraform module?",
        11: "Yes, I'll have the module done by Thursday.",
        25: "The audit is on the fifteenth. Someone has to rotate the database credentials before then.",
    }

    # "by Thursday" spoken in line 11
    deadline, reason = validate_deadline("by Thursday", [10, 11], segments)
    assert deadline == "by Thursday"
    assert reason is None

    # "before the audit on the 15th"
    deadline, reason = validate_deadline("before the audit on the 15th", [25], segments)
    assert deadline == "before the audit on the 15th"
    assert reason is None


def test_support_threshold_filter():
    segments = {
        5: "We decided to migrate the session cache from Memcached to Redis.",
    }
    ctx = get_context_text([5], segments, window=1)

    # Valid supported text
    support_good = calculate_support("Migrate session cache from Memcached to Redis", ctx)
    assert support_good >= 0.7

    # Hallucinated text not mentioned at all
    support_bad = calculate_support("Implement GraphQL gateway with Apollo Federation in Go", ctx)
    assert support_bad < 0.2


def test_deduplicate_items():
    items = [
        Decision(
            id="D1",
            text="Migrate the session cache from Memcached to Redis",
            segment_ids=[5],
        ),
        Decision(
            id="D2",
            text="Migrate session cache from Memcached to Redis",
            segment_ids=[5, 6, 7],
        ),
        Decision(
            id="D3",
            text="Do not upgrade PostgreSQL to version 16 this quarter",
            segment_ids=[15],
        ),
    ]

    deduped = deduplicate_items(
        items,
        text_extractor=lambda x: x.text,
        segment_ids_extractor=lambda x: x.segment_ids,
        threshold=88.0,
    )
    # The two Redis decisions should be merged into one, keeping the one with more segment_ids [5, 6, 7]
    assert len(deduped) == 2
    redis_decision = [d for d in deduped if "Redis" in d.text][0]
    assert redis_decision.segment_ids == [5, 6, 7]


def test_validate_quote():
    segments = {
        10: "We will roll it out on the Kubernetes staging cluster first with a canary deployment, five percent of traffic.",
    }

    # Close quote
    q1 = validate_quote("canary deployment, five percent of traffic", [10], segments)
    assert q1 is not None

    # Made up quote
    q2 = validate_quote("deploying fifty percent to production right away", [10], segments)
    assert q2 is None
