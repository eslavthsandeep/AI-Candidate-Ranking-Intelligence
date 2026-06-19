import json
import logging
import argparse
from typing import Iterator, Dict, List, Any, Callable, Optional
import time

from scoring.skill_matcher import score_skills
from scoring.career_scorer import score_career
from scoring.behavioral_scorer import score_behavioral
from scoring.honeypot_detector import detect_honeypot
from scoring.education_scorer import score_education
from scoring.disqualifier import check_disqualifiers
from scoring.semantic_scorer import score_semantic
from scoring.composite import calculate_composite_score
from scoring.reasoning import generate_reasoning
from config import PREFILTER_TITLE_KEYWORDS, SKILL_ALIASES, SKILL_TO_CLUSTER

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RankingPipeline:
    def __init__(self):
        self.honeypots_detected = 0
        self.disqualified_count = 0
        self.soft_penalized_count = 0

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
        """Fast first pass — keep if ANY relevant signal exists."""
        profile = candidate.get('profile', {})
        title = profile.get('current_title', '').lower()
        skills = [s.get('name', '').lower() for s in candidate.get('skills', [])]
        summary = profile.get('summary', '').lower()
        headline = profile.get('headline', '').lower()

        has_tech_title = any(kw in title for kw in PREFILTER_TITLE_KEYWORDS)
        has_tech_headline = any(kw in headline for kw in PREFILTER_TITLE_KEYWORDS)
        has_relevant_skills = any(
            SKILL_ALIASES.get(s, s) in SKILL_TO_CLUSTER for s in skills
        )

        if has_tech_title or has_tech_headline or has_relevant_skills:
            return True

        if any(kw in summary for kw in ('ai', 'ml', 'machine learning', 'deep learning', 'nlp', 'data science', 'retrieval', 'embedding')):
            return True

        return False

    def process_candidates(
        self,
        input_path: str,
        progress_callback: Optional[Callable] = None,
    ) -> List[Dict[str, Any]]:
        scored_candidates = []
        total_processed = 0
        filtered_in = 0
        self.honeypots_detected = 0
        self.disqualified_count = 0
        self.soft_penalized_count = 0

        for candidate in self.load_candidates(input_path):
            total_processed += 1
            if total_processed % 500 == 0:
                logger.info(f"Processed {total_processed} candidates, kept {filtered_in}")
                if progress_callback:
                    progress_callback("scoring", total_processed, filtered_in)

            if not self.prefilter(candidate):
                continue

            filtered_in += 1

            skill_res = score_skills(candidate)
            skill_score = skill_res['score']

            career_res = score_career(candidate)
            career_score = career_res['score']
            trajectory_score = career_res['trajectory_score']

            behav_res = score_behavioral(candidate)
            behav_score = behav_res['score']
            behav_mult = behav_res['multiplier']

            edu_score = score_education(candidate)
            sem_res = score_semantic(candidate)
            sem_score = sem_res['score']

            dq_res = check_disqualifiers(candidate, skill_res)
            hp_score, is_hp = detect_honeypot(candidate)

            if is_hp:
                self.honeypots_detected += 1
            if dq_res['hard_disqualified']:
                self.disqualified_count += 1
            elif dq_res['soft_penalty'] < 1.0:
                self.soft_penalized_count += 1

            comp_score = calculate_composite_score(
                candidate,
                skill_score,
                career_score,
                behav_score,
                behav_mult,
                hp_score,
                is_hp,
                edu_score,
                semantic_score=sem_score,
                hard_disqualified=dq_res['hard_disqualified'],
                soft_penalty=dq_res['soft_penalty'],
            )

            scored_candidates.append({
                'candidate': candidate,
                'candidate_id': candidate['candidate_id'],
                'skill_score': skill_score,
                'career_score': career_score,
                'trajectory_score': trajectory_score,
                'behavioral_score': behav_score,
                'education_score': edu_score,
                'semantic_score': sem_score,
                'honeypot_flag': is_hp,
                'hard_disqualified': dq_res['hard_disqualified'],
                'disqualifier_reasons': dq_res['reasons'],
                'must_have_count': skill_res.get('must_have_count', 0),
                'title_tier': skill_res.get('title_tier', dq_res.get('title_tier', 5)),
                'semantic_terms': sem_res.get('matched_terms', []),
                'composite_score': comp_score,
            })

        logger.info(
            f"Finished processing {total_processed} candidates. "
            f"Shortlisted {filtered_in}. Honeypots: {self.honeypots_detected}. "
            f"Hard DQ: {self.disqualified_count}. Soft penalties: {self.soft_penalized_count}."
        )
        return scored_candidates

    def final_rank(self, scored_candidates: List[Dict[str, Any]], top_n: int = 100) -> List[Dict[str, Any]]:
        for item in scored_candidates:
            item['rounded_score'] = round(item['composite_score'], 4)

        scored_candidates.sort(key=lambda x: (-x['rounded_score'], x['candidate_id']))

        pool_size = min(top_n, len(scored_candidates))
        top_pool = scored_candidates[:pool_size]
        results = []

        for i, item in enumerate(top_pool):
            rank = i + 1
            reasoning = generate_reasoning(
                item['candidate'],
                item['skill_score'],
                item['career_score'],
                item['behavioral_score'],
                item['education_score'],
                item['honeypot_flag'],
                rank,
                item['composite_score'],
                semantic_score=item['semantic_score'],
                must_have_count=item['must_have_count'],
                title_tier=item['title_tier'],
                disqualifier_reasons=item['disqualifier_reasons'],
                semantic_terms=item['semantic_terms'],
                hard_disqualified=item['hard_disqualified'],
            )

            results.append({
                'candidate_id': item['candidate_id'],
                'rank': rank,
                'score': item['rounded_score'],
                'reasoning': reasoning,
                'candidate': item['candidate'],
                'breakdown': {
                    'skill_match': item['skill_score'],
                    'career': item['career_score'],
                    'trajectory': item['trajectory_score'],
                    'behavioral': item['behavioral_score'],
                    'education': item['education_score'],
                    'semantic': item['semantic_score'],
                },
                'honeypot_flag': item['honeypot_flag'],
                'hard_disqualified': item['hard_disqualified'],
            })

        return results

    def run(
        self,
        input_path: str,
        output_path: str,
        progress_callback: Optional[Callable] = None,
        top_n: int = 100,
    ):
        logger.info(f"Starting ranking pipeline for {input_path}")
        start_time = time.time()

        scored = self.process_candidates(input_path, progress_callback)
        top_results = self.final_rank(scored, top_n=top_n)

        import csv
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['candidate_id', 'rank', 'score', 'reasoning'])
            for item in top_results:
                writer.writerow([
                    item['candidate_id'],
                    item['rank'],
                    f"{item['score']:.4f}",
                    item['reasoning'],
                ])

        elapsed = time.time() - start_time
        logger.info(f"Pipeline completed in {elapsed:.2f}s. Output: {output_path}")
        return top_results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Redrob Candidate Ranking')
    parser.add_argument('--candidates', required=True, help='Path to candidates.jsonl or .json')
    parser.add_argument('--out', required=True, help='Path to output CSV')
    parser.add_argument('--top', type=int, default=100, help='Number of candidates to rank (default 100)')
    args = parser.parse_args()

    pipeline = RankingPipeline()
    pipeline.run(args.candidates, args.out, top_n=args.top)
