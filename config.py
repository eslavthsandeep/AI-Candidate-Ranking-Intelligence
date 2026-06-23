"""
config.py — Central configuration for the Redrob AI Candidate Ranking System.

Contains skill taxonomy, title tiers, scoring weights, keyword lists,
consulting-company lists, location preferences, and skill aliases.
All constants are defined here so individual scorers stay clean.
"""

import os

# ─────────────────────────────────────────────────────────────
# DATA PATHS
# ─────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Challenge dataset folder (nested publish bundle from organizers)
_CHALLENGE_ROOT = os.path.join(
    BASE_DIR,
    "[PUB] India_runs_data_and_ai_challenge",
    "[PUB] India_runs_data_and_ai_challenge",
    "India_runs_data_and_ai_challenge",
)
# Flat data/ alias — place candidates.jsonl here OR use challenge folder
_DATA_FLAT = os.path.join(BASE_DIR, "data")
DATA_DIR = _DATA_FLAT if os.path.isdir(_DATA_FLAT) else _CHALLENGE_ROOT

CANDIDATES_JSONL = os.path.join(DATA_DIR, "candidates.jsonl")
if not os.path.exists(CANDIDATES_JSONL):
    CANDIDATES_JSONL = os.path.join(_CHALLENGE_ROOT, "candidates.jsonl")

SAMPLE_CANDIDATES_JSON = os.path.join(DATA_DIR, "sample_candidates.json")
if not os.path.exists(SAMPLE_CANDIDATES_JSON):
    SAMPLE_CANDIDATES_JSON = os.path.join(_CHALLENGE_ROOT, "sample_candidates.json")

VALIDATE_SCRIPT = os.path.join(_CHALLENGE_ROOT, "validate_submission.py")
DEFAULT_OUTPUT_CSV = os.path.join(BASE_DIR, "submission.csv")

# ─────────────────────────────────────────────────────────────
# JOB DESCRIPTION (semantic + UI)
# ─────────────────────────────────────────────────────────────
JD_TEXT = """
Senior AI Engineer Founding Team at Redrob AI.
Production embeddings-based retrieval, sentence-transformers, OpenAI, BGE, E5.
Vector databases, hybrid search, Pinecone, Weaviate, Qdrant, Milvus, FAISS, Elasticsearch, OpenSearch, Solr.
Strong Python coding expertise, PyTorch, TensorFlow, keras, scikit-learn.
Evaluation frameworks for ranking, NDCG, MRR, MAP, A/B testing, recommendation systems.
LLM fine-tuning, LoRA, QLoRA, PEFT, RLHF, learning-to-rank, XGBoost, lightgbm, catboost.
Distributed systems, Large-scale inference, MLOps, kubernetes, docker, AWS, GCP, Azure.
"""

JD_PROFILE_TEXT = JD_TEXT

JD_TERM_WEIGHTS: dict[str, float] = {
    "embedding": 3.0,
    "embeddings": 3.0,
    "sentence-transformers": 3.0,
    "sentence transformers": 3.0,
    "retrieval": 3.0,
    "semantic search": 2.5,
    "vector": 2.0,
    "pinecone": 2.0,
    "weaviate": 2.0,
    "qdrant": 2.0,
    "milvus": 2.0,
    "faiss": 2.0,
    "elasticsearch": 2.0,
    "opensearch": 2.0,
    "python": 2.0,
    "pytorch": 2.0,
    "ranking": 2.5,
    "ndcg": 2.0,
    "mrr": 2.0,
    "a/b testing": 1.5,
    "recommendation": 1.5,
    "learning to rank": 2.0,
    "nlp": 2.0,
    "information retrieval": 2.5,
    "production": 2.0,
    "shipped": 2.0,
    "deployed": 1.5,
    "fine-tuning": 1.0,
    "lora": 1.0,
    "mlops": 1.0,
    "hr tech": 0.8,
    "talent intelligence": 0.8,
}

