"""
disqualifier.py — Hard and soft JD disqualifier checks.

Applies role-specific gates before composite scoring so keyword-stuffed
or clearly misaligned profiles cannot reach the top 100.
"""

from __future__ import annotations

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    CONSULTING_COMPANIES,
    NON_TECH_TITLES,
    PRODUCTION_KEYWORDS,
    MUST_HAVE_CLUSTERS,
    SKILL_TO_CLUSTER,
    SKILL_ALIASES,
    TITLE_TIERS,
    REFERENCE_DATE,
)

_REFERENCE_DATE = REFERENCE_DATE

_CV_SPEECH_SKILLS = {
    "computer vision", "speech", "object detection", "image classification",
    "image segmentation", "yolo", "opencv", "asr", "tts", "robotics",
    "speech recognition", "text-to-speech", "vision", "cv", "image processing",
    "autonomous", "lidar"
}

_NLP_IR_CLUSTERS = {"Embeddings & Retrieval", "NLP & Text", "Ranking & Evaluation"}

_WRAPPER_KEYWORDS = {
    "langchain", "llamaindex", "openai api", "chatgpt", "gpt-4", "gpt-3",
    "prompt engineering", "wrapper",
}


def _canonicalize(name: str | None) -> str:
    if not name:
        return ""
    lower = name.strip().lower()
    return SKILL_ALIASES.get(lower, lower)


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


def _is_non_tech_title(title: str | None) -> bool:
    if not title:
        return False
    t = title.strip().lower()
    return any(nt in t for nt in NON_TECH_TITLES)


def _parse_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def _months_ago(date_str: str | None) -> float:
    dt = _parse_date(date_str)
    if dt is None:
        return 999
    return max((_REFERENCE_DATE - dt).days / 30.44, 0)


def _count_must_have_clusters(skills: list) -> int:
    covered: set[str] = set()
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


def _has_production_signals(text: str) -> bool:
    """Check if text contains production deployment keywords.

    Uses exact word matching for single-word keywords to avoid
    substring collisions (e.g. 'api' matching 'rapid').
    """
    import re
    lower = text.lower() if text else ""
    words = set(re.findall(r'[a-zA-Z0-9\-\+#/.]+', lower)) if lower else set()
    for kw in PRODUCTION_KEYWORDS:
        kw_clean = kw.lower()
        if ' ' in kw_clean:
            if kw_clean in lower:
                return True
        else:
            if kw_clean in words:
                return True
    return False


