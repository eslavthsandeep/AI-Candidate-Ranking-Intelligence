# Generate hackathon submission CSV from full dataset
param(
    [string]$Candidates = ".\data\candidates.jsonl",
    [string]$Output = ".\submission.csv",
    [string]$TeamId = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path $Candidates)) {
    $Fallback = ".\[PUB] India_runs_data_and_ai_challenge\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl"
    if (Test-Path $Fallback) { $Candidates = $Fallback }
    else { throw "candidates.jsonl not found. Place it in data/ folder." }
}

python rank.py --candidates $Candidates --out $Output
$ValScript = ".\[PUB] India_runs_data_and_ai_challenge\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\validate_submission.py"
python $ValScript $Output

if ($TeamId) {
    $TeamCsv = ".\$TeamId.csv"
    Copy-Item $Output $TeamCsv -Force
    python $ValScript $TeamCsv
    Write-Host "Team submission ready: $TeamCsv"
}

Write-Host "Done: $Output"
