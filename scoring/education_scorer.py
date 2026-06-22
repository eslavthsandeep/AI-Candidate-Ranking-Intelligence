import logging
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    DEGREE_WEIGHTS,
    RELEVANT_FIELDS,
    TIER_SCORES,
    RELEVANT_CERTIFICATIONS,
)

logger = logging.getLogger(__name__)


def _parse_grade(grade_str: str | None) -> float | None:
    """Parse grade string into a normalized 0-100 float representation."""
    if not grade_str:
        return None
    g_clean = grade_str.strip().lower()
    
    # Try parsing GPA out of 4
    gpa4_match = re.search(r'([0-9.]+)\s*(?:/4(?:\.0)?)', g_clean)
    if gpa4_match:
        try:
            val = float(gpa4_match.group(1))
            if val <= 4.0:
                return val * 25.0  # scale to 100
        except ValueError:
            pass

    # Try parsing CGPA out of 10
    cgpa_match = re.search(r'([0-9.]+)\s*(?:cgpa|gpa|/10)', g_clean)
    if cgpa_match:
        try:
            val = float(cgpa_match.group(1))
            # If GPA keyword is present and val <= 4.0, scale as GPA out of 4
            if "gpa" in g_clean and val <= 4.0:
                return val * 25.0
            if val <= 10.0:
                return val * 10.0  # scale to 100
        except ValueError:
            pass
            
    # Try parsing percentage out of 100
    pct_match = re.search(r'([0-9.]+)\s*%', g_clean)
    if pct_match:
        try:
            return float(pct_match.group(1))
        except ValueError:
            pass
            
    # Just try to find a float
    try:
        num_match = re.search(r'([0-9.]+)', g_clean)
        if num_match:
            val = float(num_match.group(1))
            if val <= 4.0:
                return val * 25.0
            elif val <= 10.0:
                return val * 10.0
            return val
    except ValueError:
        pass
        
    return None


def score_education(candidate):
    """
    Score education and certifications using config tables.
    Also parses grades to award up to +8 points GPA boost.
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
        
        # GPA / Grade boost (up to +8 points)
        grade_str = edu.get('grade')
        norm_grade = _parse_grade(grade_str)
        grade_boost = 0
        if norm_grade is not None:
            if norm_grade >= 80:
                grade_boost = 8
            elif norm_grade >= 70:
                grade_boost = 4
            elif norm_grade >= 60:
                grade_boost = 2
            
        edu_score = degree_score + tier_score + grade_boost
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
