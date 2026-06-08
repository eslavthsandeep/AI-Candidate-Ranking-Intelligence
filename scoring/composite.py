import logging

logger = logging.getLogger(__name__)

def calculate_composite_score(candidate, skill_score, career_score, behavioral_score, behavioral_multiplier, honeypot_score, honeypot_flag, education_score):
    """
    Calculate the final composite score for a candidate.
    
    Weights: 
    - skill_match = 0.35
    - career = 0.40 (combining career & trajectory for simplicity here if career_scorer handles both, or adjust if separated)
    - behavioral = 0.15
    - education = 0.10
    
    In the prompt, it was:
    - skill_match=0.35, career=0.25, trajectory=0.15, behavioral=0.15, education=0.10
    Assuming career_score here represents the combined career & trajectory (40% total)
    """
    
    # If the candidate is flagged as a honeypot, the score is 0
    if honeypot_flag:
        return 0.0

    # Ensure all scores are between 0 and 100
    skill_score = max(0, min(100, skill_score))
    career_score = max(0, min(100, career_score))
    behavioral_score = max(0, min(100, behavioral_score))
    education_score = max(0, min(100, education_score))

    # Calculate raw score (0-100)
    raw_score = (
        0.35 * skill_score +
        0.40 * career_score +
        0.15 * behavioral_score +
        0.10 * education_score
    )

    # Apply behavioral multiplier
    final_score = raw_score * behavioral_multiplier

    # Normalize to 0-1
    normalized_score = max(0.0, min(1.0, final_score / 100.0))

    return normalized_score