def check_disqualifiers(candidate: dict, skill_result: dict | None = None) -> dict:
    """
    Evaluate JD disqualifiers.

    Returns:
        - hard_disqualified (bool): score forced to 0
        - soft_penalty (float): multiplier in (0, 1]
        - reasons (list[str]): human-readable disqualifier notes
    """
    profile = candidate.get("profile") or {}
    career = candidate.get("career_history") or []
    skills = candidate.get("skills") or []
    title = profile.get("current_title") or ""
    title_tier = _title_tier(title)
    must_have_count = (
        skill_result.get("must_have_count", 0)
        if skill_result
        else _count_must_have_clusters(skills)
    )

    reasons: list[str] = []
    hard = False
    soft_penalty = 1.0

    # ── Hard: non-tech title + keyword stuffing ─────────────────
    if _is_non_tech_title(title) and must_have_count >= 3:
        hard = True
        reasons.append("Non-technical title with stacked AI skill keywords")

    expert_skills = [
        s for s in skills
        if isinstance(s, dict) and s.get("proficiency") in ("expert", "advanced")
    ]
    if _is_non_tech_title(title) and len(expert_skills) >= 5:
        hard = True
        reasons.append("Non-technical role with many expert-level AI skills")

    # ── Hard: consulting-only entire career ─────────────────────
    if career:
        valid_roles = [r for r in career if isinstance(r, dict)]
        consulting_roles = sum(
            1 for r in valid_roles
            if (r.get("company") or "").strip().lower() in CONSULTING_COMPANIES
            or (r.get("industry") or "").lower() in ("it services", "consulting", "staffing")
        )
        if valid_roles and consulting_roles == len(valid_roles) and must_have_count < 3:
            hard = True
            reasons.append("Entire career at consulting firms without core AI fit")

    # ── Hard: CV/Speech-only without NLP/IR depth ───────────────
    canonical_skills = {_canonicalize(s.get("name")) for s in skills if isinstance(s, dict)}
    has_cv_speech = bool(canonical_skills & _CV_SPEECH_SKILLS)
    has_nlp_ir = False
    for s in skills:
        if not isinstance(s, dict):
            continue
        canonical = _canonicalize(s.get("name"))
        if canonical in SKILL_TO_CLUSTER:
            cluster, _ = SKILL_TO_CLUSTER[canonical]
            if cluster in _NLP_IR_CLUSTERS:
                has_nlp_ir = True
                break
    summary_headline = (
        (profile.get("summary") or "") + " " + (profile.get("headline") or "")
    ).lower()
    if not has_nlp_ir:
        has_nlp_ir = any(
            kw in summary_headline
            for kw in ("nlp", "retrieval", "embedding", "search", "ranking", "ir ")
        )

    if has_cv_speech and not has_nlp_ir and must_have_count < 2:
        hard = True
        reasons.append("CV/Speech focus without NLP/IR or retrieval experience")

    deductions = 0.0

    # ── Soft: no production signals in last 18 months ───────────
    recent_roles = [
        r for r in career
        if isinstance(r, dict) and (r.get("is_current") or _months_ago(r.get("end_date") or r.get("start_date")) <= 18)
    ]
    recent_text = " ".join(
        (r.get("description") or "") + " " + (r.get("title") or "")
        for r in recent_roles if isinstance(r, dict)
    )
    if recent_roles and not _has_production_signals(recent_text):
        deductions += 0.25
        reasons.append("No production-shipping signals in the last 18 months")

    # ── Soft: recent LangChain/OpenAI wrapper-only profile ──────
    if recent_roles:
        recent_desc = recent_text.lower()
        wrapper_hits = sum(1 for kw in _WRAPPER_KEYWORDS if kw in recent_desc)
        production_hits = sum(1 for kw in PRODUCTION_KEYWORDS if kw in recent_desc)
        if wrapper_hits >= 2 and production_hits == 0 and must_have_count < 3:
            deductions += 0.30
            reasons.append("Recent profile looks like thin LLM-wrapper work")

    # ── Soft: LangChain experience less than 12 months ─────────
    langchain_under_12 = False
    for s in skills:
        if not isinstance(s, dict):
            continue
        s_name = (s.get("name") or "").lower()
        if "langchain" in s_name and (s.get("duration_months") or 0) < 12:
            langchain_under_12 = True
            break
    if langchain_under_12:
        deductions += 0.15
        reasons.append("Recent LangChain experience is less than 12 months")

    # ── Hard: low-tier title with weak must-have coverage ───────
    if title_tier >= 4 and must_have_count < 2:
        hard = True
        reasons.append("Role title not aligned with Senior AI Engineer requirements and has weak must-have coverage")

    # ── Soft: pure academic signal (research without production) ─
    academic_only = (
        any(kw in summary_headline for kw in ("phd research", "published papers", "thesis", "academic"))
        and not _has_production_signals(
            " ".join((r.get("description") or "") for r in career if isinstance(r, dict))
        )
        and must_have_count < 3
    )
    if academic_only:
        deductions += 0.25
        reasons.append("Academic/research profile without production shipping evidence")

    soft_penalty = max(0.20, 1.0 - deductions)

    return {
        "hard_disqualified": hard,
        "soft_penalty": soft_penalty,
        "reasons": reasons,
        "title_tier": title_tier,
        "must_have_count": must_have_count,
    }
