"""
semantic_scorer.py — Hybrid semantic fit scorer.

Combines TF-IDF cosine similarity (from semantic_similarity.py) with
weighted term overlap for recruiter-readable matched-term extraction.
The numeric score comes from the mathematically rigorous cosine
similarity model; the matched_terms list feeds into reasoning strings.
"""

from __future__ import annotations

import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import JD_PROFILE_TEXT, JD_TERM_WEIGHTS
from scoring.semantic_similarity import score_semantic_similarity

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+#./-]*[a-z0-9]|[a-z0-9]")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _build_profile_text(candidate: dict) -> str:
    profile = candidate.get("profile", {})
    parts = [
        profile.get("headline", ""),
        profile.get("summary", ""),
        profile.get("current_title", ""),
    ]
    for role in candidate.get("career_history", []):
        parts.append(role.get("title", ""))
        parts.append(role.get("description", ""))
    for skill in candidate.get("skills", []):
        parts.append(skill.get("name", ""))
    return " ".join(parts)


def _extract_matched_terms(candidate: dict) -> list[str]:
    """Extract which JD terms are present in the candidate profile.

    This is used for recruiter-facing reasoning only; the numeric
    score comes from the TF-IDF cosine similarity model.
    """
    text = _build_profile_text(candidate)
    tokens = set(_tokenize(text))
    if not tokens:
        return []

    matched: list[str] = []
    lower = text.lower()

    for term, weight in JD_TERM_WEIGHTS.items():
        term_tokens = term.split()
        if len(term_tokens) == 1:
            if term in tokens or term in lower:
                matched.append(term)
        else:
            if term in lower:
                matched.append(term)

    return matched[:12]


def score_semantic(candidate: dict) -> dict:
    """
    Score semantic alignment to the JD (0-100).

    Uses TF-IDF cosine similarity with static IDF heuristics for the
    numeric score, and weighted term overlap for matched-term extraction.
    """
    # Numeric score from TF-IDF cosine similarity with IDF weighting
    cosine_score = score_semantic_similarity(candidate)

    # Extract matched terms for recruiter reasoning
    matched = _extract_matched_terms(candidate)

    return {
        "score": cosine_score,
        "matched_terms": matched,
    }
