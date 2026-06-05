# `.devpilot.yml` Schema Reference

This document describes every configuration option available in `.devpilot.yml`.

DevPilot resolves configuration in this priority order:

```
.devpilot.yml (repo)  →  Azure App Configuration (global)  →  Built-in defaults
       highest                    middle                        fallback
```

> **Validation**: DevPilot validates `.devpilot.yml` on every push and posts
> a friendly error comment if the file is invalid.

---

## Top-Level Structure

```yaml
devpilot:
  predict:       { ... }
  diagnose:      { ... }
  act:           { ... }
  quality_gates: { ... }
  notify:        { ... }
  environments:  { ... }
  exclude:       { ... }
```

---

## `predict`

The Predict Agent runs **before** the pipeline starts and scores failure probability.

| Key | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `true` | Enable/disable the Predict Agent |
| `failure_threshold` | int (0-100) | `70` | Show warning check above this score |
| `block_threshold` | int (0-100) | `90` | Block PR merge above this score |
| `features` | list[string] | (all) | Signals fed to the ML model |

### Available features
- `diff_size` — total LOC added/removed
- `files_changed` — number of distinct files
- `test_history` — recent test pass rate for affected files
- `author_history` — failure rate of the commit author
- `branch_age` — how stale the branch is vs. base

---

## `diagnose`

The Diagnose Agent runs **on pipeline failure** and explains the root cause.

| Key | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `true` | Enable/disable the Diagnose Agent |
| `model` | string | `gpt-4o-mini` | Azure AI Foundry model deployment name |
| `max_log_lines` | int | `500` | Max log lines fed to the LLM (cost control) |
| `post_pr_comment` | bool | `true` | Post diagnosis as PR comment |
| `include_fix_suggestion` | bool | `true` | LLM also suggests a code fix |

### Supported models
- `gpt-4o-mini` (cheap, fast — recommended; served via Azure AI Foundry)
- `gpt-4o` (higher quality, more expensive; served via Azure AI Foundry)

---

## `act`

The Act Agent takes **autonomous actions** based on prediction + diagnosis.

| Key | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `true` | Enable/disable the Act Agent |
| `auto_create_issue` | bool | `true` | Create a GitHub Issue on failure |
| `auto_adjust_gates` | bool | `false` | Dynamically tighten/loosen quality gates |
| `suggest_deploy_strategy` | bool | `true` | Recommend canary/blue-green/rolling |

⚠️ **Safety**: When `auto_adjust_gates` is `true`, gate changes still respect `quality_gates.require_human_approval_on_act`.

---

## `quality_gates`

Hard rules that affect merge eligibility.

| Key | Type | Default | Description |
|---|---|---|---|
| `block_merge_above_risk` | int (0-100) | `90` | Block merge if risk score exceeds this value |
| `require_human_approval_on_act` | bool | `true` | Act Agent decisions need human approval |

---

## `notify`

Controls **where** DevPilot surfaces its output inside GitHub.

| Key | Type | Default | Description |
|---|---|---|---|
| `pr_comment` | bool | `true` | Rich markdown comment on the PR |
| `checks_api` | bool | `true` | Status check + annotations in PR Checks tab |
| `job_summary` | bool | `true` | Write to GitHub Actions Job Summary |
| `issue_on_failure` | bool | `true` | Auto-create GitHub Issue when pipeline fails |

---

## `environments`

Per-environment overrides. Any key from `quality_gates`, `act`, or `notify` can be overridden.

```yaml
environments:
  production:
    quality_gates:
      block_merge_above_risk: 70
    act:
      require_human_approval_on_act: true
  staging:
    quality_gates:
      block_merge_above_risk: 85
```

DevPilot detects environment from the target branch:
- `main` / `master` / `prod*` → `production`
- `staging` / `stage` → `staging`
- everything else → `development`

---

## `exclude`

Paths/branches DevPilot should completely ignore.

| Key | Type | Description |
|---|---|---|
| `paths` | list[glob] | Files/folders to ignore (e.g. `docs/**`) |
| `branches` | list[glob] | Branches to skip (e.g. `dependabot/**`) |

---

## Validation

DevPilot validates `.devpilot.yml` on every push and posts a friendly error if it's invalid. See [schema.json](../src/config/schema.json) for the JSON Schema used.

---

## Examples

### Minimal config (use all defaults)
```yaml
devpilot:
  predict:
    enabled: true
```

### Aggressive autonomous mode
```yaml
devpilot:
  predict:
    enabled: true
    block_threshold: 80
  diagnose:
    enabled: true
    model: gpt-4o
  act:
    enabled: true
    auto_create_issue: true
    auto_adjust_gates: true
  quality_gates:
    require_human_approval_on_act: false
```

### Conservative / observability-only
```yaml
devpilot:
  predict:
    enabled: true
    failure_threshold: 50
    block_threshold: 100      # never block
  diagnose:
    enabled: true
  act:
    enabled: false            # no autonomous action
```
