import json
import logging
import argparse
import re
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

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Fast compiled regexes for prefiltering short acronyms with word boundaries
RE_SHORT_TITLE = re.compile(r'\b(ai|ml|nlp)\b', re.IGNORECASE)
RE_SHORT_SUMMARY = re.compile(r'\b(ml|nlp)\b', re.IGNORECASE)


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
        """Fast first pass — keep if AI/ML relevance is found in title, headline, summary, or skills."""
        profile = candidate.get('profile', {})
        title = profile.get('current_title', '').lower()
        skills = [s.get('name', '').lower() for s in candidate.get('skills', [])]
        summary = profile.get('summary', '').lower()
        headline = profile.get('headline', '').lower()

        # Prefilter by title/headline: must be AI/ML related, or search/retrieval
        TIGHT_TITLE_LONG_KWS = {
            "machine learning", "deep learning", "search",
            "recommendation", "ranking", "retrieval", "embedding",
            "applied scientist", "speech", "computer vision", "vision"
        }

        has_ai_title = RE_SHORT_TITLE.search(title) is not None or any(kw in title for kw in TIGHT_TITLE_LONG_KWS)
        has_ai_headline = RE_SHORT_TITLE.search(headline) is not None or any(kw in headline for kw in TIGHT_TITLE_LONG_KWS)

        # AI-specific clusters and skills to check
        AI_CLUSTERS = {
            "Embeddings & Retrieval",
            "Vector Databases & Hybrid Search",
            "Ranking & Evaluation",
            "LLM Fine-tuning",
            "Learning-to-Rank",
            "NLP & Text"
        }
        AI_SKILLS = {
            "pytorch", "tensorflow", "huggingface", "keras", "scikit-learn", "deep learning", "machine learning", "neural networks"
        }

        has_ai_skills = False
        for s in skills:
            canon = SKILL_ALIASES.get(s, s)
            if canon in AI_SKILLS:
                has_ai_skills = True
                break
            if canon in SKILL_TO_CLUSTER:
                cluster, _ = SKILL_TO_CLUSTER[canon]
                if cluster in AI_CLUSTERS:
                    has_ai_skills = True
                    break

        # Summary check: must mention AI/ML core terms
        SUMMARY_LONG_KWS = {'machine learning', 'deep learning', 'retrieval', 'embedding', 'vector search', 'fine-tuning'}
        has_ai_summary = RE_SHORT_SUMMARY.search(summary) is not None or any(kw in summary for kw in SUMMARY_LONG_KWS)

        return has_ai_title or has_ai_headline or has_ai_skills or has_ai_summary


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
                'behavioral_multiplier': behav_mult,
                'soft_penalty': dq_res['soft_penalty'],
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

    def calibrate_scores(self, scored_candidates: List[Dict[str, Any]]):
        """Perform pool-wide percentile-rank scaling to calibrate scores before composite calculation."""
        if not scored_candidates:
            return
        score_keys = ['skill_score', 'career_score', 'behavioral_score', 'education_score', 'semantic_score']
        n = len(scored_candidates)
        
        for key in score_keys:
            # Sort indices based on score values ascending
            sorted_indices = sorted(range(n), key=lambda i: scored_candidates[i][key])
            
            # Compute fractional rank for duplicate handling
            i = 0
            while i < n:
                j = i
                while j < n and scored_candidates[sorted_indices[j]][key] == scored_candidates[sorted_indices[i]][key]:
                    j += 1
                # Fractional rank is the average of ranks in the duplicate group
                avg_rank = (i + j + 1) / 2.0
                percentile = (avg_rank / n) * 100.0
                for k in range(i, j):
                    scored_candidates[sorted_indices[k]][key + '_calibrated'] = percentile
                i = j
                
        # Re-calculate composite score using calibrated scores
        for item in scored_candidates:
            item['composite_score'] = calculate_composite_score(
                item['candidate'],
                item['skill_score_calibrated'],
                item['career_score_calibrated'],
                item['behavioral_score_calibrated'],
                item['behavioral_multiplier'],
                1.0 if item['honeypot_flag'] else 0.0,
                item['honeypot_flag'],
                item['education_score_calibrated'],
                semantic_score=item['semantic_score_calibrated'],
                hard_disqualified=item['hard_disqualified'],
                soft_penalty=item['soft_penalty'],
            )

    def final_rank(self, scored_candidates: List[Dict[str, Any]], top_n: int = 100, progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        import os
        from scoring.semantic_similarity import get_openai_embeddings, get_local_embeddings, assemble_candidate_text, JD_TEXT
        
        
        api_key = os.getenv("OPENAI_API_KEY")
        
        # Determine embedding function (OpenAI online vs local ONNX offline)
        embed_fn = None
        mode_label = ""
        if api_key:
            embed_fn = get_openai_embeddings
            mode_label = "OpenAI Embeddings (Online)"
        else:
            embed_fn = get_local_embeddings
            mode_label = "Local ONNX Embeddings (Offline)"
            
        if len(scored_candidates) > 0 and embed_fn is not None:
            logger.info(f"Performing Stage 2 high-fidelity semantic re-ranking with {mode_label}...")
            if progress_callback:
                progress_callback("reranking", len(scored_candidates), len(scored_candidates))
            # Sort by raw composite score to get top candidates to re-rank
            scored_candidates.sort(key=lambda x: x['composite_score'], reverse=True)

            re_rank_pool_size = min(300, len(scored_candidates))
            re_rank_pool = scored_candidates[:re_rank_pool_size]
            other_pool = scored_candidates[re_rank_pool_size:]
            
            # Extract candidate text narratives for embedding
            candidate_texts = [assemble_candidate_text(item['candidate']) for item in re_rank_pool]
            
            # Get JD embedding and candidate embeddings
            try:
                jd_emb_list = embed_fn([JD_TEXT])
                if jd_emb_list:
                    jd_emb = jd_emb_list[0]
                    cand_embs = embed_fn(candidate_texts)
                    if cand_embs:
                        import math
                        def cosine_sim(v1, v2):
                            dot = sum(a*b for a,b in zip(v1, v2))
                            n1 = math.sqrt(sum(a*a for a in v1))
                            n2 = math.sqrt(sum(b*b for b in v2))
                            return dot / (n1 * n2) if n1 > 0 and n2 > 0 else 0.0
                        
                        # Re-calculate similarity and update semantic_score
                        for item, cand_emb in zip(re_rank_pool, cand_embs):
                            sim = cosine_sim(jd_emb, cand_emb)
                            item['semantic_score'] = round(sim * 100.0, 2)
                            
                        # Merge pool back
                        scored_candidates = re_rank_pool + other_pool
            except Exception as e:
                logger.warning(f"Error during {mode_label} semantic re-ranking: {e}. Falling back to Stage 1 TF-IDF.")

        # Single pool-wide calibration of all heuristic + semantic scores
        if progress_callback:
            progress_callback("calibrating", len(scored_candidates), len(scored_candidates))
        self.calibrate_scores(scored_candidates)

        # Sort using full precision composite_score and alphabetical tie-breaker
        scored_candidates.sort(key=lambda x: (-x['composite_score'], x['candidate_id']))

        pool_size = min(top_n, len(scored_candidates))
        top_pool = scored_candidates[:pool_size]

        # Rescale composite_score for the top_pool to range from 0.20 to 0.99
        # to prevent score compression and align with sample submission range.
        if len(top_pool) > 1:
            max_score = max(item['composite_score'] for item in top_pool)
            min_score = min(item['composite_score'] for item in top_pool)
            score_range = max_score - min_score
            if score_range > 0:
                for item in top_pool:
                    scaled = 0.20 + 0.79 * ((item['composite_score'] - min_score) / score_range)
                    item['rounded_score'] = round(scaled, 4)
            else:
                for item in top_pool:
                    item['rounded_score'] = 0.9900
        elif len(top_pool) == 1:
            top_pool[0]['rounded_score'] = 0.9900

        # Sort again by rounded_score descending and candidate_id ascending to ensure tie-breaks are correct in the output CSV
        top_pool.sort(key=lambda x: (-x['rounded_score'], x['candidate_id']))

        results = []

        if api_key:
            logger.info("OPENAI_API_KEY found. Generating custom LLM-based recruiter reasonings concurrently...")
            from concurrent.futures import ThreadPoolExecutor
            
            def get_reasoning(args):
                rank, item = args
                return generate_reasoning(
                    item['candidate'],
                    item.get('skill_score_calibrated', item['skill_score']),
                    item.get('career_score_calibrated', item['career_score']),
                    item.get('behavioral_score_calibrated', item['behavioral_score']),
                    item.get('education_score_calibrated', item['education_score']),
                    item['honeypot_flag'],
                    rank,
                    item['rounded_score'], # use rescaled score for reasoning
                    semantic_score=item.get('semantic_score_calibrated', item['semantic_score']),
                    must_have_count=item['must_have_count'],
                    title_tier=item['title_tier'],
                    disqualifier_reasons=item['disqualifier_reasons'],
                    semantic_terms=item['semantic_terms'],
                    hard_disqualified=item['hard_disqualified'],
                )
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                reasoning_list = list(executor.map(get_reasoning, [(i + 1, item) for i, item in enumerate(top_pool)]))
            
            for i, item in enumerate(top_pool):
                rank = i + 1
                results.append({
                    'candidate_id': item['candidate_id'],
                    'rank': rank,
                    'score': item['rounded_score'],
                    'reasoning': reasoning_list[i],
                    'candidate': item['candidate'],
                    'breakdown': {
                        'skill_match': round(item.get('skill_score_calibrated', item['skill_score']), 2),
                        'career': round(item.get('career_score_calibrated', item['career_score']), 2),
                        'trajectory': item['trajectory_score'],
                        'behavioral': round(item.get('behavioral_score_calibrated', item['behavioral_score']), 2),
                        'education': round(item.get('education_score_calibrated', item['education_score']), 2),
                        'semantic': round(item.get('semantic_score_calibrated', item['semantic_score']), 2),
                    },
                    'honeypot_flag': item['honeypot_flag'],
                    'hard_disqualified': item['hard_disqualified'],
                })
        else:
            for i, item in enumerate(top_pool):
                rank = i + 1
                reasoning = generate_reasoning(
                    item['candidate'],
                    item.get('skill_score_calibrated', item['skill_score']),
                    item.get('career_score_calibrated', item['career_score']),
                    item.get('behavioral_score_calibrated', item['behavioral_score']),
                    item.get('education_score_calibrated', item['education_score']),
                    item['honeypot_flag'],
                    rank,
                    item['rounded_score'], # use rescaled score for reasoning
                    semantic_score=item.get('semantic_score_calibrated', item['semantic_score']),
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
                        'skill_match': round(item.get('skill_score_calibrated', item['skill_score']), 2),
                        'career': round(item.get('career_score_calibrated', item['career_score']), 2),
                        'trajectory': item['trajectory_score'],
                        'behavioral': round(item.get('behavioral_score_calibrated', item['behavioral_score']), 2),
                        'education': round(item.get('education_score_calibrated', item['education_score']), 2),
                        'semantic': round(item.get('semantic_score_calibrated', item['semantic_score']), 2),
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
        top_results = self.final_rank(scored, top_n=top_n, progress_callback=progress_callback)

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
