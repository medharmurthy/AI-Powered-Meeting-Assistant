from __future__ import annotations

from collections import Counter
import re
from typing import Any

from verbatim.schemas import Proposal

NUMBER_WORDS = {
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
    "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
    "eighty", "ninety", "hundred", "thousand", "million", "billion",
    "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth",
    "ninth", "tenth", "eleventh", "twelfth", "thirteenth", "fourteenth", "fifteenth",
    "sixteenth", "seventeenth", "eighteenth", "nineteenth", "twentieth", "thirtieth",
    "fortieth", "fiftieth", "sixtieth", "seventieth", "eightieth", "ninetieth",
    "hundredth", "thousandth", "millionth",
}

NEGATION_WORDS = {
    "not", "no", "never", "none", "nothing", "nobody", "neither", "nor", "cannot", "without"
}

COMMITMENT_WORDS = {
    "will", "won't", "shall", "should", "must", "can", "could", "might", "may", "need", "needs", "going"
}


def extract_number_multiset(text: str) -> Counter:
    """Extract multiset of digit strings and number words."""
    # Match digits: \d[\d.,]*
    raw_digits = re.findall(r"\d[\d.,]*", text)
    cleaned_digits = [re.sub(r"[.,]+$", "", d) for d in raw_digits if re.sub(r"[.,]+$", "", d)]

    # Match number words
    raw_words = re.findall(r"[a-zA-Z]+", text.lower())
    words = [w for w in raw_words if w in NUMBER_WORDS]

    return Counter(cleaned_digits + words)


def extract_negation_multiset(text: str) -> Counter:
    """Extract multiset of negation words and n't contractions."""
    raw_words = re.findall(r"[a-zA-Z']+", text.lower())
    negs = []
    for w in raw_words:
        if w in NEGATION_WORDS:
            negs.append(w)
        elif w.endswith("n't") or "n't" in w:
            negs.append("n't")
    return Counter(negs)


def extract_commitment_multiset(text: str) -> Counter:
    """Extract multiset of modal/commitment words."""
    raw_words = re.findall(r"[a-zA-Z']+", text.lower())
    return Counter(w for w in raw_words if w in COMMITMENT_WORDS)


def validate_proposal(
    proposal: Proposal | dict[str, Any],
    raw_segments_map: dict[int, str],
    editable_segment_ids: set[int] | list[int] | None = None,
    participants: list[str] | None = None,
    max_original_words: int = 6,
) -> tuple[bool, str | None]:
    """Validate a correction proposal against the 7 deterministic guardrails.

    Returns:
        (True, None) if the proposal passes all guardrails.
        (False, block_reason) if any guardrail fails.
    """
    if isinstance(proposal, dict):
        seg_id = proposal.get("segment_id")
        orig = proposal.get("original", "")
        corr = proposal.get("corrected", "")
    else:
        seg_id = proposal.segment_id
        orig = proposal.original
        corr = proposal.corrected

    orig = orig.strip() if orig else ""
    corr = corr.strip() if corr else ""

    # Rule 1: segment_id exists and is in the editable range
    if seg_id not in raw_segments_map:
        return False, "Referred to a line that doesn't exist"
    if editable_segment_ids is not None and seg_id not in editable_segment_ids:
        return False, "Referred to a line that doesn't exist"

    raw_text = raw_segments_map[seg_id]

    # Rule 2: original occurs verbatim in the raw segment (exact, then case-insensitive)
    if not orig:
        return False, "Quoted text that isn't in the recording"
    if orig not in raw_text and orig.lower() not in raw_text.lower():
        return False, "Quoted text that isn't in the recording"

    # Rule 3: original != corrected, len(original.split()) <= max_original_words,
    # len(corrected.split()) <= len(original.split()) + 3
    orig_words = orig.split()
    corr_words = corr.split()
    if orig == corr or orig.lower() == corr.lower():
        return False, "Edit was too large"
    if len(orig_words) > max_original_words:
        return False, "Edit was too large"
    if len(corr_words) > len(orig_words) + 3:
        return False, "Edit was too large"

    # Rule 4: Number tokens equal
    if extract_number_multiset(orig) != extract_number_multiset(corr):
        return False, "Would change a number"

    # Rule 5: Negations equal
    if extract_negation_multiset(orig) != extract_negation_multiset(corr):
        return False, "Would change a negation"

    # Rule 6: Modal/commitment words equal
    if extract_commitment_multiset(orig) != extract_commitment_multiset(corr):
        return False, "Would change a commitment"

    # Rule 7: Participant names preserved
    if participants:
        participant_tokens = set()
        for p in participants:
            for tok in re.findall(r"[a-zA-Z0-9]+", p.lower()):
                participant_tokens.add(tok)

        orig_tokens = set(re.findall(r"[a-zA-Z0-9]+", orig.lower()))
        corr_tokens = set(re.findall(r"[a-zA-Z0-9]+", corr.lower()))

        for p_tok in participant_tokens:
            if p_tok in orig_tokens and p_tok not in corr_tokens:
                return False, "Would change a person's name"

    return True, None
