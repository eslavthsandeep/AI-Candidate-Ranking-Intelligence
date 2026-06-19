import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    NON_TECH_TITLES,
    SKILL_ALIASES,
    SKILL_TO_CLUSTER,
    MUST_HAVE_CLUSTERS,
)

logger = logging.getLogger(__name__)


def _canonicalize(name: str | None) -> str:
    if not name:
        return ""
    lower = name.strip().lower()
    return SKILL_ALIASES.get(lower, lower)


def _is_non_tech_title(title: str | None) -> bool:
    if not title:
        return False
    t = title.strip().lower()
    return any(nt in t for nt in NON_TECH_TITLES)


def _count_must_have_clusters(skills: list) -> int:
    covered = set()
    if not isinstance(skills, list):
        return 0
    for skill in skills:
        if not isinstance(skill, dict):
            continue
        canonical = _canonicalize(skill.get("name"))
        if canonical in SKILL_TO_CLUSTER:
            cluster, is_must = SKILL_TO_CLUSTER[canonical]
            if is_must:
                covered.add(cluster)
    return len(covered)


def detect_honeypot(candidate):
    """
    Detect impossible or fabricated profiles (honeypots).
    Returns (score, is_honeypot) where score is 0-1 and is_honeypot is a boolean.
    """
    if not isinstance(candidate, dict):
        return 0.0, False
    profile = candidate.get("profile") or {}
    if not isinstance(profile, dict):
        profile = {}
    yoe = profile.get("years_of_experience") or 0
    career_history = candidate.get("career_history") or []
    if not isinstance(career_history, list):
        career_history = []
    skills = candidate.get("skills") or []
    if not isinstance(skills, list):
        skills = []
    signals = candidate.get("redrob_signals") or {}
    if not isinstance(signals, dict):
        signals = {}
    title = (profile.get("current_title") or "").lower()
    summary = (profile.get("summary") or "").lower()
    assessment_scores = signals.get("skill_assessment_scores") or {}
    if not isinstance(assessment_scores, dict):
        assessment_scores = {}

    # 1. Total career duration vs declared YOE
    total_months_career = sum(role.get("duration_months") or 0 if isinstance(role, dict) else 0 for role in career_history)
    calculated_yoe = total_months_career / 12.0

    if yoe > (calculated_yoe + 3) and yoe > 5:
        logger.debug(f"Honeypot detected: YOE {yoe} > calculated {calculated_yoe}")
        return 1.0, True

    # 2. Too many expert skills with 0 duration
    expert_zero_duration_count = sum(
        1 for s in skills if isinstance(s, dict) and s.get("proficiency") == "expert" and (s.get("duration_months") or 0) == 0
    )
    if expert_zero_duration_count >= 8:
        logger.debug("Honeypot detected: Too many expert skills with 0 duration")
        return 1.0, True

    # 3. High proficiency but low assessment score
    expert_low_assessment_count = sum(
        1 for s in skills
        if isinstance(s, dict) and s.get("proficiency") == "expert"
        and assessment_scores.get(s.get("name") or "", 100) < 30
    )
    if expert_low_assessment_count >= 3:
        logger.debug("Honeypot detected: Expert proficiency but low assessment score")
        return 1.0, True

    # Check coverage of must-have clusters at expert level
    expert_clusters = set()
    for s in skills:
        if isinstance(s, dict) and s.get("proficiency") == "expert":
            canonical = _canonicalize(s.get("name"))
            if canonical in SKILL_TO_CLUSTER:
                cluster_name, is_must = SKILL_TO_CLUSTER[canonical]
                if is_must:
                    expert_clusters.add(cluster_name)

    # 4. Keyword stuffer trap: Non-tech title with perfect AI skill list
    if _is_non_tech_title(title) and len(expert_clusters) >= 4:
        logger.debug("Honeypot detected: Non-tech title claiming expert in all must-have clusters")
        return 1.0, True

    # 5. Expert skills with 0 duration AND assessment < 40
    expert_zero_low_assessment = sum(
        1 for s in skills
        if isinstance(s, dict) and s.get("proficiency") == "expert"
        and (s.get("duration_months") or 0) == 0
        and assessment_scores.get(s.get("name") or "", 100) < 40
    )
    if expert_zero_low_assessment >= 2:
        logger.debug("Honeypot detected: Multiple expert skills with 0 duration and low assessment scores")
        return 1.0, True

    # 6. Summary vs skills mismatch: Non-tech summary with expert ML skills
    non_tech_summary_patterns = [r'\bmarketing\b', r'\baccounting\b', r'\bconstruction\b', r'\bcivil engineering\b', r'\bhr\b', r'\bsales representative\b']
    import re
    has_non_tech_summary = any(re.search(pat, summary) for pat in non_tech_summary_patterns)
    if has_non_tech_summary and len(expert_clusters) >= 2:
        logger.debug("Honeypot detected: Profile summary describes non-tech role, but lists expert ML skill clusters")
        return 1.0, True

    # 7. All high-proficiency skills have 0 endorsements and 0 duration
    high_prof_skills = [s for s in skills if isinstance(s, dict) and s.get("proficiency") in ("expert", "advanced")]
    if (
        len(high_prof_skills) >= 5
        and all(
            (s.get("endorsements") or 0) == 0 and (s.get("duration_months") or 0) == 0
            for s in high_prof_skills if isinstance(s, dict)
        )
    ):
        logger.debug("Honeypot detected: High proficiency skills but 0 endorsements and 0 duration")
        return 1.0, True

    # 8. Impossible must-have cluster coverage for career length
    must_have_count = len([c for c in expert_clusters if c in MUST_HAVE_CLUSTERS])
    if yoe < 3 and must_have_count >= len(MUST_HAVE_CLUSTERS):
        logger.debug("Honeypot detected: Full must-have coverage with very low YOE")
        return 1.0, True

    # 9. Assessment contradictions across many skills
    contradictions = sum(
        1 for s in skills
        if isinstance(s, dict) and s.get("proficiency") in ("expert", "advanced")
        and assessment_scores.get(s.get("name") or "", -1) >= 0
        and assessment_scores.get(s.get("name") or "", 100) < 25
    )
    if contradictions >= 4:
        logger.debug("Honeypot detected: Multiple assessment contradictions")
        return 1.0, True

    return 0.0, False