# ─────────────────────────────────────────────────────────────
# SKILL ALIASES  (lower-cased → canonical form)
# Lets us treat abbreviations, alternate names, and brand names
# as the same skill during matching.
# ─────────────────────────────────────────────────────────────
SKILL_ALIASES: dict[str, str] = {
    # Machine Learning / Deep Learning
    "ml": "machine learning",
    "deep learning": "deep learning",
    "dl": "deep learning",
    "neural networks": "deep learning",
    "neural nets": "deep learning",
    "ann": "deep learning",
    "cnn": "convolutional neural networks",
    "rnn": "recurrent neural networks",
    "lstm": "recurrent neural networks",
    "gru": "recurrent neural networks",
    "transformers": "transformers",
    "transformer": "transformers",
    "attention mechanism": "transformers",
    "bert": "transformers",
    "gpt": "large language models",
    "llm": "large language models",
    "llms": "large language models",
    "large language models": "large language models",
    "large language model": "large language models",
    "generative ai": "large language models",
    "gen ai": "large language models",
    "genai": "large language models",

    # NLP / IR
    "nlp": "natural language processing",
    "natural language processing": "natural language processing",
    "text mining": "natural language processing",
    "text analytics": "natural language processing",
    "information retrieval": "information retrieval",
    "ir": "information retrieval",
    "search": "search systems",
    "search systems": "search systems",
    "search system": "search systems",
    "search engine": "search systems",
    "search engineering": "search systems",
    "elasticsearch": "elasticsearch",
    "elastic search": "elasticsearch",
    "opensearch": "opensearch",
    "solr": "solr",
    "lucene": "solr",

    # Embeddings & Retrieval
    "sentence-transformers": "sentence transformers",
    "sentence transformers": "sentence transformers",
    "sentence transformer": "sentence transformers",
    "sbert": "sentence transformers",
    "openai embeddings": "embeddings",
    "embeddings": "embeddings",
    "embedding": "embeddings",
    "word embeddings": "embeddings",
    "word2vec": "embeddings",
    "glove": "embeddings",
    "fasttext": "embeddings",
    "bge": "embeddings",
    "e5": "embeddings",
    "text embeddings": "embeddings",
    "semantic search": "semantic search",
    "semantic similarity": "semantic search",
    "vector search": "semantic search",
    "dense retrieval": "semantic search",
    "retrieval": "retrieval systems",
    "retrieval systems": "retrieval systems",
    "retrieval system": "retrieval systems",
    "rag": "retrieval augmented generation",
    "retrieval augmented generation": "retrieval augmented generation",
    "retrieval-augmented generation": "retrieval augmented generation",

    # Vector databases
    "pinecone": "pinecone",
    "weaviate": "weaviate",
    "qdrant": "qdrant",
    "milvus": "milvus",
    "faiss": "faiss",
    "chromadb": "chromadb",
    "chroma": "chromadb",
    "vector database": "vector databases",
    "vector databases": "vector databases",
    "vector db": "vector databases",
    "vector store": "vector databases",
    "annoy": "vector databases",
    "scann": "vector databases",
    "hnsw": "vector databases",

    # Python ecosystem
    "python": "python",
    "python3": "python",
    "pytorch": "pytorch",
    "torch": "pytorch",
    "tensorflow": "tensorflow",
    "tf": "tensorflow",
    "keras": "keras",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "scipy": "scipy",
    "numpy": "numpy",
    "pandas": "pandas",
    "huggingface": "huggingface",
    "hugging face": "huggingface",
    "transformers library": "huggingface",

    # Ranking & Evaluation
    "ndcg": "ranking evaluation",
    "mrr": "ranking evaluation",
    "map": "ranking evaluation",
    "mean average precision": "ranking evaluation",
    "mean reciprocal rank": "ranking evaluation",
    "ranking evaluation": "ranking evaluation",
    "ranking evaluations": "ranking evaluation",
    "a/b testing": "a/b testing",
    "ab testing": "a/b testing",
    "ranking": "ranking systems",
    "ranking systems": "ranking systems",
    "ranking system": "ranking systems",
    "learning to rank": "learning to rank",
    "learning-to-rank": "learning to rank",
    "ltr": "learning to rank",
    "xgboost": "xgboost",
    "lightgbm": "lightgbm",
    "catboost": "catboost",
    "gradient boosting": "gradient boosting",

    # LLM Fine-tuning
    "lora": "lora",
    "qlora": "qlora",
    "peft": "peft",
    "fine-tuning": "fine-tuning",
    "fine tuning": "fine-tuning",
    "finetuning": "fine-tuning",
    "fine-tuning llms": "fine-tuning",
    "model fine-tuning": "fine-tuning",
    "rlhf": "rlhf",
    "instruction tuning": "fine-tuning",
    "adapter": "peft",
    "adapters": "peft",

    # Recommendation systems
    "recommendation systems": "recommendation systems",
    "recommendation system": "recommendation systems",
    "recommender systems": "recommendation systems",
    "recommender system": "recommendation systems",
    "recsys": "recommendation systems",
    "collaborative filtering": "recommendation systems",
    "content-based filtering": "recommendation systems",
    "matrix factorization": "recommendation systems",

    # HR-tech
    "hr tech": "hr tech",
    "hr-tech": "hr tech",
    "hrtech": "hr tech",
    "recruiting": "hr tech",
    "talent acquisition": "hr tech",
    "ats": "hr tech",
    "applicant tracking": "hr tech",
    "talent intelligence": "hr tech",
    "marketplace": "marketplace",

    # Distributed systems / Infra
    "distributed systems": "distributed systems",
    "microservices": "distributed systems",
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    "docker": "docker",
    "aws": "aws",
    "gcp": "gcp",
    "azure": "azure",
    "cloud": "cloud",
    "mlops": "mlops",
    "ml ops": "mlops",
    "kubeflow": "mlops",
    "mlflow": "mlflow",
    "airflow": "airflow",
    "kafka": "kafka",
    "spark": "spark",
    "pyspark": "spark",
    "ray": "ray",
    "dask": "dask",
    "celery": "celery",
    "redis": "redis",

    # Data engineering / DBs
    "sql": "sql",
    "postgresql": "sql",
    "mysql": "sql",
    "mongodb": "mongodb",
    "nosql": "nosql",
    "data engineering": "data engineering",
    "data pipeline": "data engineering",
    "data pipelines": "data engineering",
    "etl": "data engineering",
    "dbt": "data engineering",
    "snowflake": "snowflake",
    "bigquery": "bigquery",
    "databricks": "databricks",

    # Computer vision (less relevant but worth tracking)
    "computer vision": "computer vision",
    "cv": "computer vision",
    "image classification": "computer vision",
    "object detection": "computer vision",
    "image segmentation": "computer vision",
    "yolo": "computer vision",
    "opencv": "computer vision",

    # Speech (less relevant)
    "speech recognition": "speech",
    "asr": "speech",
    "tts": "speech",
    "text to speech": "speech",
    "speech synthesis": "speech",

    # MLOps / Serving
    "bentoml": "model serving",
    "triton": "model serving",
    "torchserve": "model serving",
    "onnx": "model serving",
    "tensorrt": "model serving",
    "model serving": "model serving",
    "model deployment": "model serving",
    "sagemaker": "sagemaker",
    "vertex ai": "vertex ai",

    # Misc ML
    "feature engineering": "feature engineering",
    "feature store": "feature engineering",
    "statistical modeling": "statistical modeling",
    "statistics": "statistical modeling",
    "bayesian": "statistical modeling",
    "time series": "time series",
    "forecasting": "time series",
    "anomaly detection": "anomaly detection",
    "gans": "generative models",
    "vae": "generative models",
    "diffusion models": "generative models",
    "stable diffusion": "generative models",

    # Agents / Chains (recent but useful for context)
    "langchain": "langchain",
    "llamaindex": "llamaindex",
    "llama index": "llamaindex",
    "autogen": "ai agents",
    "ai agents": "ai agents",
    "agents": "ai agents",

    # Weights & Biases / Experiment tracking
    "weights & biases": "experiment tracking",
    "wandb": "experiment tracking",
    "w&b": "experiment tracking",
    "neptune": "experiment tracking",
    "comet": "experiment tracking",
    "experiment tracking": "experiment tracking",
    "experiment-tracking": "experiment tracking",

    # Open source
    "open source": "open source",
    "open-source": "open source",
    "github": "github",
    "git": "git",

    # Web / API
    "flask": "flask",
    "fastapi": "fastapi",
    "django": "django",
    "rest api": "rest api",
    "graphql": "graphql",
    "grpc": "grpc",
}

