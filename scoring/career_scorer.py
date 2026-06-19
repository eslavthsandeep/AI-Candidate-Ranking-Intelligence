"""
career_scorer.py — Analyze career history for role fit.

Evaluates title relevance, career trajectory, experience years,
industry/domain match, production deployment signals, job-hopping
patterns, consulting-only career penalty, and AI/ML description
relevance.

Returns a normalized 0-100 score plus a detailed breakdown dict.
"""

from __future__ import annotations

import re
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    TITLE_TIERS,
    CONSULTING_COMPANIES,
    PRODUCTION_KEYWORDS,
    AI_ML_KEYWORDS,
)


def _get_title_tier(title: str | None) -> int:
    """Return tier (1-5) for a title. Default 5 for unrecognized titles."""
    if not title:
        return 5
    t = title.strip().lower()
    # Exact match first
    if t in TITLE_TIERS:
        return TITLE_TIERS[t]
    # Substring match
    for pattern, tier in TITLE_TIERS.items():
        if pattern in t:
            return tier
    return 5


def _is_consulting_company(company: str | None) -> bool:
    if not company:
        return False
    return company.strip().lower() in CONSULTING_COMPANIES


def _count_keyword_hits(text: str | None, keywords: set[str]) -> int:
    """Count how many distinct keywords appear in the text.

    Single-word keywords use exact word matching (tokenized) to prevent
    substring collisions like 'api' matching 'rapid'.
    Multi-word/compound keywords use substring matching.
    """
    if not text:
        return 0
    text_lower = text.lower()
    words = set(re.findall(r'[a-zA-Z0-9\-\+#/.]+', text_lower))

    hits = 0
    for kw in keywords:
        kw_clean = kw.lower()
        if ' ' in kw_clean:
            # Multi-word phrase → substring match
            if kw_clean in text_lower:
                hits += 1
        else:
            # Single word → exact word match
            if kw_clean in words:
                hits += 1
    return hits


