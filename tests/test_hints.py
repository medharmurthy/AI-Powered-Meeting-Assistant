from __future__ import annotations

from verbatim.refine.hints import Hint, hints
from verbatim.schemas import Segment


def test_hints_post_gress_ql_to_postgresql():
    seg = Segment(
        id=8,
        start=20.0,
        end=24.0,
        text="On post gress Q L, we are not going to upgrade this quarter.",
    )
    terms = ["PostgreSQL", "Redis", "Kafka"]
    results = hints([seg], terms, min_score=72)

    pg_hints = [h for h in results if h.term == "PostgreSQL"]
    assert len(pg_hints) > 0
    top = pg_hints[0]
    assert top.segment_id == 8
    assert "post gress" in top.heard.lower()
    assert top.score >= 72


def test_hints_cooper_netties_to_kubernetes():
    seg = Segment(
        id=3,
        start=8.0,
        end=12.0,
        text="We deploy it on cooper netties next week.",
    )
    terms = ["Kubernetes", "Docker"]
    results = hints([seg], terms, min_score=72)

    k8s_hints = [h for h in results if h.term == "Kubernetes"]
    assert len(k8s_hints) > 0
    top = k8s_hints[0]
    assert top.segment_id == 3
    assert top.heard.lower() == "cooper netties"
    assert top.score >= 72


def test_hints_memcatch_to_memcached():
    seg = Segment(
        id=1,
        start=2.0,
        end=6.0,
        text="On the session cache, we are still on Memcatch.",
    )
    terms = ["Memcached", "Redis"]
    results = hints([seg], terms, min_score=72)

    mem_hints = [h for h in results if h.term == "Memcached"]
    assert len(mem_hints) > 0
    top = mem_hints[0]
    assert top.segment_id == 1
    assert "memcatch" in top.heard.lower()
    assert top.score >= 72


def test_hints_excludes_exact_matches():
    seg = Segment(
        id=2,
        start=6.0,
        end=9.0,
        text="Moving the session cache to Redis is approved.",
    )
    terms = ["Redis"]
    results = hints([seg], terms, min_score=72)
    # Redis is already spelled correctly; should not suggest Redis -> Redis
    redis_hints = [h for h in results if h.heard.lower() == "redis"]
    assert len(redis_hints) == 0


def test_hint_object_properties_and_access():
    h = Hint(segment_id=5, heard="gr pick", term="gRPC", score=80.0)
    assert h.segment_id == 5
    assert h.heard == "gr pick"
    assert h.term == "gRPC"
    assert h.score == 80.0
    # Also test dict-like access for Jinja2 template compatibility
    assert h["segment_id"] == 5
    assert h["heard"] == "gr pick"
    assert h["term"] == "gRPC"