# ─────────────────────────────────────────────────────────────
# SKILL CLUSTERS  (canonical skill → cluster name)
# Each cluster groups related canonical skills that satisfy
# a particular JD requirement.
# ─────────────────────────────────────────────────────────────

MUST_HAVE_CLUSTERS: dict[str, set[str]] = {
    "Embeddings & Retrieval": {
        "sentence transformers", "embeddings", "semantic search",
        "retrieval systems", "retrieval augmented generation",
        "dense retrieval", "information retrieval",
    },
    "Vector Databases & Hybrid Search": {
        "pinecone", "weaviate", "qdrant", "milvus", "faiss",
        "chromadb", "vector databases", "elasticsearch", "opensearch",
        "solr",
    },
    "Python": {
        "python", "pytorch", "tensorflow", "keras", "scikit-learn",
        "scipy", "numpy", "pandas", "huggingface",
    },
    "Ranking & Evaluation": {
        "ranking evaluation", "a/b testing", "ranking systems",
        "recommendation systems",
    },
}

NICE_TO_HAVE_CLUSTERS: dict[str, set[str]] = {
    "LLM Fine-tuning": {
        "fine-tuning", "lora", "qlora", "peft", "rlhf",
        "large language models",
    },
    "Learning-to-Rank": {
        "learning to rank", "xgboost", "lightgbm", "catboost",
        "gradient boosting",
    },
    "HR-tech & Marketplace": {
        "hr tech", "marketplace",
    },
    "Distributed Systems & Infra": {
        "distributed systems", "kubernetes", "docker", "aws", "gcp",
        "azure", "cloud", "mlops", "mlflow", "airflow", "kafka",
        "spark", "ray", "dask", "sagemaker", "vertex ai",
    },
    "Open Source & Community": {
        "open source", "github",
    },
    "NLP & Text": {
        "natural language processing", "transformers",
        "search systems",
    },
    "Model Serving & MLOps": {
        "model serving", "experiment tracking",
        "mlops", "mlflow",
    },
}

