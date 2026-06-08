"""
Integration tests for the predict agent.
"""
import pytest
from src.agents.predict_agent.agent import extract_features, predict, PredictFeatures

def test_predict_with_large_diff():
    diff = '\n'.join(['+line' + str(i) for i in range(200)])
    features = extract_features(diff)
    assert features.diff_size >= 100

def test_predict_score_increases_with_risk():
    low = PredictFeatures(diff_size=5, files_changed=1)
    high = PredictFeatures(diff_size=600, files_changed=20, test_history=0.5)
    from src.agents.predict_agent.agent import _score_heuristic
    assert _score_heuristic(high) > _score_heuristic(low)

def test_predict_returns_label():
    f = PredictFeatures(diff_size=200, files_changed=8)
    result = predict(f)
    assert result.label in ('low', 'medium', 'high', 'critical')
    assert 0 <= result.score <= 100
