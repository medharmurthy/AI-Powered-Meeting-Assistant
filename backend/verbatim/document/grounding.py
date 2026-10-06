from __future__ import annotations

import re
from typing import Any, Callable, TypeVar
import rapidfuzz
from rapidfuzz import fuzz

from verbatim.schemas import (
    ActionItem,
    Decision,
    Dropped,
    Point,
    MinutesTopic,
    Unresolved,
)

T = TypeVar("T")

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
    "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so",
    "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
    "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll",
    "they're", "they've", "this", "those", "through", "to", "too", "under",
    "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're",
    "we've", "were", "weren't", "what", "what's", "when", "when's", "where",
    "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with",
    "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've",
    "your", "yours", "yourself", "yourselves", "just", "now", "well", "okay",
}

GENERIC_OWNERS = {
    "i", "me", "my", "we", "us", "our", "team", "everyone", "everybody",
    "someone", "somebody", "anyone", "anybody", "nobody", "speaker", "all",
    "the team", "engineering team", "unassigned",
}


def crude_stem(word: str) -> str:
    """Crude stemming: strip common trailing inflections if length is sufficient."""
    w = word.lower()
    if len(w) > 5 and w.endswith("ing"):
        return w[:-3]
    if len(w) > 4 and w.endswith("ed"):
        return w[:-2]
    if len(w) > 4 and w.endswith("es"):
        return w[:-2]
    if len(w) > 3 and w.endswith("s"):
        return w[:-1]
    return w


def extract_content_tokens(text: str) -> set[str]:
    """Extract content tokens: lowercase words, length >= 3, stopwords removed, crudely stemmed."""
    words = re.findall(r"\b[a-zA-Z0-9_-]+\b", text.lower())
    tokens = set()
    for w in words:
        if len(w) >= 3 and w not in STOPWORDS:
            tokens.add(crude_stem(w))
    return tokens


def get_context_text(
    segment_ids: list[int],
    segments_by_id: dict[int, str],
    window: int = 1,
) -> str:
    """Gather text of cited segment IDs expanded by +/- window lines."""
    expanded_ids = set()
    for sid in segment_ids:
        for offset in range(-window, window + 1):
            target_id = sid + offset
            if target_id in segments_by_id:
                expanded_ids.add(target_id)
    return " ".join(segments_by_id[sid] for sid in sorted(expanded_ids))


def calculate_support(item_text: str, context_text: str) -> float:
    """Calculate support: |tokens(item) ∩ tokens(cited +/-1 lines)| / |tokens(item)|."""
    item_tokens = extract_content_tokens(item_text)
    if not item_tokens:
        return 1.0
    ctx_tokens = extract_content_tokens(context_text)
    overlap = len(item_tokens & ctx_tokens)
    return overlap / len(item_tokens)


def validate_owner(
    owner: str | None,
    cited_ids: list[int],
    segments_by_id: dict[int, str],
    participants: list[str],
    owner_window: int = 4,
) -> tuple[str | None, str | None]:
    """
    Validate owner candidate against rules:
    - null if generic pronoun/role or SPEAKER_nn
    - must appear in cited +/- owner_window or explicit participants list
    Returns (cleaned_owner_or_none, drop_reason_if_demoted).
    """
    if not owner or not owner.strip():
        return None, None

    cleaned = owner.strip()
    lower = cleaned.lower()

    # Rule 1: Generic owners check
    if lower in GENERIC_OWNERS:
        return None, f"generic owner '{cleaned}' set to unspecified"
    if re.match(r"^speaker[_\s-]?\d+$", lower):
        return None, f"generic speaker label '{cleaned}' set to unspecified"

    # Rule 2: Explicit participants list check
    for p in participants:
        p_clean = p.strip().lower()
        if p_clean and (p_clean in lower or lower in p_clean):
            return cleaned, None

    # Rule 3: Must appear within owner_window lines of cited lines
    window_text = get_context_text(cited_ids, segments_by_id, window=owner_window).lower()
    owner_words = [w.lower() for w in re.findall(r"\b[a-zA-Z0-9_-]+\b", cleaned) if len(w) >= 2]
    if owner_words and all(w in window_text for w in owner_words):
        return cleaned, None

    return None, f"owner '{cleaned}' not stated in cited lines or participants"


def validate_deadline(
    deadline: str | None,
    cited_ids: list[int],
    segments_by_id: dict[int, str],
    deadline_window: int = 2,
) -> tuple[str | None, str | None]:
    """
    Validate deadline phrase against rules:
    - must appear in cited lines +/- deadline_window
    - keep verbatim as spoken, never guess calendar dates
    """
    if not deadline or not deadline.strip():
        return None, None

    cleaned = deadline.strip()
    window_text = get_context_text(cited_ids, segments_by_id, window=deadline_window).lower()

    content_tokens = extract_content_tokens(cleaned)
    if not content_tokens:
        content_tokens = {w.lower() for w in re.findall(r"\b[a-zA-Z0-9_-]+\b", cleaned) if len(w) >= 2}

    if not content_tokens:
        return None, f"deadline '{cleaned}' has no meaningful tokens"

    # Check if any content token or the phrase is in the cited window
    if any(token in window_text for token in content_tokens) or cleaned.lower() in window_text:
        return cleaned, None

    return None, f"deadline '{cleaned}' not stated in cited lines"


def validate_quote(
    quote: str | None,
    cited_ids: list[int],
    segments_by_id: dict[int, str],
) -> str | None:
    """Validate quote: rapidfuzz partial_ratio >= 85 against cited text, else null."""
    if not quote or not quote.strip():
        return None
    cleaned = quote.strip()
    cited_text = " ".join(segments_by_id.get(sid, "") for sid in cited_ids)
    if not cited_text:
        return None
    ratio = fuzz.partial_ratio(cleaned.lower(), cited_text.lower())
    if ratio >= 85:
        return cleaned
    return None


def deduplicate_items(
    items: list[T],
    text_extractor: Callable[[T], str],
    segment_ids_extractor: Callable[[T], list[int]],
    threshold: float = 88.0,
) -> list[T]:
    """
    De-duplicate items where fuzz.token_set_ratio >= threshold.
    Keeps the one citing more segment_ids.
    """
    result: list[T] = []
    for item in items:
        item_text = text_extractor(item)
        item_sids = segment_ids_extractor(item)
        duplicate_idx = -1

        for idx, kept in enumerate(result):
            kept_text = text_extractor(kept)
            score = fuzz.token_set_ratio(item_text, kept_text)
            if score >= threshold:
                duplicate_idx = idx
                break

        if duplicate_idx == -1:
            result.append(item)
        else:
            kept_sids = segment_ids_extractor(result[duplicate_idx])
            # If current item has more segment_ids, replace the existing one
            if len(item_sids) > len(kept_sids):
                result[duplicate_idx] = item

    return result
