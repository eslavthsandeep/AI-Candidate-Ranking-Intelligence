import logging

logger = logging.getLogger(__name__)

def detect_honeypot(candidate):
    """
    Detect impossible profiles (honeypots).
    Returns (score, is_honeypot) where score is 0-1 and is_honeypot is a boolean.
    """
    profile = candidate.get('profile', {})
    yoe = profile.get('years_of_experience', 0)
    career_history = candidate.get('career_history', [])
    skills = candidate.get('skills', [])
    signals = candidate.get('redrob_signals', {})
    
    # 1. Total career duration vs declared YOE
    total_months_career = sum([role.get('duration_months', 0) for role in career_history])
    calculated_yoe = total_months_career / 12.0
    
    # If they claim >3 years more experience than their career history shows
    if yoe > (calculated_yoe + 3) and yoe > 5:
        logger.debug(f"Honeypot detected: YOE {yoe} > calculated {calculated_yoe}")
        return 1.0, True
        
    # 2. Too many expert skills with 0 duration
    expert_zero_duration_count = sum(1 for s in skills if s.get('proficiency') == 'expert' and s.get('duration_months', 0) == 0)
    if expert_zero_duration_count >= 8:
        logger.debug("Honeypot detected: Too many expert skills with 0 duration")
        return 1.0, True
        
    # 3. High proficiency but low assessment score
    expert_low_assessment_count = sum(1 for s in skills if s.get('proficiency') == 'expert' and signals.get('skill_assessment_scores', {}).get(s.get('name', ''), 100) < 30)
    if expert_low_assessment_count > 0:
        logger.debug("Honeypot detected: Expert proficiency but low assessment score")
        return 1.0, True
        
    # 4. Keyword stuffer trap: Non-tech title with perfect AI skill list
    title = profile.get('current_title', '').lower()
    non_tech_titles = ['marketing', 'hr', 'accountant', 'sales', 'civil', 'mechanical']
    is_non_tech = any(t in title for t in non_tech_titles)
    
    ai_skills = ['machine learning', 'deep learning', 'nlp', 'python', 'pytorch', 'tensorflow', 'embeddings']
    expert_ai_count = sum(1 for s in skills if s.get('name', '').lower() in ai_skills and s.get('proficiency') in ['expert', 'advanced'])
    
    if is_non_tech and expert_ai_count >= 5:
        logger.debug("Honeypot detected: Keyword stuffer (non-tech title + expert AI skills)")
        return 1.0, True
        
    # 5. All skills have 0 endorsements and 0 duration but high proficiency
    high_prof_skills = [s for s in skills if s.get('proficiency') in ['expert', 'advanced']]
    if len(high_prof_skills) >= 5 and all(s.get('endorsements', 0) == 0 and s.get('duration_months', 0) == 0 for s in high_prof_skills):
        logger.debug("Honeypot detected: High proficiency skills but 0 endorsements and 0 duration")
        return 1.0, True

    return 0.0, False
