from __future__ import annotations

from verbatim.refine.apply import apply, propagate_corrections
from verbatim.schemas import Correction, Segment


def test_apply_zero_corrections():
    text = "We are deploying on staging today."
    refined_text, spans = apply(text, [])
    assert refined_text == text
    assert spans == []


def test_apply_one_correction():
    text = "We are still on Memcatch today."
    corr = Correction(
        id="c1",
        segment_id=0,
        original="Memcatch",
        corrected="Memcached",
        reason="Misheard Memcached",
        status="applied",
    )
    refined_text, spans = apply(text, [corr])
    assert refined_text == "We are still on Memcached today."
    assert len(spans) == 1
    assert spans[0].correction_id == "c1"
    assert spans[0].start == 16
    assert spans[0].end == 25
    assert refined_text[spans[0].start : spans[0].end] == "Memcached"


def test_apply_two_non_overlapping_corrections():
    text = "Deploy cooper netties and use Memcatch for cache."
    c1 = Correction(
        id="c1",
        segment_id=0,
        original="cooper netties",
        corrected="Kubernetes",
        reason="Misheard Kubernetes",
        status="applied",
    )
    c2 = Correction(
        id="c2",
        segment_id=0,
        original="Memcatch",
        corrected="Memcached",
        reason="Misheard Memcached",
        status="applied",
    )
    refined_text, spans = apply(text, [c2, c1])  # Pass out of order to verify sorting
    assert refined_text == "Deploy Kubernetes and use Memcached for cache."
    assert len(spans) == 2

    # Check first span
    assert spans[0].correction_id == "c1"
    assert refined_text[spans[0].start : spans[0].end] == "Kubernetes"

    # Check second span
    assert spans[1].correction_id == "c2"
    assert refined_text[spans[1].start : spans[1].end] == "Memcached"


def test_apply_overlapping_corrections():
    text = "Deploy on cooper netties cluster."
    c1 = Correction(
        id="c1",
        segment_id=0,
        original="cooper netties",
        corrected="Kubernetes",
        reason="Misheard Kubernetes",
        status="applied",
    )
    # Overlapping edit targeting just "netties"
    c2 = Correction(
        id="c2",
        segment_id=0,
        original="netties",
        corrected="network",
        reason="test overlap",
        status="applied",
    )
    refined_text, spans = apply(text, [c1, c2])
    # c2 overlaps with c1, so c2 must be skipped
    assert refined_text == "Deploy on Kubernetes cluster."
    assert len(spans) == 1
    assert spans[0].correction_id == "c1"
    assert refined_text[spans[0].start : spans[0].end] == "Kubernetes"


def test_apply_case_insensitive_fallback():
    text = "We are using MEMCATCH for sessions."
    corr = Correction(
        id="c1",
        segment_id=0,
        original="memcatch",
        corrected="Memcached",
        reason="case insensitive match",
        status="applied",
    )
    refined_text, spans = apply(text, [corr])
    assert refined_text == "We are using Memcached for sessions."
    assert len(spans) == 1
    assert refined_text[spans[0].start : spans[0].end] == "Memcached"


def test_propagation_across_segments():
    seg1 = Segment(id=1, start=0.0, end=3.0, text="We migrate from Memcatch to Redis.")
    seg2 = Segment(id=2, start=3.0, end=6.0, text="Redis latency was ninety milliseconds.")
    seg3 = Segment(id=3, start=6.0, end=9.0, text="Because Memcatch was too slow for login.")

    accepted = [
        Correction(
            id="c1",
            segment_id=1,
            original="Memcatch",
            corrected="Memcached",
            reason="Misheard Memcached",
            status="applied",
        )
    ]

    counter = 1

    def next_id():
        nonlocal counter
        counter += 1
        return f"c{counter}"

    def always_valid(c):
        return True, None

    propagated = propagate_corrections(
        segments=[seg1, seg2, seg3],
        accepted_corrections=accepted,
        validator=always_valid,
        next_id_fn=next_id,
    )

    # seg1 already had c1, seg2 has no Memcatch, seg3 has Memcatch -> propagated to seg3
    assert len(propagated) == 1
    assert propagated[0].segment_id == 3
    assert propagated[0].original == "Memcatch"
    assert propagated[0].corrected == "Memcached"
    assert propagated[0].source == "propagated"
    assert propagated[0].status == "applied"


def test_refine_transcript_stage_end_to_end():
    from verbatim.refine.stage import refine_transcript
    from verbatim.schemas import DomainProfile, Proposal, ProposalList, RawTranscript
    from verbatim.store import create_run, delete_run, load_json, save_json, save_meta

    run_id = create_run("test_refine_end_to_end.wav")
    try:
        seg0 = Segment(id=0, start=0.0, end=4.0, text="We are deploying on cooper netties next week.")
        seg1 = Segment(id=1, start=4.0, end=8.0, text="The database is on Memcatch.")
        raw = RawTranscript(segments=[seg0, seg1], duration=8.0, language="en", model="distil-large-v3", device="cpu")
        save_json(run_id, "raw_transcript.json", raw)
        save_meta(run_id, {"glossary": ["Kubernetes", "Memcached"], "participants": ["Maya"]})

        class MockLLM:
            def __init__(self):
                self.unloaded = False

            def structured(self, *, model, system, user, schema, role=None):
                if schema == DomainProfile:
                    return DomainProfile(topic="infra", domain="backend", likely_terms=["Kubernetes", "Memcached"], names=["Maya"])
                elif schema == ProposalList:
                    return ProposalList(
                        corrections=[
                            Proposal(segment_id=0, original="cooper netties", corrected="Kubernetes", reason="Misheard Kubernetes"),
                            Proposal(segment_id=1, original="Memcatch", corrected="Memcached", reason="Misheard Memcached"),
                        ]
                    )
                raise ValueError(f"Unexpected schema: {schema}")

            def unload(self, model):
                self.unloaded = True

            def available_models(self):
                return {"mock-model"}

        mock_llm = MockLLM()
        refined = refine_transcript(run_id, llm_client=mock_llm)

        assert len(refined.segments) == 2
        assert refined.segments[0].text == "We are deploying on Kubernetes next week."
        assert len(refined.segments[0].spans) == 1
        assert refined.segments[0].spans[0].start == 20
        assert refined.segments[0].spans[0].end == 30
        assert refined.segments[1].text == "The database is on Memcached."
        assert len(refined.corrections) == 2
        assert mock_llm.unloaded is True

        saved_data = load_json(run_id, "refined_transcript.json")
        assert saved_data is not None
        assert "segments" in saved_data
        assert "corrections" in saved_data
    finally:
        delete_run(run_id)

