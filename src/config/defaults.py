"""Hardcoded fallback defaults for DevPilot configuration.

Resolution order: .devpilot.yml (repo) → Azure App Configuration (global) → these defaults.
"""

DEFAULTS = {
    "predict": {
        "enabled": True,
        "failure_threshold": 70,
        "block_threshold": 90,
        "features": [
            "diff_size",
            "files_changed",
            "test_history",
            "author_history",
            "branch_age",
        ],
    },
    "diagnose": {
        "enabled": True,
        "model": "diagnose",
        "max_log_lines": 500,
        "post_pr_comment": True,
        "include_fix_suggestion": True,
    },
    "act": {
        "enabled": True,
        "auto_create_issue": True,
        "auto_adjust_gates": False,
        "suggest_deploy_strategy": True,
    },
    "quality_gates": {
        "block_merge_above_risk": 90,
        "require_human_approval_on_act": True,
    },
    "notify": {
        "pr_comment": True,
        "checks_api": True,
        "job_summary": True,
        "issue_on_failure": True,
    },
    "exclude": {
        "paths": ["docs/**", "**/*.md", ".github/**"],
        "branches": ["dependabot/**", "renovate/**"],
    },
}