# Flattened lookup: canonical_skill → (cluster_name, is_must_have)
SKILL_TO_CLUSTER: dict[str, tuple[str, bool]] = {}
for _cluster, _skills in MUST_HAVE_CLUSTERS.items():
    for _s in _skills:
        SKILL_TO_CLUSTER[_s] = (_cluster, True)
for _cluster, _skills in NICE_TO_HAVE_CLUSTERS.items():
    for _s in _skills:
        if _s not in SKILL_TO_CLUSTER:  # must-have takes precedence
            SKILL_TO_CLUSTER[_s] = (_cluster, False)

# ─────────────────────────────────────────────────────────────
# TITLE TIERS  (lower-cased title substring → tier 1-5)
# Tier 1 = perfect match, Tier 5 = adjacent/tangential
# ─────────────────────────────────────────────────────────────
TITLE_TIERS: dict[str, int] = {
    # Tier 1 — direct AI/ML engineering titles
    "ai engineer": 1,
    "ml engineer": 1,
    "machine learning engineer": 1,
    "senior ai engineer": 1,
    "senior ml engineer": 1,
    "staff ml engineer": 1,
    "staff ai engineer": 1,
    "principal ml engineer": 1,
    "principal ai engineer": 1,
    "lead ml engineer": 1,
    "lead ai engineer": 1,
    "nlp engineer": 1,
    "search engineer": 1,
    "ranking engineer": 1,
    "retrieval engineer": 1,
    "recommendation engineer": 1,
    "recommendation systems engineer": 1,
    "applied scientist": 1,
    "applied ml scientist": 1,
    "ml scientist": 1,

    # Tier 2 — data science / research engineering
    "data scientist": 2,
    "senior data scientist": 2,
    "lead data scientist": 2,
    "principal data scientist": 2,
    "staff data scientist": 2,
    "research engineer": 2,
    "research scientist": 2,
    "ml researcher": 2,
    "ai researcher": 2,
    "deep learning engineer": 2,
    "computer vision engineer": 2,
    "cv engineer": 2,
    "data science lead": 2,
    "mlops engineer": 2,
    "ml platform engineer": 2,
    "ai developer": 2,
    "ml developer": 2,

    # Tier 3 — software / data engineering (can be adjacent)
    "software engineer": 3,
    "senior software engineer": 3,
    "staff software engineer": 3,
    "principal software engineer": 3,
    "lead software engineer": 3,
    "backend engineer": 3,
    "senior backend engineer": 3,
    "full stack engineer": 3,
    "fullstack engineer": 3,
    "platform engineer": 3,
    "data engineer": 3,
    "senior data engineer": 3,
    "lead data engineer": 3,
    "analytics engineer": 3,
    "data analyst": 3,
    "senior data analyst": 3,
    "software developer": 3,
    "senior software developer": 3,
    "tech lead": 3,
    "engineering manager": 3,
    "technical architect": 3,
    "solutions architect": 3,

    # Tier 4 — some technical relevance
    "product manager": 4,
    "technical product manager": 4,
    "devops engineer": 4,
    "site reliability engineer": 4,
    "sre": 4,
    "cloud engineer": 4,
    "database administrator": 4,
    "systems engineer": 4,
    "qa engineer": 4,
    "test engineer": 4,
    "frontend engineer": 4,
    "ui engineer": 4,
    "mobile developer": 4,
    "ios developer": 4,
    "android developer": 4,
    "it manager": 4,
    "technical writer": 4,
    "data architect": 4,
    "bi analyst": 4,
    "business intelligence": 4,

    # Tier 5 — non-technical
    "business analyst": 5,
    "project manager": 5,
    "operations manager": 5,
    "marketing manager": 5,
    "sales manager": 5,
    "hr manager": 5,
    "accountant": 5,
    "customer support": 5,
    "content writer": 5,
    "graphic designer": 5,
    "consultant": 5,
    "management consultant": 5,
    "civil engineer": 5,
    "mechanical engineer": 5,
    "electrical engineer": 5,
    "chemical engineer": 5,
}

