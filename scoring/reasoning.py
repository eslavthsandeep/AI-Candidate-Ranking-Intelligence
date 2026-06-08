import random

def generate_reasoning(candidate, skill_score, career_score, behavioral_score, education_score, honeypot_flag, rank, final_score):
    """
    Generate a specific, varied reasoning string for a candidate.
    """
    profile = candidate.get('profile', {})
    title = profile.get('current_title', 'Professional')
    yoe = profile.get('years_of_experience', 0)
    company = profile.get('current_company', 'their current company')
    location = profile.get('location', 'their location')
    
    skills = candidate.get('skills', [])
    top_skills = [s['name'] for s in sorted(skills, key=lambda x: (x.get('proficiency', '') == 'expert', x.get('duration_months', 0)), reverse=True)[:3]]
    skills_str = ", ".join(top_skills) if top_skills else "general tech skills"
    
    signals = candidate.get('redrob_signals', {})
    rr = signals.get('recruiter_response_rate', 0) * 100
    
    # Check for gaps
    gaps = []
    if yoe < 5:
        gaps.append("slightly light on total experience")
    elif yoe > 10:
        gaps.append("might be overqualified or senior for a hands-on role")
        
    if signals.get('notice_period_days', 0) > 30:
        gaps.append(f"notice period is {signals.get('notice_period_days')} days")
        
    if career_score < 50:
        gaps.append("career history lacks strong product/AI focus")
        
    gap_str = random.choice(gaps) if gaps else "no obvious red flags"

    patterns = [
        f"{title} with {yoe}y exp; shipped systems at {company}; strong {skills_str}. Concern: {gap_str}.",
        f"Deep AI/ML background ({yoe}y); solid fit with {skills_str}. Good behavioral signals (response rate {rr:.0f}%). Location: {location}.",
        f"Strong {title} profile featuring {skills_str}. Experience ({yoe}y) aligns well. Note: {gap_str}.",
        f"Solid technical foundation with {skills_str} at {company}. {yoe} years of relevant experience. Concern: {gap_str}.",
        f"Good match for the role. Brings {yoe}y of experience as a {title}, utilizing {skills_str}. Behavioral signals are decent (response {rr:.0f}%)."
    ]
    
    if rank <= 10:
        patterns.append(f"Exceptional fit. {yoe}y experience as {title} at {company}. Highly proficient in {skills_str}. {location} based.")
        patterns.append(f"Top tier candidate with {yoe} years experience. Strong background in {skills_str}. High engagement (RR: {rr:.0f}%).")
        
    reasoning = random.choice(patterns)
    return reasoning
