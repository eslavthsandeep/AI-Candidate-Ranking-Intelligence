import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    DEGREE_WEIGHTS,
    RELEVANT_FIELDS,
    TIER_SCORES,
    RELEVANT_CERTIFICATIONS,
)

logger = logging.getLogger(__name__)


def score_education(candidate):
    """
    Score education and certifications using config tables.
    Returns normalized score 0-100.
    """
    if not isinstance(candidate, dict):
        return 0
    education = candidate.get('education') or []
    if not isinstance(education, list):
        education = []
    certifications = candidate.get('certifications') or []
    if not isinstance(certifications, list):
        certifications = []
    
    score = 0
    best_edu_score = 0
    
    for edu in education:
        if not isinstance(edu, dict):
            continue
        edu_score = 0
        field = (edu.get('field_of_study') or '').lower()
        is_relevant = any(f in field for f in RELEVANT_FIELDS)
        
        degree = (edu.get('degree') or '').lower()
        
        # Use config DEGREE_WEIGHTS for degree scoring
        degree_score = 0
        for deg_key, deg_val in DEGREE_WEIGHTS.items():
            if deg_key in degree:
                degree_score = max(degree_score, deg_val)
                
        if is_relevant:
            degree_score = int(degree_score * 1.2)
            
        # Use config TIER_SCORES for institution tier
        tier = (edu.get('tier') or 'unknown').lower()
        tier_score = TIER_SCORES.get(tier, TIER_SCORES.get('unknown', 5))
            
        edu_score = degree_score + tier_score
        best_edu_score = max(best_edu_score, edu_score)
    
    score += best_edu_score
        
    # Certifications — use config RELEVANT_CERTIFICATIONS
    cert_score = 0
    for cert in certifications:
        if not isinstance(cert, dict):
            continue
        name = (cert.get('name') or '').lower()
        matched = False
        for cert_key, cert_val in RELEVANT_CERTIFICATIONS.items():
            if cert_key in name:
                cert_score += cert_val
                matched = True
                break
        if not matched:
            cert_score += 2  # generic certification
    
    # Cap cert contribution to avoid inflation
    cert_score = min(cert_score, 30)
    score += cert_score
        
    return min(100, score)