def _parse_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def score_career(candidate: dict) -> dict:
    """
    Score career history for role fit.

    Returns dict with:
        - score (float 0-100)
        - title_score (float): best title relevance
        - trajectory_score (float): career direction
        - experience_fit (float): years match
        - production_score (float): production signals
        - description_relevance (float): AI/ML description match
        - consulting_penalty (float): penalty for consulting-only
        - hopping_penalty (float): penalty for frequent switching
        - industry_score (float): product co vs services
    """
    if not isinstance(candidate, dict):
        return _empty_result()
    profile = candidate.get("profile") or {}
    if not isinstance(profile, dict):
        profile = {}
    career = candidate.get("career_history") or []
    if not isinstance(career, list):
        career = []
    yoe = profile.get("years_of_experience") or 0

    if not career:
        return _empty_result()

    # ── 1. Title relevance (0-25) ────────────────────────────
    best_tier = 5
    current_tier = 5
    for i, role in enumerate(career):
        if not isinstance(role, dict):
            continue
        t = _get_title_tier(role.get("title"))
        if t < best_tier:
            best_tier = t
        if role.get("is_current", False) or i == 0:
            current_tier = t

    # Tier 1=25, 2=20, 3=12, 4=5, 5=0
    tier_to_score = {1: 25, 2: 20, 3: 12, 4: 5, 5: 0}
    title_score = tier_to_score.get(best_tier, 0)

    # Extra boost if current role is high-tier
    if current_tier <= 2 and best_tier <= 2:
        title_score = min(title_score + 3, 25)

    # ── 2. Career trajectory (0-15) ──────────────────────────
    trajectory_score = 0.0
    if len(career) >= 2:
        tiers = [_get_title_tier(r.get("title", "")) for r in career]
        # Check if trending towards more relevant roles
        # (lower tier number = better)
        recent_avg = sum(tiers[:min(2, len(tiers))]) / min(2, len(tiers))
        older_avg = sum(tiers[2:]) / max(len(tiers) - 2, 1) if len(tiers) > 2 else recent_avg

        if recent_avg < older_avg:
            trajectory_score = 12  # improving trajectory
        elif recent_avg == older_avg:
            if recent_avg <= 2:
                trajectory_score = 10  # stable and strong
            elif recent_avg <= 3:
                trajectory_score = 7
            else:
                trajectory_score = 3
        else:
            trajectory_score = 2  # declining (moved away from AI)

        # Bonus for staying in AI throughout career
        if all(t <= 2 for t in tiers):
            trajectory_score = 15
    else:
        # Single role
        if best_tier <= 2:
            trajectory_score = 10
        elif best_tier <= 3:
            trajectory_score = 6
        else:
            trajectory_score = 2

    # ── 3. Experience years fit (0-15) ────────────────────────
    # Sweet spot: 5-9 years
    if 5 <= yoe <= 9:
        experience_fit = 15
    elif 4 <= yoe < 5 or 9 < yoe <= 12:
        experience_fit = 12
    elif 3 <= yoe < 4 or 12 < yoe <= 15:
        experience_fit = 8
    elif 2 <= yoe < 3:
        experience_fit = 5
    elif yoe > 15:
        experience_fit = 6
    else:
        experience_fit = 2

    # ── 4. Production deployment signals (0-15) ──────────────
    production_hits = 0
    total_desc_len = 0
    for role in career:
        if not isinstance(role, dict):
            continue
        desc = role.get("description") or ""
        total_desc_len += len(desc)
        production_hits += _count_keyword_hits(desc, PRODUCTION_KEYWORDS)

    if production_hits >= 8:
        production_score = 15
    elif production_hits >= 5:
        production_score = 12
    elif production_hits >= 3:
        production_score = 8
    elif production_hits >= 1:
        production_score = 4
    else:
        production_score = 0

    # ── 5. Career description AI/ML relevance (0-15) ─────────
    ml_hits = 0
    for role in career:
        if not isinstance(role, dict):
            continue
        desc = role.get("description") or ""
        ml_hits += _count_keyword_hits(desc, AI_ML_KEYWORDS)

    if ml_hits >= 15:
        description_relevance = 15
    elif ml_hits >= 10:
        description_relevance = 12
    elif ml_hits >= 6:
        description_relevance = 9
    elif ml_hits >= 3:
        description_relevance = 5
    elif ml_hits >= 1:
        description_relevance = 2
    else:
        description_relevance = 0

    # ── 6. Industry / domain match (0-8) ─────────────────────
    product_co_roles = 0
    service_co_roles = 0
    for role in career:
        if not isinstance(role, dict):
            continue
        company = role.get("company") or ""
        industry = (role.get("industry") or "").lower()
        if _is_consulting_company(company):
            service_co_roles += 1
        elif industry in ("it services", "consulting", "staffing"):
            service_co_roles += 1
        else:
            product_co_roles += 1

    if product_co_roles > 0 and service_co_roles == 0:
        industry_score = 8
    elif product_co_roles > service_co_roles:
        industry_score = 6
    elif product_co_roles == service_co_roles:
        industry_score = 4
    elif product_co_roles > 0:
        industry_score = 2
    else:
        industry_score = 0  # all consulting

    # ── 7. Consulting-only penalty (0 to -10) ────────────────
    consulting_penalty = 0.0
    if len(career) > 0 and service_co_roles == len(career):
        consulting_penalty = -10.0
    elif len(career) > 1 and service_co_roles >= len(career) - 1:
        consulting_penalty = -5.0

    # ── 8. Job hopping penalty (0 to -7) ─────────────────────
    hopping_penalty = 0.0
    if len(career) >= 2:
        durations = [r.get("duration_months") or 0 if isinstance(r, dict) else 0 for r in career]
        # Exclude current role from avg tenure calc
        non_current = [
            d for r, d in zip(career, durations) if isinstance(r, dict) and not r.get("is_current", False)
        ]
        if non_current:
            avg_tenure = sum(non_current) / len(non_current)
            if avg_tenure < 12:
                hopping_penalty = -7
            elif avg_tenure < 18:
                hopping_penalty = -4
            elif avg_tenure < 24:
                hopping_penalty = -1

        # Check total number of roles vs years
        if yoe > 0 and len(career) / yoe > 0.8:
            hopping_penalty = min(hopping_penalty, -5)

    # ── Combine ──────────────────────────────────────────────
    raw = (
        title_score
        + trajectory_score
        + experience_fit
        + production_score
        + description_relevance
        + industry_score
        + consulting_penalty
        + hopping_penalty
    )

    # Normalize to 0-100
    # Max possible: 25 + 15 + 15 + 15 + 15 + 8 = 93
    final_score = max(0.0, min(raw / 93.0 * 100.0, 100.0))

    return {
        "score": round(final_score, 2),
        "title_score": title_score,
        "best_tier": best_tier,
        "current_tier": current_tier,
        "trajectory_score": trajectory_score,
        "experience_fit": experience_fit,
        "production_score": production_score,
        "description_relevance": description_relevance,
        "industry_score": industry_score,
        "consulting_penalty": consulting_penalty,
        "hopping_penalty": hopping_penalty,
        "production_hits": production_hits,
        "ml_hits": ml_hits,
        "num_roles": len(career),
    }


def _empty_result() -> dict:
    return {
        "score": 0.0,
        "title_score": 0,
        "best_tier": 5,
        "current_tier": 5,
        "trajectory_score": 0,
        "experience_fit": 0,
        "production_score": 0,
        "description_relevance": 0,
        "industry_score": 0,
        "consulting_penalty": 0,
        "hopping_penalty": 0,
        "production_hits": 0,
        "ml_hits": 0,
        "num_roles": 0,
    }
