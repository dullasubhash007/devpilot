"""Unit tests for Predict agent feature extraction (src/agents/predict_agent/agent.py)."""
import pytest
from src.agents.predict_agent.agent import (
    extract_features,
    predict,
    PredictFeatures,
    _score_heuristic,
    format_check_summary,
)


SMALL_DIFF = """\
diff --git a/src/foo.py b/src/foo.py
--- a/src/foo.py
+++ b/src/foo.py
@@ -1,3 +1,4 @@
+import os
 def foo():
-    pass
+    return os.environ.get('FOO', 'bar')
"""

def _make_large_diff() -> str:
    lines = []
    for i in range(15):
        lines.append(f"diff --git a/src/file{i}.py b/src/file{i}.py")
        lines.append(f"--- a/src/file{i}.py")
        lines.append(f"+++ b/src/file{i}.py")
        for j in range(100):
            lines.append(f"+line{j}")
    return "\n".join(lines)

LARGE_DIFF = _make_large_diff()


# ── extract_features ───────────────────────────────────────────────────────────

def test_extract_features_small_diff():
    f = extract_features(SMALL_DIFF)
    assert f.diff_size == 3      # 1 addition + 2 removals (excluding +++/--- lines)
    assert f.files_changed == 1
    assert f.test_history == 1.0
    assert f.branch_age == 0


def test_extract_features_large_diff():
    f = extract_features(LARGE_DIFF)
    assert f.files_changed == 15
    assert f.diff_size > 100


def test_extract_features_author_stats():
    stats = {"total_runs": 10, "failed_runs": 3}
    f = extract_features(SMALL_DIFF, author_stats=stats)
    assert abs(f.author_history - 0.3) < 0.01


def test_extract_features_zero_author_runs():
    stats = {"total_runs": 0, "failed_runs": 0}
    f = extract_features(SMALL_DIFF, author_stats=stats)
    assert f.author_history == 0.0


def test_extract_features_branch_age():
    f = extract_features(SMALL_DIFF, branch_age_days=20)
    assert f.branch_age == 20


# ── _score_heuristic ──────────────────────────────────────────────────────────

def test_heuristic_small_change_low_score():
    f = PredictFeatures(diff_size=10, files_changed=1)
    assert _score_heuristic(f) < 40


def test_heuristic_large_diff_high_score():
    f = PredictFeatures(diff_size=1500, files_changed=25, test_history=0.5, author_history=0.5, branch_age=20)
    assert _score_heuristic(f) >= 70


def test_heuristic_capped_at_100():
    f = PredictFeatures(diff_size=9999, files_changed=999, test_history=0.0, author_history=1.0, branch_age=30)
    assert _score_heuristic(f) == 100


# ── predict ───────────────────────────────────────────────────────────────────

def test_predict_label_low():
    features = PredictFeatures(diff_size=5, files_changed=1)
    result = predict(features)
    assert result.label == "low"
    assert 0 <= result.score <= 39


def test_predict_label_critical():
    features = PredictFeatures(diff_size=2000, files_changed=30, test_history=0.0, author_history=1.0, branch_age=30)
    result = predict(features)
    assert result.label == "critical"
    assert result.score == 100


def test_predict_respects_enabled_features():
    features = PredictFeatures(diff_size=2000, files_changed=30, branch_age=0)
    # enabled_features filters which features are sent to ML endpoint / stored in result
    result = predict(features, enabled_features=["branch_age"])
    # Only branch_age should appear in the features dict output
    assert list(result.features.keys()) == ["branch_age"]
    assert "diff_size" not in result.features


# ── format_check_summary ──────────────────────────────────────────────────────

def test_format_check_summary_contains_score():
    from src.agents.predict_agent.agent import PredictResult
    result = PredictResult(score=75, features={"diff_size": 300}, label="high")
    summary = format_check_summary(result, failure_threshold=70, block_threshold=90)
    assert "75" in summary
    assert "high" in summary.lower() or "❌" in summary
    assert "70" in summary
    assert "90" in summary
