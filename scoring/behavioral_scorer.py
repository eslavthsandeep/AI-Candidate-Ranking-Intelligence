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

from config import PREFERRED_CITIES, PREFERRED_COUNTRY

# Reference date for recency calculations
_NOW = datetime(2026, 6, 8)


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

    # ── Compute combined multiplier ──────────────────────────
    combined_mult = 1.0
    for m in multipliers.values():
        combined_mult *= m

    # Clamp multiplier to [0.3, 1.5]
    combined_mult = max(0.3, min(combined_mult, 1.5))

    # Normalize raw score (max possible ~120 → 100)
    max_raw = 120.0
    final_score = min(raw_points / max_raw * 100.0, 100.0)

    return {
        "score": round(final_score, 2),
        "multiplier": round(combined_mult, 4),
        "breakdown": multipliers,
    }
