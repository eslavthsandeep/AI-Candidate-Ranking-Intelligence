# 🏆 Redrob AI Candidate Ranking System — Technical Approach

## 1. Executive Summary
The Redrob Candidate Ranking System is designed to solve the problem of candidate sourcing at scale (100K+ profiles) under strict compute constraints (<5 min on a standard CPU with <16GB RAM). 

Instead of simple keyword filtering or computationally expensive on-the-fly deep learning LLM calls, we implement a **Hybrid Recruiter Model**. This approach combines:
1. **Explicit Recruiter Domain Heuristics**: Multi-signal scoring across title tiers, career trajectory, tenure stability, preferred locations, and education/certifications.
2. **Lightweight Cosine Similarity**: Local TF-IDF semantic relevance matching candidate summaries against the core job description.
3. **Rigorous Trap and Disqualifier Filtering**: Proactive honeypot screening and strict disqualification rules.

---

## 2. Multi-Stage Pipeline Architecture

Our pipeline processes candidates in a staged, funnel-based architecture:

```
[100,000+ Candidates JSONL]
           │
           ▼
┌───────────────────────────────┐
│ Stage 1: Prefilter (~2s)      │  <── Excludes obvious non-fits using config taxonomy
└──────────┬────────────────────┘
           │ (~60% filtered out)
           ▼
┌───────────────────────────────┐
│ Stage 2: Honeypot & Scorer    │  <── Flag impossible profiles (score forced to 0.0)
└──────────┬────────────────────┘
           │
           ▼
┌───────────────────────────────┐
│ Stage 3: Multi-Signal Scoring │  <── Skills (30%), Career (35%), Behavioral (12%), 
│                               │      Education (8%), TF-IDF Semantic Similarity (15%)
└──────────┬────────────────────┘
           │
           ▼
┌───────────────────────────────┐
│ Stage 4: JD Disqualifiers     │  <── Apply penalties for LangChain-only, no recent prod code, etc.
└──────────┬────────────────────┘
           │
           ▼
┌───────────────────────────────┐
│ Stage 5: Sorting & Tie-Break   │  <── Rounded score descending, candidate_id ascending
└──────────┬────────────────────┘
           │
           ▼
    [Top 100 Shortlist]
```

---

## 3. Hybrid Scoring Formula & Weights

The final composite score is calculated using the following dimensions (configured in `config.py`):
- **Career Score (35%)**: Checks title tiers, career progression, product vs service background, and years of experience.
- **Skill Match Score (30%)**: Compares candidate's skill taxonomy against must-have and nice-to-have skill clusters.
- **Behavioral Signal Score (12%)**: Integrates Redrob platform metrics (recruiter response rate, activity recency, profile completeness, GitHub contributions).
- **Education & Certifications (8%)**: Scores degrees, institution tiers, and relevant credentials (AWS ML, Google Cloud ML, databricks).
- **TF-IDF Semantic Similarity (15%)**: Cosine similarity between job description text and candidate profiles.

---

## 4. Honeypot Strategy

To catch fraudulent or inflated profiles (which are typical in high-volume settings), we enforce **8 strict checks**:
1. **Experience duration inflation**: Discrepancy between declared years of experience and career history sum.
2. **Expert keyword stuffing**: Claiming expert level for 8+ skills with 0 months of duration.
3. **Low assessment scores**: Claiming expert proficiency but scoring <30 in corresponding Redrob skill tests.
4. **Keyword stuffer (Non-tech title + expert AI/ML clusters)**: Profiles with generic non-tech titles (HR, Admin) claiming expert proficiency in 4 must-have AI clusters.
5. **Zero endorsements & duration**: Claiming expert/advanced level on 5+ skills that have 0 endorsements and 0 duration.
6. **Zero duration + low assessment**: Expert skills with 0 duration and test scores <40.
7. **Summary vs skills mismatch**: Non-tech keyword stuffing in profile summaries matching advanced tech skills.

Flagged profiles have their final score forced to `0.0`, ensuring they never make the top 100 shortlist.

---

## 5. Recruiter-Trust Reasoning Engine
Reasoning strings are structured to resemble human recruiter notes rather than vague descriptions. They present evidence-linked summaries:
- **Strengths**: Skill clusters covered.
- **Evidence**: Key companies and titles.
- **Risks/Concerns**: Identified disqualifiers or notices.
- **Verdict**: Strong Yes, Yes, Maybe, or No based on composite thresholds.
