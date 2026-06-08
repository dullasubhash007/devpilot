"""
Feature service for the DevPilot prediction engine.
Handles feature extraction and normalisation.
"""
from dataclasses import dataclass
from typing import Optional

@dataclass
class FeatureVector:
    diff_size: int
    files_changed: int
    test_pass_rate: float
    author_fail_rate: float
    branch_age: int
    has_test_changes: bool = False
    is_config_only: bool = False

    def normalise(self) -> dict:
        return {
            'diff_size_norm': min(self.diff_size / 1000, 1.0),
            'files_changed_norm': min(self.files_changed / 50, 1.0),
            'test_pass_rate': self.test_pass_rate,
            'author_fail_rate': self.author_fail_rate,
            'branch_age_norm': min(self.branch_age / 30, 1.0),
        }

    def risk_indicators(self) -> list:
        risks = []
        if self.diff_size > 500: risks.append('large_diff')
        if self.files_changed > 10: risks.append('many_files')
        if self.test_pass_rate < 0.8: risks.append('low_test_pass')
        if self.author_fail_rate > 0.2: risks.append('high_author_failure')
        if self.branch_age > 7: risks.append('stale_branch')
        return risks
