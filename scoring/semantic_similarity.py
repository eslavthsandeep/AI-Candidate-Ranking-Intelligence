"""
semantic_similarity.py — Hybrid semantic similarity scorer with IDF weighting.
Calculates cosine similarity between Job Description requirements and the candidate profile
(summary, current title, and career history) using a domain-focused vocabulary with
inverse-document-frequency heuristics to prioritize rare, discriminative terms.
"""

import re
import math
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AI_ML_KEYWORDS, PRODUCTION_KEYWORDS, PREFILTER_TITLE_KEYWORDS

logger = logging.getLogger(__name__)

# Core Job Description representation for ranking
JD_TEXT = """
Senior AI Engineer Founding Team at Redrob AI.
Production embeddings-based retrieval, sentence-transformers, OpenAI, BGE, E5.
Vector databases, hybrid search, Pinecone, Weaviate, Qdrant, Milvus, FAISS, Elasticsearch, OpenSearch, Solr.
Strong Python coding expertise, PyTorch, TensorFlow, keras, scikit-learn.
Evaluation frameworks for ranking, NDCG, MRR, MAP, A/B testing, recommendation systems.
LLM fine-tuning, LoRA, QLoRA, PEFT, RLHF, learning-to-rank, XGBoost, lightgbm, catboost.
Distributed systems, Large-scale inference, MLOps, kubernetes, docker, AWS, GCP, Azure.
"""


def _tokenize(text: str) -> list[str]:
    """Tokenize and normalize text to lowercase words/phrases."""
    if not text:
        return []
    # Lowercase and replace non-alphanumeric with spaces
    text_clean = re.sub(r'[^a-zA-Z0-9\-\s]', ' ', text.lower())
    # Split by whitespace and filter empty
    tokens = [w for w in text_clean.split() if len(w) > 1]
    return tokens


# Build static domain-focused vocabulary from config keywords
VOCABULARY = set()
for kw in AI_ML_KEYWORDS:
    VOCABULARY.update(_tokenize(kw))
for kw in PRODUCTION_KEYWORDS:
    VOCABULARY.update(_tokenize(kw))
for kw in PREFILTER_TITLE_KEYWORDS:
    VOCABULARY.update(_tokenize(kw))

# Add specific JD keywords to vocab
VOCABULARY.update(_tokenize(JD_TEXT))
VOCAB_LIST = sorted(list(VOCABULARY))
VOCAB_INDEX = {word: idx for idx, word in enumerate(VOCAB_LIST)}

# ─────────────────────────────────────────────────────────────
# STATIC IDF HEURISTICS
# Rare, domain-specific terms get high IDF; generic terms get low IDF.
# This compensates for the absence of a real corpus-based IDF calculation.
# ─────────────────────────────────────────────────────────────

# Very common / generic terms (low IDF → down-weighted)
_GENERIC_TERMS = {
    "engineer", "senior", "software", "developer", "manager", "lead",
    "team", "data", "system", "systems", "experience", "project",
    "application", "development", "design", "testing", "building",
    "analysis", "support", "service", "platform", "solution",
    "technology", "based", "cloud", "working", "work", "tools",
    "large", "scale", "strong", "coding", "expertise",
}

# Moderately common tech terms (medium IDF)
_MEDIUM_TERMS = {
    "python", "pytorch", "tensorflow", "keras", "scikit-learn",
    "aws", "gcp", "azure", "docker", "kubernetes",
    "api", "ml", "ai", "deep", "learning", "machine",
    "inference", "training", "model", "neural", "network",
}

# Rare, highly discriminative terms (high IDF → up-weighted)
_RARE_TERMS = {
    "qlora", "lora", "peft", "rlhf", "ndcg", "mrr", "bge",
    "faiss", "pinecone", "weaviate", "qdrant", "milvus",
    "opensearch", "solr", "lucene", "pgvector",
    "sentence-transformers", "embeddings", "embedding",
    "xgboost", "lightgbm", "catboost",
    "learning-to-rank", "reranking", "re-ranking", "cross-encoder",
    "bi-encoder", "retrieval", "mlops", "mlflow", "kubeflow",
    "sagemaker", "elasticsearch",
}


def _get_idf(word: str) -> float:
    """Return a static IDF weight for a word based on its rarity."""
    if word in _RARE_TERMS:
        return 3.0
    if word in _MEDIUM_TERMS:
        return 1.5
    if word in _GENERIC_TERMS:
        return 0.3
    return 1.0  # default


def _get_tfidf_vector(text: str) -> list[float]:
    """Create a TF-IDF vector for a text block using our vocabulary and static IDF."""
    tokens = _tokenize(text)
    vector = [0.0] * len(VOCAB_LIST)

    # Calculate word frequency counts
    counts: dict[str, int] = {}
    for t in tokens:
        if t in VOCAB_INDEX:
            counts[t] = counts.get(t, 0) + 1

    # Apply sublinear TF scaling (1 + log(tf)) × IDF
    for word, count in counts.items():
        idx = VOCAB_INDEX[word]
        tf = 1.0 + math.log(count)
        idf = _get_idf(word)
        vector[idx] = tf * idf

    return vector


def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate the cosine similarity between two frequency vectors."""
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


# Precompute the JD vector once at module load
JD_VECTOR = _get_tfidf_vector(JD_TEXT)


def score_semantic_similarity(candidate: dict) -> float:
    """
    Compute semantic similarity between candidate profile and the JD.
    Returns a normalized similarity score from 0.0 to 100.0.

    Uses TF-IDF with static IDF heuristics to heavily weight rare,
    domain-specific terms (e.g. 'qlora', 'weaviate', 'ndcg') and
    down-weight generic terms (e.g. 'engineer', 'senior', 'development').
    """
    if not isinstance(candidate, dict):
        return 0.0
    profile = candidate.get('profile') or {}
    if not isinstance(profile, dict):
        profile = {}
    summary = profile.get('summary') or ''
    headline = profile.get('headline') or ''
    title = profile.get('current_title') or ''

    # Assemble candidate's profile narrative text
    candidate_text_parts = [summary, headline, title]

    # Append recent job titles and descriptions
    career_history = candidate.get('career_history') or []
    if not isinstance(career_history, list):
        career_history = []
    for role in career_history[:3]:  # focus on last 3 roles
        if isinstance(role, dict):
            candidate_text_parts.append(role.get('title') or '')
            candidate_text_parts.append(role.get('description') or '')

    # Also include skill names for vocabulary coverage
    skills = candidate.get('skills') or []
    if not isinstance(skills, list):
        skills = []
    for skill in skills:
        if isinstance(skill, dict):
            candidate_text_parts.append(skill.get('name') or '')

    candidate_text = " ".join([str(p) for p in candidate_text_parts if p])

    # Calculate TF-IDF vector
    cand_vector = _get_tfidf_vector(candidate_text)

    # Calculate similarity
    sim = _cosine_similarity(JD_VECTOR, cand_vector)

    # Scale from 0-1 to 0-100
    return round(sim * 100.0, 2)