# ─────────────────────────────────────────────────────────────
# NON-TECH TITLES (keyword stuffer trap detection)
# If someone has one of these titles AND 10+ expert AI skills,
# they're almost certainly a keyword stuffer.
# ─────────────────────────────────────────────────────────────
NON_TECH_TITLES: set[str] = {
    "marketing manager", "hr manager", "accountant", "sales manager",
    "operations manager", "customer support", "business analyst",
    "content writer", "graphic designer", "civil engineer",
    "mechanical engineer", "chemical engineer", "financial analyst",
    "supply chain manager", "procurement manager", "legal counsel",
    "office manager", "executive assistant", "recruiter",
    "talent acquisition", "public relations", "event manager",
    "teacher", "professor", "lecturer", "pharmacist",
    "architect", "interior designer", "real estate",
}

# ─────────────────────────────────────────────────────────────
# CONSULTING / SERVICE COMPANIES
# Entire career at these → penalty (per JD disqualifier)
# ─────────────────────────────────────────────────────────────
CONSULTING_COMPANIES: set[str] = {
    "tcs", "infosys", "wipro", "accenture", "cognizant", "capgemini",
    "hcl", "hcl technologies", "tech mahindra", "mindtree",
    "l&t infotech", "lti", "ltimindtree", "mphasis", "hexaware",
    "cyient", "persistent systems", "zensar", "niit technologies",
    "birlasoft", "sonata software", "coforge", "kpit",
    "deloitte", "ey", "ernst & young", "pwc", "kpmg",
    "mckinsey", "bain", "bcg", "boston consulting",
}

# ─────────────────────────────────────────────────────────────
# LOCATION PREFERENCES
# ─────────────────────────────────────────────────────────────
PREFERRED_CITIES: set[str] = {
    "pune", "noida", "hyderabad", "mumbai", "delhi",
    "gurgaon", "gurugram", "bangalore", "bengaluru",
    "chennai", "kolkata", "ahmedabad", "jaipur",
    "new delhi", "greater noida", "navi mumbai", "thane",
}
PREFERRED_COUNTRY = "india"

# ─────────────────────────────────────────────────────────────
# PRODUCTION KEYWORDS  (for career description analysis)
# ─────────────────────────────────────────────────────────────
PRODUCTION_KEYWORDS: set[str] = {
    "production", "deployed", "shipped", "launched", "live",
    "users", "scale", "pipeline", "serving", "latency",
    "throughput", "sla", "uptime", "monitoring", "alerting",
    "ci/cd", "cicd", "rollout", "a/b test", "ab test",
    "real-time", "realtime", "micro-service", "microservice",
    "api", "endpoint", "traffic", "qps", "rps",
    "kubernetes", "docker", "aws", "gcp", "azure",
    "million", "billion", "thousand", "k users",
    "99.9", "p99", "p95", "slo",
}

AI_ML_KEYWORDS: set[str] = {
    "machine learning", "deep learning", "neural network", "nlp",
    "natural language", "information retrieval", "search",
    "ranking", "recommendation", "embeddings", "embedding",
    "vector", "semantic", "retrieval", "transformer",
    "bert", "gpt", "llm", "fine-tun", "finetun",
    "classification", "regression", "clustering",
    "feature engineering", "model training", "inference",
    "pytorch", "tensorflow", "scikit", "sklearn",
    "huggingface", "hugging face", "sentence-transformer",
    "faiss", "pinecone", "weaviate", "qdrant", "milvus",
    "elasticsearch", "opensearch", "solr", "lucene",
    "rag", "recsys", "collaborative filter", "content-based",
    "lora", "qlora", "peft", "rlhf",
    "xgboost", "lightgbm", "gradient boost", "catboost",
    "anomaly detection", "time series", "forecasting",
    "data science", "data scientist", "ml engineer",
    "ai engineer", "research scientist",
    "ndcg", "mrr", "precision", "recall", "f1",
    "auc", "roc", "cross-validation",
    "pipeline", "mlops", "mlflow", "kubeflow",
    "sagemaker", "vertex ai",
    "attention", "self-attention", "multi-head",
    "tokenizer", "tokenization", "vocab",
    "sparse retrieval", "dense retrieval", "hybrid search",
    "re-ranking", "reranking", "cross-encoder", "bi-encoder",
    "knowledge graph", "entity extraction", "ner",
    "sentiment analysis", "text classification",
    "question answering", "qa system",
    "chatbot", "conversational ai", "dialogue",
}

