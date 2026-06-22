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
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AI_ML_KEYWORDS, PRODUCTION_KEYWORDS, PREFILTER_TITLE_KEYWORDS, JD_TERM_WEIGHTS

logger = logging.getLogger(__name__)

# Global OpenAI client lazy initialization
_openai_client = None

def get_openai_client():
    global _openai_client
    if _openai_client is not None:
        return _openai_client
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            _openai_client = OpenAI(api_key=api_key)
            return _openai_client
        except Exception as e:
            logger.warning(f"Error creating OpenAI client: {e}")
    return None


def get_openai_embeddings(texts: list[str]) -> list[list[float]] | None:
    client = get_openai_client()
    if not client:
        return None
    try:
        response = client.embeddings.create(
            input=texts,
            model="text-embedding-3-small"
        )
        return [item.embedding for item in response.data]
    except Exception as e:
        logger.warning(f"Failed to fetch OpenAI embeddings: {e}")
        return None


import numpy as np

# Global ONNX Encoder lazy initializer
_onnx_encoder = None

class ONNXEncoder:
    def __init__(self):
        try:
            from huggingface_hub import hf_hub_download
            import onnxruntime as ort
            from tokenizers import Tokenizer
            
            # Download/locate models
            models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")
            os.makedirs(models_dir, exist_ok=True)
            
            tokenizer_file = os.path.join(models_dir, "tokenizer.json")
            model_file = os.path.join(models_dir, "onnx", "model.onnx")
            
            if os.path.exists(tokenizer_file) and os.path.exists(model_file):
                logger.info("Loading ONNX Encoder and Tokenizer from local files.")
            else:
                logger.info("Local ONNX files not found. Attempting download from Hugging Face Hub...")
                tokenizer_file = hf_hub_download(
                    repo_id="sentence-transformers/all-MiniLM-L6-v2",
                    filename="tokenizer.json",
                    local_dir=models_dir,
                    local_dir_use_symlinks=False
                )
                model_file = hf_hub_download(
                    repo_id="sentence-transformers/all-MiniLM-L6-v2",
                    filename="onnx/model.onnx",
                    local_dir=models_dir,
                    local_dir_use_symlinks=False
                )
            
            self.tokenizer = Tokenizer.from_file(tokenizer_file)
            
            # Disable multithreading to avoid CPU safety alerts in server/sandbox
            sess_options = ort.SessionOptions()
            sess_options.intra_op_num_threads = 1
            sess_options.inter_op_num_threads = 1
            self.session = ort.InferenceSession(model_file, sess_options)
        except Exception as e:
            logger.warning(f"Could not load offline ONNX Encoder: {e}")
            raise e

    def encode(self, texts: list[str]) -> list[list[float]] | None:
        try:
            embeddings = []
            for text in texts:
                self.tokenizer.enable_truncation(max_length=512)
                encoded = self.tokenizer.encode(text)
                
                input_ids = np.array([encoded.ids], dtype=np.int64)
                attention_mask = np.array([encoded.attention_mask], dtype=np.int64)
                token_type_ids = np.zeros_like(input_ids)
                
                inputs = {
                    "input_ids": input_ids,
                    "attention_mask": attention_mask,
                    "token_type_ids": token_type_ids
                }
                outputs = self.session.run(None, inputs)
                
                # token embeddings shape: [1, seq_len, 384]
                token_embeddings = outputs[0][0]
                mask = attention_mask[0]
                
                # Mean Pooling
                sum_embeddings = np.sum(token_embeddings * mask[:, None], axis=0)
                sum_mask = np.sum(mask)
                mean_embedding = sum_embeddings / max(sum_mask, 1e-9)
                
                # L2 Norm
                norm = np.linalg.norm(mean_embedding)
                if norm > 0:
                    mean_embedding = mean_embedding / norm
                embeddings.append(mean_embedding.tolist())
            return embeddings
        except Exception as e:
            logger.warning(f"ONNX encoding failed: {e}")
            return None

def get_onnx_encoder():
    global _onnx_encoder
    if _onnx_encoder is not None:
        return _onnx_encoder
    try:
        _onnx_encoder = ONNXEncoder()
        return _onnx_encoder
    except Exception:
        return None

def get_local_embeddings(texts: list[str]) -> list[list[float]] | None:
    encoder = get_onnx_encoder()
    if not encoder:
        return None
    return encoder.encode(texts)

# Core Job Description representation for ranking
from config import JD_TEXT


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
    """Return a static IDF weight for a word based on its rarity, boosted by JD_TERM_WEIGHTS."""
    base_idf = 1.0
    if word in _RARE_TERMS:
        base_idf = 3.0
    elif word in _MEDIUM_TERMS:
        base_idf = 1.5
    elif word in _GENERIC_TERMS:
        base_idf = 0.3

    # Apply boost if term is found in JD_TERM_WEIGHTS or is part of a multi-word phrase
    if word in JD_TERM_WEIGHTS:
        base_idf *= JD_TERM_WEIGHTS[word]
    else:
        for term, weight in JD_TERM_WEIGHTS.items():
            if word in term.split():
                base_idf *= (weight * 0.7)
                break
    return base_idf


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


def assemble_candidate_text(candidate: dict) -> str:
    if not isinstance(candidate, dict):
        return ""
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

    return " ".join([str(p) for p in candidate_text_parts if p])


def score_semantic_similarity(candidate: dict) -> float:
    """
    Compute semantic similarity between candidate profile and the JD.
    Returns a normalized similarity score from 0.0 to 100.0.

    Uses TF-IDF with static IDF heuristics to heavily weight rare,
    domain-specific terms (e.g. 'qlora', 'weaviate', 'ndcg') and
    down-weight generic terms (e.g. 'engineer', 'senior', 'development').
    """
    candidate_text = assemble_candidate_text(candidate)
    if not candidate_text:
        return 0.0

    # Calculate TF-IDF vector
    cand_vector = _get_tfidf_vector(candidate_text)

    # Calculate similarity
    sim = _cosine_similarity(JD_VECTOR, cand_vector)

    # Scale from 0-1 to 0-100
    return round(sim * 100.0, 2)
