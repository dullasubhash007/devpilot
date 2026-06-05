"""Predict Agent — failure probability scoring via Azure ML endpoint.

Feature extraction from a pull request, then calls the Azure ML
serverless inference endpoint. Returns a risk score (0–100).
"""
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

import httpx

from src.shared.credential import get_credential
from src.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PredictFeatures:
    diff_size: int = 0          # total lines added + removed
    files_changed: int = 0      # number of distinct files
    test_history: float = 1.0   # recent test pass-rate (0.0–1.0)
    author_history: float = 1.0 # recent author failure-rate (0.0–1.0)
    branch_age: int = 0         # days since branch diverged from base


@dataclass
class PredictResult:
    score: int          # 0–100 risk score
    features: dict
    label: str          # "low" | "medium" | "high" | "critical"


def extract_features(
    diff: str,
    author_stats: dict | None = None,
    test_pass_rate: float = 1.0,
    branch_age_days: int = 0,
) -> PredictFeatures:
    """Derive model features from the raw PR diff and metadata."""
    additions = sum(1 for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++"))
    deletions = sum(1 for l in diff.splitlines() if l.startswith("-") and not l.startswith("---"))
    diff_size = additions + deletions

    changed_files = set()
    for line in diff.splitlines():
        if line.startswith("diff --git"):
            parts = line.split(" b/")
            if len(parts) == 2:
                changed_files.add(parts[1])

    author_fail_rate = 0.0
    if author_stats:
        total = author_stats.get("total_runs", 0)
        failures = author_stats.get("failed_runs", 0)
        author_fail_rate = (failures / total) if total > 0 else 0.0

    return PredictFeatures(
        diff_size=diff_size,
        files_changed=len(changed_files),
        test_history=test_pass_rate,
        author_history=author_fail_rate,
        branch_age=branch_age_days,
    )


def _score_heuristic(features: PredictFeatures) -> int:
    """Fallback heuristic scorer when the ML endpoint is unavailable."""
    score = 0.0
    # diff size: 0–40 pts
    if features.diff_size > 1000:
        score += 40
    elif features.diff_size > 300:
        score += 20
    elif features.diff_size > 50:
        score += 10
    # files changed: 0–20 pts
    if features.files_changed > 20:
        score += 20
    elif features.files_changed > 5:
        score += 10
    # test history: low pass rate → up to 20 pts
    score += max(0, (1.0 - features.test_history) * 20)
    # author failure history: up to 15 pts
    score += min(15, features.author_history * 15)
    # branch age: up to 5 pts
    if features.branch_age > 14:
        score += 5
    elif features.branch_age > 7:
        score += 2
    return min(100, int(score))


def predict(
    features: PredictFeatures,
    enabled_features: list[str] | None = None,
) -> PredictResult:
    """Call Azure ML endpoint or fall back to heuristic scorer."""
    enabled = set(enabled_features or ["diff_size", "files_changed", "test_history",
                                        "author_history", "branch_age"])
    feature_dict = {k: v for k, v in asdict(features).items() if k in enabled}

    score = _call_ml_endpoint(feature_dict)
    if score is None:
        logger.warning("ML endpoint unavailable, using heuristic scorer")
        score = _score_heuristic(features)

    if score >= 90:
        label = "critical"
    elif score >= 70:
        label = "high"
    elif score >= 40:
        label = "medium"
    else:
        label = "low"

    logger.info("Predict score=%d label=%s", score, label)
    return PredictResult(score=score, features=feature_dict, label=label)


def _call_ml_endpoint(features: dict) -> int | None:
    endpoint = os.getenv("AZURE_ML_ENDPOINT")
    if not endpoint:
        return None
    try:
        token = get_credential().get_token(
            "https://ml.azure.com/.default"
        ).token
        resp = httpx.post(
            endpoint,
            json={"data": [list(features.values())]},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        resp.raise_for_status()
        raw_score = resp.json().get("result", [None])[0]
        return int(round(float(raw_score) * 100)) if raw_score is not None else None
    except Exception as exc:
        logger.warning("ML endpoint call failed: %s", exc)
        return None


def format_check_summary(result: PredictResult, failure_threshold: int, block_threshold: int) -> str:
    emoji = {"low": "✅", "medium": "⚠️", "high": "❌", "critical": "🚨"}.get(result.label, "❓")
    lines = [
        f"## {emoji} DevPilot Prediction — Risk Score: {result.score}/100",
        "",
        f"| Signal | Value |",
        f"|--------|-------|",
    ]
    labels = {
        "diff_size": "Lines changed",
        "files_changed": "Files changed",
        "test_history": "Test pass rate",
        "author_history": "Author failure rate",
        "branch_age": "Branch age (days)",
    }
    for k, v in result.features.items():
        if isinstance(v, float):
            v = f"{v:.0%}"
        lines.append(f"| {labels.get(k, k)} | {v} |")
    lines += [
        "",
        f"**Thresholds**: warn ≥{failure_threshold} · block ≥{block_threshold}",
    ]
    return "\n".join(lines)
