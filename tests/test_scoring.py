"""Unit tests for ranking pipeline components."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.honeypot_detector import detect_honeypot
from scoring.disqualifier import check_disqualifiers
from scoring.skill_matcher import score_skills
from scoring.composite import calculate_composite_score
from scoring.reasoning import generate_reasoning
from rank import RankingPipeline


SAMPLE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "[PUB] India_runs_data_and_ai_challenge",
    "[PUB] India_runs_data_and_ai_challenge",
    "India_runs_data_and_ai_challenge",
    "sample_candidates.json",
)


def _load_sample():
    with open(SAMPLE_PATH, encoding="utf-8") as f:
        return json.load(f)


class TestHoneypotDetector(unittest.TestCase):
    def test_yoe_mismatch_honeypot(self):
        cand = {
            "candidate_id": "CAND_0000001",
            "profile": {"current_title": "ML Engineer", "years_of_experience": 12},
            "career_history": [{"duration_months": 12}],
            "skills": [],
            "redrob_signals": {},
        }
        _, is_hp = detect_honeypot(cand)
        self.assertTrue(is_hp)

    def test_non_tech_keyword_stuffer(self):
        cand = {
            "candidate_id": "CAND_0000002",
            "profile": {"current_title": "HR Manager", "years_of_experience": 6},
            "career_history": [{"duration_months": 60, "company": "Acme"}],
            "skills": [
                {"name": "Python", "proficiency": "expert", "duration_months": 0, "endorsements": 0},
                {"name": "PyTorch", "proficiency": "expert", "duration_months": 0, "endorsements": 0},
                {"name": "Embeddings", "proficiency": "expert", "duration_months": 0, "endorsements": 0},
                {"name": "Pinecone", "proficiency": "expert", "duration_months": 0, "endorsements": 0},
                {"name": "FAISS", "proficiency": "expert", "duration_months": 0, "endorsements": 0},
            ],
            "redrob_signals": {"skill_assessment_scores": {}},
        }
        _, is_hp = detect_honeypot(cand)
        self.assertTrue(is_hp)


class TestDisqualifiers(unittest.TestCase):
    def test_consulting_only_hard_dq(self):
        cand = {
            "profile": {"current_title": "Software Engineer", "years_of_experience": 7},
            "career_history": [
                {"company": "TCS", "duration_months": 36, "description": "apps", "industry": "IT Services"},
                {"company": "Infosys", "duration_months": 48, "description": "apps", "industry": "IT Services"},
            ],
            "skills": [{"name": "Java", "proficiency": "advanced", "duration_months": 24}],
        }
        res = check_disqualifiers(cand, {"must_have_count": 0})
        self.assertTrue(res["hard_disqualified"])


class TestSkillMatcher(unittest.TestCase):
    def test_title_tier_penalizes_non_tech(self):
        cand = {
            "profile": {"current_title": "Civil Engineer"},
            "skills": [
                {"name": "Python", "proficiency": "expert", "duration_months": 36, "endorsements": 10},
                {"name": "Embeddings", "proficiency": "expert", "duration_months": 24, "endorsements": 5},
                {"name": "Pinecone", "proficiency": "advanced", "duration_months": 12, "endorsements": 3},
                {"name": "FAISS", "proficiency": "advanced", "duration_months": 12, "endorsements": 2},
            ],
            "redrob_signals": {"skill_assessment_scores": {}},
        }
        res = score_skills(cand)
        self.assertLessEqual(res["title_tier"], 5)
        self.assertLess(res["title_skill_multiplier"], 1.0)


class TestComposite(unittest.TestCase):
    def test_honeypot_zero_score(self):
        score = calculate_composite_score(
            {}, 90, 90, 80, 1.1, 1.0, True, 70, semantic_score=80,
        )
        self.assertEqual(score, 0.0)

    def test_hard_disqualified_zero_score(self):
        score = calculate_composite_score(
            {}, 90, 90, 80, 1.1, 0.0, False, 70, semantic_score=80,
            hard_disqualified=True,
        )
        self.assertEqual(score, 0.0)


class TestReasoning(unittest.TestCase):
    def test_no_exceptional_fit_for_weak_candidate(self):
        cand = {
            "candidate_id": "CAND_0000099",
            "profile": {
                "current_title": "Civil Engineer",
                "years_of_experience": 5,
                "current_company": "Wipro",
                "location": "Pune",
            },
            "skills": [{"name": "Sales", "proficiency": "beginner", "duration_months": 1}],
            "redrob_signals": {"recruiter_response_rate": 0.3},
        }
        text = generate_reasoning(cand, 10, 20, 30, 15, False, 50, 0.15, must_have_count=0, title_tier=5)
        self.assertNotIn("Exceptional fit", text)
        self.assertTrue(text.startswith("Strengths:"))


class TestPipelineIntegration(unittest.TestCase):
    @unittest.skipUnless(os.path.exists(SAMPLE_PATH), "sample_candidates.json missing")
    def test_top_candidate_is_ml_engineer(self):
        pipeline = RankingPipeline()
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            out = tmp.name
        try:
            results = pipeline.run(SAMPLE_PATH, out, top_n=10)
            self.assertGreater(len(results), 0)
            top = results[0]
            title = top["candidate"]["profile"]["current_title"].lower()
            self.assertTrue(
                any(kw in title for kw in ("ml", "ai", "recommendation", "search", "nlp", "applied")),
                f"Expected ML-related top candidate, got {title}",
            )
            self.assertNotIn("Exceptional fit", top["reasoning"])
        finally:
            os.unlink(out)


if __name__ == "__main__":
    unittest.main()
