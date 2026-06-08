"""
scoring — Sub-package containing all individual scoring modules for
the Redrob AI Candidate Ranking pipeline.

Modules:
    skill_matcher      – Match candidate skills to JD requirements
    career_scorer      – Evaluate career history and trajectory
    behavioral_scorer  – Score engagement and behavioral signals
    honeypot_detector  – Flag impossible / fabricated profiles
    education_scorer   – Score education and certifications
    composite          – Combine sub-scores into final ranking score
    reasoning          – Generate human-readable reasoning strings
"""

from .skill_matcher import score_skills
from .career_scorer import score_career
from .behavioral_scorer import score_behavioral
from .honeypot_detector import detect_honeypot
from .education_scorer import score_education
from .composite import calculate_composite_score
from .reasoning import generate_reasoning

__all__ = [
    "score_skills",
    "score_career",
    "score_behavioral",
    "detect_honeypot",
    "score_education",
    "calculate_composite_score",
    "generate_reasoning",
]
