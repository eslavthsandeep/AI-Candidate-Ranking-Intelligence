#!/bin/bash
# Redrob Hackathon — One-liner runner and validator script

echo "=== 1. Running Candidate Ranking Pipeline on 100K dataset ==="
python rank.py \
  --candidates "./[PUB] India_runs_data_and_ai_challenge/[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/candidates.jsonl" \
  --out team_antigravity.csv

echo ""
echo "=== 2. Running Official Submission Validator ==="
python "./[PUB] India_runs_data_and_ai_challenge/[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/validate_submission.py" team_antigravity.csv