# Keywords to search in summaries and headlines for pre-filter
PREFILTER_TITLE_KEYWORDS: set[str] = {
    "ai", "ml", "machine learning", "deep learning", "data",
    "scientist", "nlp", "research",
    "analytics", "search",
    "recommendation", "ranking", "retrieval", "embedding",
}

# ─────────────────────────────────────────────────────────────
# SCORING WEIGHTS
# ─────────────────────────────────────────────────────────────
COMPOSITE_WEIGHTS = {
    "skill_match":  0.30,
    "career":       0.35,
    "behavioral":   0.12,
    "education":    0.08,
    "semantic":     0.15,
}
# Behavioral multiplier is applied on top of the weighted sum.

# Title tier → skill score multiplier (penalize misaligned titles)
TITLE_SKILL_MULTIPLIER: dict[int, float] = {
    1: 1.0,
    2: 1.0,
    3: 0.85,
    4: 0.45,
    5: 0.25,
}

# ─────────────────────────────────────────────────────────────
# PROFICIENCY MULTIPLIERS
# ─────────────────────────────────────────────────────────────
PROFICIENCY_MULTIPLIER: dict[str, float] = {
    "expert":       1.0,
    "advanced":     0.85,
    "intermediate": 0.70,
    "beginner":     0.50,
}

# ─────────────────────────────────────────────────────────────
# EDUCATION CONFIGURATION
# ─────────────────────────────────────────────────────────────
RELEVANT_FIELDS: set[str] = {
    "computer science", "cs", "machine learning", "artificial intelligence",
    "ai", "data science", "statistics", "mathematics", "math",
    "information technology", "it", "electronics",
    "ece", "electrical and computer engineering",
    "electrical engineering", "electronics and communication",
    "electronics & communication", "information systems",
    "computational linguistics", "applied mathematics",
    "software engineering", "computing", "computer engineering", "physics",
}

DEGREE_WEIGHTS: dict[str, int] = {
    "ph.d": 25, "phd": 25, "ph.d.": 25, "doctorate": 25,
    "m.tech": 20, "m.tech.": 20, "ms": 20, "m.s": 20,
    "m.s.": 20, "m.sc": 20, "m.sc.": 20, "m.e.": 20, "m.e": 20,
    "mca": 15, "mba": 5,
    "b.tech": 15, "b.tech.": 15, "b.e.": 15, "b.e": 15,
    "b.sc": 12, "b.sc.": 12, "bs": 12, "b.s": 12, "b.s.": 12,
    "bca": 10,
    "diploma": 5,
}

TIER_SCORES: dict[str, int] = {
    "tier_1": 20,
    "tier_2": 15,
    "tier_3": 8,
    "tier_4": 3,
    "unknown": 5,
}

RELEVANT_CERTIFICATIONS: dict[str, int] = {
    "aws certified machine learning": 15,
    "aws machine learning specialty": 15,
    "aws ml specialty": 15,
    "google cloud professional machine learning": 15,
    "google cloud professional ml engineer": 15,
    "gcp ml engineer": 15,
    "gcp machine learning": 15,
    "tensorflow developer certificate": 12,
    "tensorflow developer": 12,
    "deep learning specialization": 12,
    "deep learning nanodegree": 10,
    "machine learning specialization": 10,
    "machine learning nanodegree": 10,
    "natural language processing specialization": 10,
    "nlp specialization": 10,
    "data science professional": 8,
    "azure ai engineer": 12,
    "azure data scientist": 10,
    "databricks certified": 8,
    "kubeflow certification": 8,
    "mlops certification": 8,
    "aws solutions architect": 5,
    "aws certified cloud practitioner": 3,
    "google cloud architect": 5,
    "kubernetes certification": 5,
    "cka": 5,
    "ckad": 5,
    "scrum master": 1,
    "pmp": 1,
}

from datetime import datetime
REFERENCE_DATE = datetime(2026, 6, 8)
