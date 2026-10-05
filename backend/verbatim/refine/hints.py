from __future__ import annotations

import re
from typing import Any
import jellyfish
from pydantic import BaseModel
import rapidfuzz.fuzz as fuzz


class Hint(BaseModel):
    segment_id: int
    heard: str
    term: str
    score: float

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)


def hints(
    segments: list[Any],
    terms: list[str],
    min_score: int = 72,
) -> list[Hint]:
    """Generate candidate phonetic mishearings for speech-to-text segments."""
    norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    out: dict[tuple[int, str, str], float] = {}

    for seg in segments:
        seg_id = getattr(seg, "id", None)
        if seg_id is None and isinstance(seg, dict):
            seg_id = seg.get("id")
        seg_text = getattr(seg, "text", None)
        if seg_text is None and isinstance(seg, dict):
            seg_text = seg.get("text", "")
        if not seg_text or seg_id is None:
            continue

        toks = re.findall(r"[A-Za-z0-9'.\-]+", seg_text)
        for n in (1, 2, 3):
            for i in range(len(toks) - n + 1):
                heard = " ".join(toks[i : i + n])
                h = norm(heard)
                if len(h) < 4:
                    continue
                for t in terms:
                    if heard.lower() == t.lower():
                        continue
                    t_norm = norm(t)
                    if not t_norm:
                        continue
                    score = max(
                        float(fuzz.ratio(h, t_norm)),
                        float(fuzz.ratio(jellyfish.metaphone(h), jellyfish.metaphone(t_norm))),
                    )
                    if score >= min_score:
                        out[(seg_id, heard, t)] = score

    sorted_keys = sorted(out.keys(), key=lambda k: -out[k])
    return [
        Hint(
            segment_id=k[0],
            heard=k[1],
            term=k[2],
            score=round(out[k], 2),
        )
        for k in sorted_keys
    ]
