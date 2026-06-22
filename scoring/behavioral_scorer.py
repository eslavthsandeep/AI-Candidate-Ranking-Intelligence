"""
behavioral_scorer.py — Score behavioral / engagement signals.

Produces both a raw 0-100 score and a multiplier [0.3, 1.5] that
gets applied on top of the composite score. The multiplier rewards
highly engaged, responsive, available candidates and penalizes
inactive or unresponsive ones.
"""

from __future__ import annotations

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PREFERRED_CITIES, PREFERRED_COUNTRY, REFERENCE_DATE

# Reference date for recency calculations
_NOW = REFERENCE_DATE


def _parse_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def _days_since(date_str: str | None) -> float:
    """Return days since the given date, or a large number if unknown."""
    dt = _parse_date(date_str)
    if dt is None:
        return 365  # assume stale
    delta = _NOW - dt
    return max(delta.days, 0)


def score_behavioral(candidate: dict) -> dict:
    """
    Score behavioral signals.

    Returns dict with:
        - score (float 0-100)
        - multiplier (float 0.3-1.5)
        - breakdown (dict of individual signal multipliers)
    """
    signals = candidate.get("redrob_signals", {})
    profile = candidate.get("profile", {})

    multipliers: dict[str, float] = {}
    raw_points = 0.0

    # ── 1. Recruiter response rate ───────────────────────────
    rrr = signals.get("recruiter_response_rate", -1)
    if rrr < 0:
        multipliers["recruiter_response"] = 0.95
    elif rrr < 0.2:
        multipliers["recruiter_response"] = 0.75
        raw_points += 2
    elif rrr < 0.5:
        multipliers["recruiter_response"] = 0.90
        raw_points += 6
    elif rrr < 0.7:
        multipliers["recruiter_response"] = 1.0
        raw_points += 10
    else:
        multipliers["recruiter_response"] = 1.08
        raw_points += 14

    # ── 2. Last active date (recency) ────────────────────────
    days_inactive = _days_since(signals.get("last_active_date"))
    if days_inactive <= 30:
        multipliers["recency"] = 1.0
        raw_points += 12
    elif days_inactive <= 90:
        multipliers["recency"] = 0.95
        raw_points += 9
    elif days_inactive <= 180:
        multipliers["recency"] = 0.85
        raw_points += 5
    else:
        multipliers["recency"] = 0.70
        raw_points += 1

    # ── 3. Open to work ──────────────────────────────────────
    otw = signals.get("open_to_work_flag", False)
    if otw:
        multipliers["open_to_work"] = 1.10
        raw_points += 10
    else:
        multipliers["open_to_work"] = 0.88
        raw_points += 3

    # ── 4. Profile completeness ──────────────────────────────
    completeness = signals.get("profile_completeness_score", 50)
    if completeness > 80:
        multipliers["completeness"] = 1.05
        raw_points += 8
    elif completeness >= 50:
        multipliers["completeness"] = 1.0
        raw_points += 5
    else:
        multipliers["completeness"] = 0.88
        raw_points += 2

    # ── 5. GitHub activity ───────────────────────────────────
    github = signals.get("github_activity_score", -1)
    if github < 0:
        multipliers["github"] = 0.92
        raw_points += 2
    elif github <= 20:
        multipliers["github"] = 1.0
        raw_points += 5
    elif github <= 50:
        multipliers["github"] = 1.05
        raw_points += 8
    else:
        multipliers["github"] = 1.15
        raw_points += 12

    # ── 6. Average response time ─────────────────────────────
    resp_time = signals.get("avg_response_time_hours", 999)
    if resp_time < 24:
        multipliers["response_time"] = 1.10
        raw_points += 10
    elif resp_time <= 72:
        multipliers["response_time"] = 1.0
        raw_points += 7
    elif resp_time <= 168:
        multipliers["response_time"] = 0.92
        raw_points += 4
    else:
        multipliers["response_time"] = 0.80
        raw_points += 1

    # ── 7. Interview completion rate ─────────────────────────
    icr = signals.get("interview_completion_rate", -1)
    if icr < 0:
        multipliers["interview_completion"] = 0.95
        raw_points += 3
    elif icr >= 0.8:
        multipliers["interview_completion"] = 1.10
        raw_points += 10
    elif icr >= 0.5:
        multipliers["interview_completion"] = 1.0
        raw_points += 6
    else:
        multipliers["interview_completion"] = 0.85
        raw_points += 2

    # ── 8. Notice period ─────────────────────────────────────
    notice = signals.get("notice_period_days", 90)
    if notice <= 30:
        multipliers["notice_period"] = 1.10
        raw_points += 10
    elif notice <= 60:
        multipliers["notice_period"] = 1.0
        raw_points += 7
    elif notice <= 90:
        multipliers["notice_period"] = 0.95
        raw_points += 4
    else:
        multipliers["notice_period"] = 0.88
        raw_points += 1

    # ── 9. Verified signals ──────────────────────────────────
    verified_count = sum([
        bool(signals.get("verified_email", False)),
        bool(signals.get("verified_phone", False)),
        bool(signals.get("linkedin_connected", False)),
    ])
    if verified_count >= 3:
        multipliers["verified"] = 1.05
        raw_points += 6
    elif verified_count >= 2:
        multipliers["verified"] = 1.0
        raw_points += 4
    elif verified_count >= 1:
        multipliers["verified"] = 0.97
        raw_points += 3
    else:
        multipliers["verified"] = 0.90
        raw_points += 1

    # ── 10. Saved by recruiters ──────────────────────────────
    saved = signals.get("saved_by_recruiters_30d", 0)
    if saved > 10:
        multipliers["saved_by_recruiters"] = 1.10
        raw_points += 8
    elif saved >= 5:
        multipliers["saved_by_recruiters"] = 1.05
        raw_points += 5
    else:
        multipliers["saved_by_recruiters"] = 1.0
        raw_points += 2

    # ── 11. Location ─────────────────────────────────────────
    location = profile.get("location", "").lower()
    country = profile.get("country", "").lower()

    if any(city in location for city in PREFERRED_CITIES):
        multipliers["location"] = 1.10
        raw_points += 10
    elif country == PREFERRED_COUNTRY:
        multipliers["location"] = 1.05
        raw_points += 7
    else:
        multipliers["location"] = 0.95
        raw_points += 3

    # ── 12. Preferred work mode / relocation ──────────────────
    pwm = signals.get("preferred_work_mode", "").lower()
    wtr = signals.get("willing_to_relocate", True)
    if pwm == "remote" and not wtr:
        multipliers["work_mode"] = 0.85
        raw_points += 1
    elif pwm in ("hybrid", "onsite", "flexible") or wtr:
        multipliers["work_mode"] = 1.05
        raw_points += 9
    else:
        multipliers["work_mode"] = 0.95
        raw_points += 5

    # ── 13. Profile views (social proof) ──────────────────────
    views = signals.get("profile_views_received_30d", 0)
    if views > 50:
        multipliers["profile_views"] = 1.08
        raw_points += 8
    elif views >= 20:
        multipliers["profile_views"] = 1.03
        raw_points += 6
    elif views >= 5:
        multipliers["profile_views"] = 1.0
        raw_points += 4
    else:
        multipliers["profile_views"] = 0.95
        raw_points += 1

    # ── 14. Search appearances ────────────────────────────────
    appearances = signals.get("search_appearance_30d", 0)
    if appearances > 200:
        multipliers["search_appearances"] = 1.08
        raw_points += 8
    elif appearances >= 50:
        multipliers["search_appearances"] = 1.03
        raw_points += 6
    elif appearances >= 10:
        multipliers["search_appearances"] = 1.0
        raw_points += 4
    else:
        multipliers["search_appearances"] = 0.95
        raw_points += 1

    # ── 15. Connection count ──────────────────────────────────
    connections = signals.get("connection_count", 0)
    if connections > 500:
        multipliers["connections"] = 1.06
        raw_points += 6
    elif connections >= 150:
        multipliers["connections"] = 1.02
        raw_points += 4
    elif connections >= 50:
        multipliers["connections"] = 1.0
        raw_points += 2
    else:
        multipliers["connections"] = 0.95
        raw_points += 0

    # ── 16. Offer acceptance rate ─────────────────────────────
    oar = signals.get("offer_acceptance_rate", -1)
    if oar < 0:
        multipliers["offer_acceptance"] = 1.0
        raw_points += 4
    elif oar >= 0.8:
        multipliers["offer_acceptance"] = 1.06
        raw_points += 6
    elif oar >= 0.5:
        multipliers["offer_acceptance"] = 1.0
        raw_points += 4
    else:
        multipliers["offer_acceptance"] = 0.88
        raw_points += 1

    # ── 17. Languages (English proficiency) ───────────────────
    langs = candidate.get("languages") or []
    english_prof = "none"
    for l in langs:
        if isinstance(l, dict):
            lang_name = (l.get("language") or "").lower()
            if "english" in lang_name:
                english_prof = (l.get("proficiency") or "none").lower()
                break

    if english_prof in ("professional", "native"):
        multipliers["english"] = 1.05
        raw_points += 6
    elif english_prof == "conversational":
        multipliers["english"] = 1.02
        raw_points += 4
    elif english_prof == "basic":
        multipliers["english"] = 0.95
        raw_points += 1
    else:
        multipliers["english"] = 0.98
        raw_points += 2

    # ── 18. Applications submitted in last 30 days ───────────────────
    apps = signals.get("applications_submitted_30d", -1)
    if apps < 0:
        multipliers["applications_submitted"] = 1.0
        raw_points += 2
    elif apps >= 12:
        multipliers["applications_submitted"] = 1.05
        raw_points += 5
    elif apps >= 5:
        multipliers["applications_submitted"] = 1.0
        raw_points += 3
    elif apps >= 1:
        multipliers["applications_submitted"] = 0.98
        raw_points += 1
    else:
        multipliers["applications_submitted"] = 0.95
        raw_points += 0

    # ── 19. Endorsements received ────────────────────────────────────
    endorsements = signals.get("endorsements_received", -1)
    if endorsements < 0:
        multipliers["endorsements_received"] = 1.0
        raw_points += 2
    elif endorsements >= 50:
        multipliers["endorsements_received"] = 1.06
        raw_points += 6
    elif endorsements >= 20:
        multipliers["endorsements_received"] = 1.02
        raw_points += 4
    elif endorsements >= 1:
        multipliers["endorsements_received"] = 1.0
        raw_points += 2
    else:
        multipliers["endorsements_received"] = 0.96
        raw_points += 0

    # ── Compute combined multiplier ──────────────────────────
    combined_mult = 1.0
    for m in multipliers.values():
        combined_mult *= m

    # Clamp multiplier to [0.6, 1.3] — tight enough to be a tie-breaker,
    # not so wide that it overrides strong credentials
    combined_mult = max(0.6, min(combined_mult, 1.3))

    # Normalize raw score (max possible ~164 → 100)
    max_raw = 164.0
    final_score = min(raw_points / max_raw * 100.0, 100.0)

    return {
        "score": round(final_score, 2),
        "multiplier": round(combined_mult, 4),
        "breakdown": multipliers,
    }
