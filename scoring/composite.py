import logging
from config import COMPOSITE_WEIGHTS

logger = logging.getLogger(__name__)


def calculate_composite_score(
    candidate,
    skill_score,
    career_score,
    behavioral_score,
    behavioral_multiplier,
    honeypot_score,
    honeypot_flag,
    education_score,
    semantic_score,
    hard_disqualified=False,
    soft_penalty=1.0,
):
    """
    Calculate the final composite score for a candidate.

    Weights (from config):
    - skill_match = 0.30
    - career = 0.35
    - behavioral = 0.12
    - education = 0.08
    - semantic = 0.15
    """
    if honeypot_flag or hard_disqualified:
        return 0.0

    skill_score = max(0, min(100, skill_score))
    career_score = max(0, min(100, career_score))
    behavioral_score = max(0, min(100, behavioral_score))
    education_score = max(0, min(100, education_score))
    semantic_score = max(0, min(100, semantic_score))

    w = COMPOSITE_WEIGHTS

    raw_score = (
        w["skill_match"] * skill_score
        + w["career"] * career_score
        + w["behavioral"] * behavioral_score
        + w["education"] * education_score
        + w.get("semantic", 0.0) * semantic_score
    )

    # Apply symmetric scaling for the behavioral multiplier (maps [0.6, 1.3] to [0.88, 1.09])
    adjusted = raw_score * (0.7 + 0.3 * behavioral_multiplier)

    adjusted *= max(0.1, min(1.0, soft_penalty))

    normalized_score = max(0.0, min(1.0, adjusted / 109.0))
    return normalized_score
