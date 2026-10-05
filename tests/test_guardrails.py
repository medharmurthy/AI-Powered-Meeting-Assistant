from __future__ import annotations

import pytest
from verbatim.refine.guardrails import validate_proposal
from verbatim.schemas import Proposal


@pytest.fixture
def sample_segments():
    return {
        0: "Okay, let's get started. Thanks for joining, Priya and Dan.",
        1: "On the session cache, we're still on Memcatch, and p99 latency on login is around three hundred forty milliseconds.",
        2: "Maya: we deploy it on cooper netties next week.",
        3: "On post gress Q L, we are not going to upgrade to version sixteen this quarter.",
        4: "Dan, can you write the Terraform module?",
        5: "Yes, we will ship it on the 14th, no later.",
    }


def test_rule_1_segment_existence_and_editable_window(sample_segments):
    # Segment does not exist at all
    p_nonexistent = Proposal(
        segment_id=999,
        original="anything",
        corrected="something",
        reason="test",
    )
    ok, reason = validate_proposal(p_nonexistent, sample_segments, editable_segment_ids={1, 2})
    assert not ok
    assert reason == "Referred to a line that doesn't exist"

    # Segment exists in transcript, but is in read-only context (not in editable_segment_ids)
    p_context = Proposal(
        segment_id=0,
        original="Priya",
        corrected="Priya",
        reason="test",
    )
    ok, reason = validate_proposal(p_context, sample_segments, editable_segment_ids={1, 2})
    assert not ok
    assert reason == "Referred to a line that doesn't exist"


def test_rule_2_original_verbatim_presence(sample_segments):
    # Quoted text not in line
    p_fake = Proposal(
        segment_id=1,
        original="Apache Kafka",
        corrected="Kafka",
        reason="test",
    )
    ok, reason = validate_proposal(p_fake, sample_segments, editable_segment_ids={1})
    assert not ok
    assert reason == "Quoted text that isn't in the recording"


def test_rule_3_edit_size_and_identity(sample_segments):
    # Identical edit
    p_same = Proposal(
        segment_id=1,
        original="Memcatch",
        corrected="Memcatch",
        reason="test",
    )
    ok, reason = validate_proposal(p_same, sample_segments, editable_segment_ids={1})
    assert not ok
    assert reason == "Edit was too large"

    # Original too long (> 6 words)
    long_orig = "we're still on Memcatch, and p99 latency"
    p_long_orig = Proposal(
        segment_id=1,
        original=long_orig,
        corrected="Redis",
        reason="test",
    )
    ok, reason = validate_proposal(p_long_orig, sample_segments, editable_segment_ids={1})
    assert not ok
    assert reason == "Edit was too large"

    # Corrected too long (> original words + 3)
    p_long_corr = Proposal(
        segment_id=1,
        original="Memcatch",
        corrected="Redis cluster with high availability and replication",
        reason="test",
    )
    ok, reason = validate_proposal(p_long_corr, sample_segments, editable_segment_ids={1})
    assert not ok
    assert reason == "Edit was too large"


def test_rule_4_number_invariance(sample_segments):
    # Changing number word: three hundred forty -> three hundred fifty
    p_num_word = Proposal(
        segment_id=1,
        original="three hundred forty",
        corrected="three hundred fifty",
        reason="test",
    )
    ok, reason = validate_proposal(p_num_word, sample_segments, editable_segment_ids={1})
    assert not ok
    assert reason == "Would change a number"

    # Changing digit: p99 -> p95
    p_digit = Proposal(
        segment_id=1,
        original="p99",
        corrected="p95",
        reason="test",
    )
    ok, reason = validate_proposal(p_digit, sample_segments, editable_segment_ids={1})
    assert not ok
    assert reason == "Would change a number"

    # Dropping a number: version sixteen -> version
    p_drop_num = Proposal(
        segment_id=3,
        original="version sixteen",
        corrected="version",
        reason="test",
    )
    ok, reason = validate_proposal(p_drop_num, sample_segments, editable_segment_ids={3})
    assert not ok
    assert reason == "Would change a number"


def test_rule_5_negation_invariance(sample_segments):
    # Dropping negation: not going to -> going to
    p_neg_drop = Proposal(
        segment_id=3,
        original="not going to",
        corrected="going to",
        reason="test",
    )
    ok, reason = validate_proposal(p_neg_drop, sample_segments, editable_segment_ids={3})
    assert not ok
    assert reason == "Would change a negation"

    # Adding negation: deploy -> never deploy
    p_neg_add = Proposal(
        segment_id=2,
        original="deploy",
        corrected="never deploy",
        reason="test",
    )
    ok, reason = validate_proposal(p_neg_add, sample_segments, editable_segment_ids={2})
    assert not ok
    assert reason == "Would change a negation"


def test_rule_6_commitment_words_invariance(sample_segments):
    # Altering commitment word: will ship -> might ship
    p_commit = Proposal(
        segment_id=5,
        original="will ship",
        corrected="might ship",
        reason="test",
    )
    ok, reason = validate_proposal(p_commit, sample_segments, editable_segment_ids={5})
    assert not ok
    assert reason == "Would change a commitment"

    # Dropping commitment word: will ship -> ship
    p_commit_drop = Proposal(
        segment_id=5,
        original="will ship",
        corrected="ship",
        reason="test",
    )
    ok, reason = validate_proposal(p_commit_drop, sample_segments, editable_segment_ids={5})
    assert not ok
    assert reason == "Would change a commitment"


def test_rule_7_participant_names_preservation(sample_segments):
    # Changing or dropping participant name
    participants = ["Maya", "Priya", "Dan"]

    p_drop_dan = Proposal(
        segment_id=4,
        original="Dan, can you",
        corrected="Can you",
        reason="test",
    )
    ok, reason = validate_proposal(p_drop_dan, sample_segments, editable_segment_ids={4}, participants=participants)
    assert not ok
    assert reason == "Would change a person's name"

    p_change_dan = Proposal(
        segment_id=4,
        original="Dan, can you",
        corrected="Dave, can you",
        reason="test",
    )
    ok, reason = validate_proposal(p_change_dan, sample_segments, editable_segment_ids={4}, participants=participants)
    assert not ok
    assert reason == "Would change a person's name"


def test_valid_technical_proposals_pass(sample_segments):
    participants = ["Maya", "Priya", "Dan"]

    # 1. Memcatch -> Memcached
    p1 = Proposal(
        segment_id=1,
        original="Memcatch",
        corrected="Memcached",
        reason="Misheard Memcached",
    )
    ok1, reason1 = validate_proposal(p1, sample_segments, editable_segment_ids={1}, participants=participants)
    assert ok1
    assert reason1 is None

    # 2. cooper netties -> Kubernetes
    p2 = Proposal(
        segment_id=2,
        original="cooper netties",
        corrected="Kubernetes",
        reason="Misheard Kubernetes",
    )
    ok2, reason2 = validate_proposal(p2, sample_segments, editable_segment_ids={2}, participants=participants)
    assert ok2
    assert reason2 is None

    # 3. post gress Q L -> PostgreSQL (negation "not" untouched outside span)
    p3 = Proposal(
        segment_id=3,
        original="post gress Q L",
        corrected="PostgreSQL",
        reason="Misheard PostgreSQL",
    )
    ok3, reason3 = validate_proposal(p3, sample_segments, editable_segment_ids={3}, participants=participants)
    assert ok3
    assert reason3 is None
