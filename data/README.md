# Dataset Setup

Place the challenge files here:

```
data/
  candidates.jsonl      ← full 100K dataset (download from challenge portal)
  sample_candidates.json  ← optional copy of sample set
```

If `data/candidates.jsonl` is missing, the pipeline falls back to:

```
[PUB] India_runs_data_and_ai_challenge/.../India_runs_data_and_ai_challenge/
```

## Generate submission

```bash
python rank.py --candidates ./data/candidates.jsonl --out ./submission.csv
python "[PUB] India_runs_data_and_ai_challenge/.../validate_submission.py" submission.csv
```

Rename `submission.csv` to your registered participant ID (e.g. `team_abc123.csv`) before upload.
