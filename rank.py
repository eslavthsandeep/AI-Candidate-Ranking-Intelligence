import json
import logging
import argparse
from typing import Iterator, Dict, List, Any
import time

from scoring.skill_matcher import score_skills
from scoring.career_scorer import score_career
from scoring.behavioral_scorer import score_behavioral
from scoring.honeypot_detector import detect_honeypot
from scoring.education_scorer import score_education
from scoring.composite import calculate_composite_score
from scoring.reasoning import generate_reasoning

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RankingPipeline:
    def __init__(self):
        pass

    def load_candidates(self, path: str) -> Iterator[Dict[str, Any]]:
        """Load candidates from JSONL or JSON file efficiently."""
        if path.endswith('.jsonl'):
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        yield json.loads(line)
        elif path.endswith('.json'):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    yield item
        else:
            raise ValueError("Unsupported file format. Must be .json or .jsonl")

    def prefilter(self, candidate: Dict[str, Any]) -> bool:
        """
        Fast first pass to eliminate obvious non-fits.
        Keep if ANY relevant signals, exclude if ALL irrelevant.
        """
        profile = candidate.get('profile', {})
        title = profile.get('current_title', '').lower()
        skills = [s.get('name', '').lower() for s in candidate.get('skills', [])]
        summary = profile.get('summary', '').lower()
        
        tech_keywords = ['ml', 'ai', 'data', 'engineer', 'developer', 'tech', 'software', 'backend', 'scientist', 'nlp', 'research']
        has_tech_title = any(kw in title for kw in tech_keywords)
        
        ai_skills = ['machine learning', 'deep learning', 'nlp', 'python', 'pytorch', 'tensorflow', 'embeddings', 'retrieval', 'llm', 'search']
        has_ai_skills = any(any(akw in s for akw in ai_skills) for s in skills)
        
        if has_tech_title or has_ai_skills or 'ai' in summary or 'ml' in summary:
            return True
            
        return False

    def process_candidates(self, input_path: str, progress_callback=None) -> List[Dict[str, Any]]:
        scored_candidates = []
        total_processed = 0
        filtered_in = 0
        
        for candidate in self.load_candidates(input_path):
            total_processed += 1
            if total_processed % 1000 == 0:
                logger.info(f"Processed {total_processed} candidates, kept {filtered_in}")
                if progress_callback:
                    progress_callback("scoring", total_processed, filtered_in)

            if not self.prefilter(candidate):
                continue
                
            filtered_in += 1
            
            # Score components
            skill_res = score_skills(candidate)
            skill_score = skill_res['score']
            
            career_res = score_career(candidate)
            career_score = career_res['score']
            trajectory_score = career_res['trajectory_score']
            
            behav_res = score_behavioral(candidate)
            behav_score = behav_res['score']
            behav_mult = behav_res['multiplier']
            
            edu_score = score_education(candidate)
            hp_score, is_hp = detect_honeypot(candidate)
            
            comp_score = calculate_composite_score(
                candidate, skill_score, career_score, behav_score, behav_mult, hp_score, is_hp, edu_score
            )
            
            scored_candidates.append({
                'candidate': candidate,
                'candidate_id': candidate['candidate_id'],
                'skill_score': skill_score,
                'career_score': career_score,
                'trajectory_score': trajectory_score,
                'behavioral_score': behav_score,
                'education_score': edu_score,
                'honeypot_flag': is_hp,
                'composite_score': comp_score
            })
            
        logger.info(f"Finished processing {total_processed} candidates. Shortlisted {filtered_in}.")
        return scored_candidates

    def final_rank(self, scored_candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Sort by composite score descending
        scored_candidates.sort(key=lambda x: x['composite_score'], reverse=True)
        
        top_100 = scored_candidates[:100]
        results = []
        
        for i, item in enumerate(top_100):
            rank = i + 1
            reasoning = generate_reasoning(
                item['candidate'], 
                item['skill_score'], 
                item['career_score'], 
                item['behavioral_score'], 
                item['education_score'],
                item['honeypot_flag'],
                rank,
                item['composite_score']
            )
            
            results.append({
                'candidate_id': item['candidate_id'],
                'rank': rank,
                'score': round(item['composite_score'], 4),
                'reasoning': reasoning,
                'candidate': item['candidate'],
                'breakdown': {
                    'skill_match': item['skill_score'],
                    'career': item['career_score'],
                    'trajectory': item['trajectory_score'],
                    'behavioral': item['behavioral_score'],
                    'education': item['education_score']
                },
                'honeypot_flag': item['honeypot_flag']
            })
            
        return results

    def run(self, input_path: str, output_path: str, progress_callback=None):
        logger.info(f"Starting ranking pipeline for {input_path}")
        start_time = time.time()
        
        scored = self.process_candidates(input_path, progress_callback)
        top_100 = self.final_rank(scored)
        
        # Write CSV
        import csv
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['candidate_id', 'rank', 'score', 'reasoning'])
            for item in top_100:
                writer.writerow([item['candidate_id'], item['rank'], f"{item['score']:.4f}", item['reasoning']])
                
        elapsed = time.time() - start_time
        logger.info(f"Pipeline completed in {elapsed:.2f} seconds. Output saved to {output_path}")
        return top_100

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Redrob Candidate Ranking')
    parser.add_argument('--candidates', required=True, help='Path to candidates.jsonl or .json')
    parser.add_argument('--out', required=True, help='Path to output CSV')
    args = parser.parse_args()
    
    pipeline = RankingPipeline()
    pipeline.run(args.candidates, args.out)
