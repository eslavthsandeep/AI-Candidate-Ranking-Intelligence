import logging

logger = logging.getLogger(__name__)

def score_education(candidate):
    """
    Score education and certifications.
    Returns normalized score 0-100.
    """
    education = candidate.get('education', [])
    certifications = candidate.get('certifications', [])
    
    score = 0
    
    relevant_fields = ['computer science', 'machine learning', 'artificial intelligence', 'data science', 
                       'statistics', 'mathematics', 'information technology', 'electronics', 'ece']
                       
    for edu in education:
        field = edu.get('field_of_study', '').lower()
        is_relevant = any(f in field for f in relevant_fields)
        
        degree = edu.get('degree', '').lower()
        degree_score = 0
        if 'phd' in degree or 'doctor' in degree:
            degree_score = 25
        elif 'm.tech' in degree or 'ms' in degree or 'master' in degree:
            degree_score = 20
        elif 'b.tech' in degree or 'be' in degree or 'bs' in degree or 'bachelor' in degree:
            degree_score = 15
        elif 'mba' in degree:
            degree_score = 5
            
        if is_relevant:
            degree_score *= 1.2
            
        tier = edu.get('tier', 'unknown').lower()
        tier_score = 5
        if 'tier_1' in tier:
            tier_score = 20
        elif 'tier_2' in tier:
            tier_score = 15
        elif 'tier_3' in tier:
            tier_score = 8
        elif 'tier_4' in tier:
            tier_score = 3
            
        score += degree_score + tier_score
        
    # Certifications
    ai_certs = ['aws ml', 'gcp ml', 'tensorflow', 'deep learning', 'machine learning', 'nlp']
    for cert in certifications:
        name = cert.get('name', '').lower()
        if any(c in name for c in ai_certs):
            score += 10
        else:
            score += 2
            
    return min(100, score)
