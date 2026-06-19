"""
reasoning.py — Evidence-linked recruiter reasoning strings.

Each summary cites strengths, risks, and a verdict tied to score signals.
Deterministic per candidate_id for reproducible submissions.
"""

from __future__ import annotations

import hashlib


def _verdict(rank: int, composite: float, honeypot: bool, hard_dq: bool, must_have: int, title_tier: int) -> str:
    if honeypot or hard_dq:
        return "No (Flagged/Disqualified)"
    # Enforce strict "Strong Yes" criteria per evaluator's specification
    if composite >= 0.85 and must_have >= 4 and title_tier <= 2:
        return "Strong Yes"
    if rank <= 25 and composite >= 0.50 and must_have >= 2 and title_tier <= 3:
        return "Yes"
    if composite >= 0.25 and must_have >= 1:
        return "Maybe"
    return "No"


def _top_jd_skills(skills: list, limit: int = 3) -> list[str]:
    if not isinstance(skills, list):
        return []
    priority = {
        "expert": 4, "advanced": 3, "intermediate": 2, "beginner": 1,
    }
    jd_keywords = (
        "embedding", "retrieval", "pinecone", "weaviate", "qdrant", "faiss",
        "milvus", "python", "pytorch", "ranking", "ndcg", "nlp", "search",
        "vector", "sentence", "transformer", "llm", "lora", "xgboost",
    )
    scored = []
    for s in skills:
        if not isinstance(s, dict):
            continue
        name = s.get("name") or ""
        lower = name.lower()
        relevance = sum(1 for kw in jd_keywords if kw in lower)
        if relevance == 0:
            continue
        scored.append((
            relevance,
            priority.get(s.get("proficiency") or "", 0),
            s.get("duration_months") or 0,
            name,
        ))
    scored.sort(reverse=True)
    return [x[3] for x in scored[:limit]]


def generate_reasoning(
    candidate,
    skill_score,
    career_score,
    behavioral_score,
    education_score,
    honeypot_flag,
    rank,
    final_score,
    semantic_score=0.0,
    must_have_count=0,
    title_tier=5,
    disqualifier_reasons=None,
    semantic_terms=None,
    hard_disqualified=False,
):
    """Generate a recruiter-trustworthy, deterministic reasoning string."""
    if not isinstance(candidate, dict):
        return "Strengths: None. Evidence: Invalid candidate profile structure. Risks: Invalid data. Verdict: No."
    profile = candidate.get("profile") or {}
    if not isinstance(profile, dict):
        profile = {}
    title = profile.get("current_title") or "Professional"
    yoe = profile.get("years_of_experience") or 0
    company = profile.get("current_company") or "current company"
    location = profile.get("location") or "unknown location"
    skills = candidate.get("skills") or []
    if not isinstance(skills, list):
        skills = []
    signals = candidate.get("redrob_signals") or {}
    if not isinstance(signals, dict):
        signals = {}
    rr = (signals.get("recruiter_response_rate") or 0) * 100

    disqualifier_reasons = disqualifier_reasons or []
    semantic_terms = semantic_terms or []

    if honeypot_flag:
        return (
            f"Strengths: None. Evidence: Impossible timeline/fraud signals detected for {title} at {company}. "
            f"Risks: Profile failed honeypot/trap criteria. Verdict: No (Flagged/Disqualified)."
        )

    if hard_disqualified:
        risk = disqualifier_reasons[0] if disqualifier_reasons else "JD disqualifier triggered"
        return (
            f"Strengths: Minimal. Evidence: {title} at {company} ({yoe:.1f}y). "
            f"Risks: {risk}. Verdict: No (Flagged/Disqualified)."
        )

    jd_skills = _top_jd_skills(skills)
    skills_str = ", ".join(jd_skills) if jd_skills else "limited JD-aligned skills"
    verdict = _verdict(rank, final_score, honeypot_flag, hard_disqualified, must_have_count, title_tier)

    strengths = []
    if must_have_count >= 3:
        strengths.append(f"covers {must_have_count}/4 core AI must-have clusters ({skills_str})")
    elif must_have_count >= 1:
        strengths.append(f"partial must-have coverage ({must_have_count}/4 clusters)")
    if career_score >= 60:
        strengths.append("strong product/AI engineering career arc")
    if semantic_score >= 50 and semantic_terms:
        strengths.append("high semantic JD alignment")

    risks = list(disqualifier_reasons[:2])
    if must_have_count < 2:
        risks.append("thin coverage of core retrieval/ranking stack")
    if title_tier >= 4:
        risks.append("title not aligned with hands-on AI engineering requirements")
    if yoe < 5:
        risks.append("below preferred 5y experience floor")
    if signals.get("notice_period_days", 0) > 60:
        risks.append(f"notice period is {signals.get('notice_period_days')} days")

    if not risks:
        risks.append("no major red flags")

    strength_str = "; ".join(strengths) if strengths else "adjacent software experience"
    risk_str = "; ".join(risks[:2])

    # Standardized, highly clear recruiter notes format
    return (
        f"Strengths: {strength_str}. "
        f"Evidence: {title} at {company} ({yoe:.1f}y), based in {location}. "
        f"Risks: {risk_str}. "
        f"Verdict: {verdict}."
    )
