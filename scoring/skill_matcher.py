"""
skill_matcher.py — Score candidates on skill match to JD requirements.

Uses semantic skill clusters (NOT keyword matching) to determine how
well a candidate's listed skills align with the must-have and
nice-to-have requirements for the Senior AI Engineer role.

Returns a normalized 0-100 score.
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    SKILL_ALIASES,
    MUST_HAVE_CLUSTERS,
    NICE_TO_HAVE_CLUSTERS,
    SKILL_TO_CLUSTER,
    PROFICIENCY_MULTIPLIER,
    TITLE_TIERS,
    TITLE_SKILL_MULTIPLIER,
)


def _title_tier(title: str | None) -> int:
    if not title:
        return 5
    t = title.strip().lower()
    if t in TITLE_TIERS:
        return TITLE_TIERS[t]
    for pattern, tier in TITLE_TIERS.items():
        if pattern in t:
            return tier
    return 5


def _canonicalize_skill(name: str | None) -> str:
    """Map a raw skill name to its canonical form via aliases."""
    if not name:
        return ""
    lower = name.strip().lower()
    return SKILL_ALIASES.get(lower, lower)


def _proficiency_mult(proficiency: str | None) -> float:
    if not proficiency:
        return 0.5
    return PROFICIENCY_MULTIPLIER.get(proficiency.strip().lower(), 0.5)


def _duration_mult(duration_months: int | float | None) -> float:
    if duration_months is None:
        return 0.8
    if duration_months > 24:
        return 1.2
    elif duration_months >= 12:
        return 1.0
    else:
        return 0.8


def _endorsement_boost(endorsements: int | None) -> float:
    if endorsements is None:
        return 1.0
    return 1.1 if endorsements > 20 else 1.0


def score_skills(candidate: dict) -> dict:
    """
    Score a candidate's skill match to JD requirements.

    Returns a dict with:
        - score (float 0-100)
        - must_have_coverage (dict: cluster_name → best_score)
        - nice_to_have_coverage (dict: cluster_name → best_score)
        - matched_skills (list of matched skill names)
        - must_have_count (int: number of must-have clusters covered)
    """
    if not isinstance(candidate, dict):
        return {
            "score": 0.0,
            "must_have_coverage": {},
            "nice_to_have_coverage": {},
            "matched_skills": [],
            "must_have_count": 0,
            "title_tier": 5,
            "title_skill_multiplier": 0.25,
        }
    skills = candidate.get("skills") or []
    if not isinstance(skills, list):
        skills = []
    signals = candidate.get("redrob_signals") or {}
    if not isinstance(signals, dict):
        signals = {}
    assessment_scores = signals.get("skill_assessment_scores") or {}
    if not isinstance(assessment_scores, dict):
        assessment_scores = {}

    # Track best score per cluster
    must_have_scores: dict[str, float] = {c: 0.0 for c in MUST_HAVE_CLUSTERS}
    nice_have_scores: dict[str, float] = {c: 0.0 for c in NICE_TO_HAVE_CLUSTERS}
    matched_skills: list[str] = []

    for skill_entry in skills:
        if not isinstance(skill_entry, dict):
            continue
        raw_name = skill_entry.get("name") or ""
        canonical = _canonicalize_skill(raw_name)

        if canonical not in SKILL_TO_CLUSTER:
            continue

        cluster_name, is_must_have = SKILL_TO_CLUSTER[canonical]
        matched_skills.append(raw_name)

        # Base score from proficiency
        prof = skill_entry.get("proficiency") or "beginner"
        base = _proficiency_mult(prof)

        # Duration multiplier
        dur = skill_entry.get("duration_months") or 0
        dur_m = _duration_mult(dur)

        # Endorsement boost
        endorse = skill_entry.get("endorsements") or 0
        endorse_m = _endorsement_boost(endorse)

        # Assessment score integration
        assess_m = 1.0
        assess_score = assessment_scores.get(raw_name, -1)
        if assess_score >= 0:
            # Scale: 80+ excellent, 50-80 good, 30-50 moderate, <30 weak
            if assess_score >= 80:
                assess_m = 1.25
            elif assess_score >= 60:
                assess_m = 1.1
            elif assess_score >= 40:
                assess_m = 1.0
            elif assess_score >= 20:
                assess_m = 0.85
            else:
                assess_m = 0.6

        skill_score = base * dur_m * endorse_m * assess_m

        # Update cluster coverage with the best score for this cluster
        if is_must_have:
            if skill_score > must_have_scores[cluster_name]:
                must_have_scores[cluster_name] = skill_score
        else:
            if skill_score > nice_have_scores[cluster_name]:
                nice_have_scores[cluster_name] = skill_score

    # ── Compute final score ──────────────────────────────────
    # Must-have: 70 points max (17.5 per cluster)
    must_have_max_per = 17.5
    must_have_total = 0.0
    must_have_count = 0
    for cluster, best in must_have_scores.items():
        if best > 0:
            must_have_count += 1
            # cap individual contribution at must_have_max_per
            contribution = min(best * must_have_max_per, must_have_max_per)
            must_have_total += contribution

    # Bonus for covering all 4 must-have clusters
    if must_have_count == 4:
        must_have_total = min(must_have_total * 1.15, 70.0)
    elif must_have_count == 3:
        must_have_total = min(must_have_total * 1.05, 70.0)

    must_have_total = min(must_have_total, 70.0)

    # Nice-to-have: 30 points max
    nice_max_per = 30.0 / max(len(NICE_TO_HAVE_CLUSTERS), 1)
    nice_total = 0.0
    for cluster, best in nice_have_scores.items():
        if best > 0:
            contribution = min(best * nice_max_per, nice_max_per)
            nice_total += contribution

    nice_total = min(nice_total, 30.0)

    final_score = min(must_have_total + nice_total, 100.0)

    # Scale skill score by current title relevance to the JD
    current_title = (candidate.get("profile") or {}).get("current_title")
    tier = _title_tier(current_title)
    title_mult = TITLE_SKILL_MULTIPLIER.get(tier, 0.25)
    # Scale skill score by title tier multiplier to penalize keyword-stuffing in non-aligned roles
    final_score = round(final_score * title_mult, 2)

    return {
        "score": round(final_score, 2),
        "must_have_coverage": must_have_scores,
        "nice_to_have_coverage": nice_have_scores,
        "matched_skills": matched_skills,
        "must_have_count": must_have_count,
        "title_tier": tier,
        "title_skill_multiplier": title_mult,
    }
