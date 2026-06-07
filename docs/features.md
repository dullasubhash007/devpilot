# DevPilot Features Guide

> **DevPilot** is an AI-powered GitHub App that predicts pipeline failures before they happen, diagnoses root causes when they do, and autonomously acts to keep your delivery pipeline flowing — all inside GitHub's native UI.

---

## Table of Contents

1. [Predict Agent — Failure Risk Scoring](#1-predict-agent--failure-risk-scoring)
2. [Diagnose Agent — AI Root Cause Analysis](#2-diagnose-agent--ai-root-cause-analysis)
3. [Act Agent — Autonomous Remediation](#3-act-agent--autonomous-remediation)
4. [Quality Gates — Merge Protection](#4-quality-gates--merge-protection)
5. [Notifications — GitHub-Native Surfaces](#5-notifications--github-native-surfaces)
6. [Per-Repo Configuration — `.devpilot.yml`](#6-per-repo-configuration--devpilotyml)
7. [Environment Overrides — Production vs Staging](#7-environment-overrides--production-vs-staging)
8. [Exclusions — Skipping Paths and Branches](#8-exclusions--skipping-paths-and-branches)

---

## 1. Predict Agent — Failure Risk Scoring

### Description

The Predict Agent runs **before the pipeline starts** and scores the probability that the current pull request will cause a CI/CD failure. It analyses signals from the code change itself and the repository's history to produce a risk score from **0 (safe) to 100 (critical)**.

The score appears as a **GitHub Check** on every pull request within seconds of the push — before any workflow even starts running.

### Problem It Solves

Developers discover pipeline failures only *after* waiting 10–30 minutes for CI to complete. By that time, context has switched, the feedback loop is long, and the cost of fixing is higher. Teams waste **45–90 minutes per day** on reactive firefighting.

There is no signal in existing tools that says *"this change looks risky — consider reviewing it before pushing"* at the moment the developer opens a PR.

### Solution

DevPilot extracts five signals from the pull request and feeds them into a scoring model:

| Signal | What It Measures |
|---|---|
| `diff_size` | Total lines added + removed |
| `files_changed` | Number of distinct files modified |
| `test_history` | Recent test pass rate for affected files |
| `author_history` | This author's pipeline failure rate |
| `branch_age` | How many days the branch has diverged from base |

The score maps to four labels:

| Score | Label | GitHub Check |
|---|---|---|
| 0–39 | low | ✅ success |
| 40–69 | medium | ✅ success |
| 70–89 | high | ⚠️ neutral |
| 90–100 | critical | ❌ failure (blocks merge if configured) |

### Step-by-Step: How to Use

**Step 1 — Install DevPilot on your repository**

Install the GitHub App from your organisation's GitHub App settings. Grant access to the target repository.

**Step 2 — Add `.devpilot.yml` to your repo root**

```yaml
devpilot:
  predict:
    enabled: true
    failure_threshold: 70    # show warning above this score
    block_threshold: 90      # block merge above this score
    features:
      - diff_size
      - files_changed
      - test_history
      - author_history
      - branch_age
```

**Step 3 — Open a pull request**

As soon as you push a branch and open a PR, DevPilot creates a check run named **"DevPilot · Predict"** within 5 seconds.

**Step 4 — Read the check result**

Click on the check to see the full risk breakdown:

```
## ⚠️ DevPilot Prediction — Risk Score: 78/100

| Signal          | Value   |
|-----------------|---------|
| Lines changed   | 342     |
| Files changed   | 8       |
| Test pass rate  | 72%     |
| Author fail rate| 15%     |
| Branch age (days)| 3      |

Thresholds: warn ≥70 · block ≥90
```

**Step 5 — Act on the signal**

- Score < 70 → proceed normally
- Score 70–89 → review the change carefully before merging
- Score ≥ 90 → merge is blocked; reduce diff size or fix failing tests first

### Example

A developer adds 1,200 lines across 22 files after a 10-day-old branch:

```yaml
diff_size: 1200
files_changed: 22
branch_age: 10
test_history: 0.60   # 60% pass rate — some tests were failing
```

**DevPilot Score: 92 / 100 — CRITICAL ❌**

The merge is blocked. The developer sees:
> *"This change has a high failure probability. Consider splitting into smaller PRs or fixing the 40% failing tests before merging."*

---

## 2. Diagnose Agent — AI Root Cause Analysis

### Description

The Diagnose Agent runs **automatically when a GitHub Actions workflow fails**. It fetches the failure logs and the PR diff, then calls Azure AI Foundry (GPT-4.1 mini) to produce a structured diagnosis with a root cause, a suggested fix, and the exact file and line number responsible.

The diagnosis is posted as a **comment on the pull request** within seconds of the workflow failure being reported.

### Problem It Solves

When a CI pipeline fails, developers open the GitHub Actions log, scroll through thousands of lines, and manually try to identify what went wrong. This takes 5–20 minutes per failure and requires deep context about the codebase. Junior developers or developers unfamiliar with a module may spend much longer.

Existing tools show you the logs. **DevPilot reads and explains them.**

### Solution

When a `workflow_run` event arrives with `conclusion: failure`, DevPilot:

1. Fetches the last N lines of the workflow logs (configurable, default 500)
2. Fetches the PR diff (what changed)
3. Sends both to Azure AI Foundry with a structured prompt
4. Receives a JSON response: `{root_cause, fix_suggestion, file, line, confidence}`
5. Posts a formatted comment on the PR

The AI model understands build errors, test failures, import errors, configuration issues, Docker problems, npm/pip errors, timeout errors, and more.

### Step-by-Step: How to Use

**Step 1 — Configure the Diagnose agent**

```yaml
devpilot:
  diagnose:
    enabled: true
    model: gpt-4.1-mini        # Azure AI Foundry deployment name
    max_log_lines: 500         # lines of logs fed to the model
    post_pr_comment: true      # post result as PR comment
    include_fix_suggestion: true
```

**Step 2 — Push code and let the pipeline run**

DevPilot watches `workflow_run` events. If any GitHub Actions workflow on your PR fails, it automatically triggers.

**Step 3 — Read the diagnosis comment**

Within seconds of the failure, the `azuredevpilot` bot posts a comment:

```
## 🔍 DevPilot Diagnosis 🟢

**Root Cause**
The pytest module is not installed in the environment, causing the test run
to fail with 'No module named pytest'.

**Suggested Fix**
Add a step in the GitHub Actions workflow to install pytest
(e.g., 'pip install pytest') before running the tests.

📄 **Location**: `.github/workflows/ci.yml`

Powered by Azure AI Foundry · View run
```

**Step 4 — Apply the fix**

Follow the suggestion and push again. DevPilot will diagnose the next failure too if it recurs.

**Step 5 — Reduce `max_log_lines` for cost control**

For large workflows generating megabytes of logs, reduce this to keep costs low:

```yaml
diagnose:
  max_log_lines: 200    # only last 200 lines
```

### Example

**Scenario**: A Python microservice fails in CI with:
```
ERROR: ModuleNotFoundError: No module named 'fastapi'
```

DevPilot diagnosis:
```json
{
  "root_cause": "fastapi is missing from requirements.txt causing import failure",
  "fix_suggestion": "Add 'fastapi>=0.111.0' to requirements.txt",
  "file": "requirements.txt",
  "line": null,
  "confidence": "high"
}
```

**Scenario**: A Docker build fails:
```
COPY src/ ./src/     # COPY failed: file not found in build context
```

DevPilot diagnosis:
```json
{
  "root_cause": "Dockerfile COPY references 'src/' but the build context does not include it — likely a .dockerignore rule or wrong build directory",
  "fix_suggestion": "Check .dockerignore and ensure 'src' is not excluded, or update the docker build command to use the correct context path",
  "file": "Dockerfile",
  "line": 12,
  "confidence": "high"
}
```

---

## 3. Act Agent — Autonomous Remediation

### Description

The Act Agent runs **after the Diagnose Agent completes**. It reads the risk score from the Predict Agent and the structured diagnosis from the Diagnose Agent, then calls Azure AI Foundry (GPT-4.1 mini) to decide what autonomous actions to take:

- **Create a GitHub Issue** with full diagnosis details (default: on)
- **Recommend a deployment strategy** — rolling, canary, or blue-green (default: on)
- **Adjust quality gates** dynamically based on risk trends (default: off, requires explicit opt-in)

The AI reasons about the risk score and diagnosis together to select the most appropriate deploy strategy.

### Problem It Solves

After a pipeline failure is diagnosed, someone still has to:
- Create a bug ticket manually
- Decide whether to deploy cautiously or roll back
- Adjust thresholds if the team is in a risky period

These are repetitive decisions that follow predictable patterns. DevPilot automates them.

### Solution

The Act Agent calls Azure AI Foundry with the full context and receives a decision:

```json
{
  "deploy_strategy": "rolling",
  "adjust_gate_to": null,
  "reasoning": "Risk score 50/100 falls into the medium risk category. Rolling deployment strategy allows gradual rollout and monitoring while addressing the pytest installation issue."
}
```

Based on the decision, Act will:

1. **Create a GitHub Issue** with the diagnosis, risk score, run URL, and file location
2. **Update the PR comment** with the recommended deploy strategy
3. **Log the action** to Cosmos DB for audit

### Step-by-Step: How to Use

**Step 1 — Enable autonomous Act (disable human approval gate)**

```yaml
devpilot:
  act:
    enabled: true
    auto_create_issue: true
    suggest_deploy_strategy: true
    auto_adjust_gates: false

  quality_gates:
    require_human_approval_on_act: false   # set false to enable autonomous actions
```

> ⚠️ **Safety note**: Keep `require_human_approval_on_act: true` until you trust DevPilot's decisions. When `true`, the Act agent still runs but skips all actions.

**Step 2 — Let a pipeline fail (Diagnose fires first, then Act)**

The Act agent is triggered automatically after Diagnose completes. No manual steps needed.

**Step 3 — Check the created GitHub Issue**

A new issue is automatically created with labels `bug` and `devpilot`:

```
Title: [DevPilot] Pipeline failure on PR #4 (risk 50/100)

PR: #4
Risk Score: 50/100 (medium)
Run: https://github.com/org/repo/actions/runs/12345

### Root Cause
The pytest module is not installed in the environment.

### Suggested Fix
Add 'pip install pytest' before running tests.

---
Created automatically by DevPilot Act Agent · Powered by Azure AI Foundry
```

**Step 4 — Check the PR comment update**

The PR comment is updated with the Act summary:

```
## 🤖 DevPilot Actions

- Created issue: https://github.com/org/repo/issues/7
- Recommended deploy strategy: rolling

_Risk score 50/100 falls into the medium risk category. Rolling deployment
strategy allows gradual rollout and monitoring._
```

**Step 5 — Filter DevPilot issues**

All auto-created issues have the `devpilot` label. Filter them:
```
https://github.com/org/repo/issues?labels=devpilot
```

**Step 6 — Enable auto_adjust_gates (advanced)**

Only enable after reviewing several cycles:

```yaml
devpilot:
  act:
    auto_adjust_gates: true
  quality_gates:
    block_merge_above_risk: 90
    require_human_approval_on_act: false
```

### Deploy Strategy Logic

The Act agent selects deploy strategy based on risk score:

| Score | Strategy | Reasoning |
|---|---|---|
| < 40 | `null` (standard deploy) | Low risk — no special strategy needed |
| 40–69 | `rolling` | Medium risk — gradual rollout, easy rollback |
| 70–89 | `canary` | High risk — expose small percentage of traffic first |
| ≥ 90 | `blue-green` | Critical risk — keep old version hot for instant switch |

### Verified Test Output

Real output from a live test run (PR #4, risk score 50):

```
Act decision: {
  "deploy_strategy": "rolling",
  "reasoning": "The risk score is 50/100, which falls into the medium risk
  category. A rolling deployment strategy allows gradual rollout and monitoring
  of the fix, minimizing potential impact while addressing the missing pytest
  installation."
}

✅ Created issue #7: [DevPilot] Pipeline failure on PR #4 (risk 50/100)
✅ Recommended deploy strategy: rolling
```

**GitHub Issues created automatically**: https://github.com/dullasubhash007/devpilot/issues?labels=devpilot

---

## 4. Quality Gates — Merge Protection

### Description

Quality Gates let you define hard rules that **block or warn on pull request merges** based on the Predict Agent's risk score.

### Problem It Solves

Teams often merge risky changes because there's no automated enforcement. "It looks fine" becomes the gate, which fails when context is missing.

### Solution

DevPilot creates GitHub Check Runs that integrate with branch protection rules. You can require the DevPilot check to pass before merging.

### Step-by-Step: How to Use

**Step 1 — Configure thresholds**

```yaml
devpilot:
  predict:
    failure_threshold: 70    # warn (yellow) above this
    block_threshold: 90      # block merge above this

  quality_gates:
    block_merge_above_risk: 90
    require_human_approval_on_act: true
```

**Step 2 — Enable branch protection in GitHub**

1. Go to **Repository Settings → Branches → Branch protection rules**
2. Add a rule for `master` / `main`
3. Check **"Require status checks to pass before merging"**
4. Add **"DevPilot · Predict"** as a required check

**Step 3 — DevPilot automatically enforces the gate**

| Score | Check Status | Merge Allowed? |
|---|---|---|
| < 70 | ✅ success | Yes |
| 70–89 | ⚠️ neutral | Yes (warning shown) |
| ≥ 90 | ❌ failure | **No — blocked** |

**Step 4 — Override for emergencies**

Temporarily set `block_threshold: 100` in `.devpilot.yml` to allow all merges during an incident, then revert after.

---

## 5. Notifications — GitHub-Native Surfaces

### Description

DevPilot surfaces all its output inside GitHub's native UI. No external dashboards, no new tools to learn.

### Available Surfaces

| Surface | What It Shows |
|---|---|
| **PR Check tab** | Predict score with full signal breakdown |
| **PR Comment** | Diagnose root cause + fix suggestion |
| **GitHub Issues** | Auto-created by Act agent per failure |
| **Job Summary** | Written to the GitHub Actions job summary |

### Step-by-Step: Configure Notifications

```yaml
devpilot:
  notify:
    pr_comment: true       # Diagnose comment on PR
    checks_api: true       # Predict check in PR Checks tab
    job_summary: true      # Write to Actions job summary
    issue_on_failure: true # Auto-create issue (Act agent)
```

**Disable individual surfaces:**

```yaml
devpilot:
  notify:
    pr_comment: false      # silent mode — no PR comments
    issue_on_failure: false
```

---

## 6. Per-Repo Configuration — `.devpilot.yml`

### Description

Every behaviour of DevPilot can be configured per repository by placing a `.devpilot.yml` file in the repo root.

### Configuration Resolution Order

```
.devpilot.yml (highest priority)
    ↓
Azure App Configuration (global defaults)
    ↓
Built-in defaults (fallback)
```

### Full Example

```yaml
devpilot:
  predict:
    enabled: true
    failure_threshold: 70
    block_threshold: 90
    features:
      - diff_size
      - files_changed
      - test_history
      - author_history
      - branch_age

  diagnose:
    enabled: true
    model: gpt-4.1-mini        # your AI Foundry deployment name
    max_log_lines: 500
    post_pr_comment: true
    include_fix_suggestion: true

  act:
    enabled: true
    auto_create_issue: true
    auto_adjust_gates: false
    suggest_deploy_strategy: true

  quality_gates:
    block_merge_above_risk: 90
    require_human_approval_on_act: true

  notify:
    pr_comment: true
    checks_api: true
    job_summary: true
    issue_on_failure: true

  exclude:
    paths:
      - "docs/**"
      - "**/*.md"
      - ".github/**"
    branches:
      - "dependabot/**"
      - "renovate/**"
```

### Minimal Config (Safe Defaults)

```yaml
devpilot:
  predict:
    enabled: true
```

Everything else uses sensible defaults.

### Aggressive Autonomous Config

```yaml
devpilot:
  predict:
    block_threshold: 80
  diagnose:
    model: gpt-4.1-mini
  act:
    auto_create_issue: true
    auto_adjust_gates: true
  quality_gates:
    require_human_approval_on_act: false
```

### Observability-Only Config (No Actions)

```yaml
devpilot:
  predict:
    enabled: true
    block_threshold: 100    # never block
  diagnose:
    enabled: true
  act:
    enabled: false          # no autonomous actions
```

---

## 7. Environment Overrides — Production vs Staging

### Description

Use the `environments` section to apply **stricter rules in production** while keeping development flexible.

### Step-by-Step: Configure Per-Environment Rules

**Step 1 — Add environment overrides**

```yaml
devpilot:
  predict:
    block_threshold: 90    # default for all branches

  environments:
    production:
      quality_gates:
        block_merge_above_risk: 70    # much stricter in prod
      act:
        require_human_approval_on_act: true

    staging:
      quality_gates:
        block_merge_above_risk: 85

    development:
      quality_gates:
        block_merge_above_risk: 95   # very lenient in dev
```

**Step 2 — DevPilot auto-detects environment from branch name**

| Branch Pattern | Environment Applied |
|---|---|
| `main`, `master`, `prod*` | `production` |
| `staging`, `stage` | `staging` |
| Everything else | `development` |

**Example**: A PR targeting `main` with score 75 → **blocked** (prod threshold: 70).
The same change targeting `develop` with score 75 → **allowed** (dev threshold: 95).

---

## 8. Exclusions — Skipping Paths and Branches

### Description

Some changes (documentation, dependency bots, config files) don't need pipeline risk analysis. Use `exclude` to skip them entirely.

### Step-by-Step: Configure Exclusions

```yaml
devpilot:
  exclude:
    paths:
      - "docs/**"           # all docs changes
      - "**/*.md"           # all markdown files
      - ".github/**"        # GitHub config files
      - "**/*.lock"         # lockfiles (package-lock.json etc.)
      - "infra/**"          # Terraform changes (different risk profile)

    branches:
      - "dependabot/**"     # Dependabot auto-updates
      - "renovate/**"       # Renovate auto-updates
      - "release/**"        # Release branches (managed separately)
```

When a PR only touches excluded paths, DevPilot skips all agents and marks the check as **skipped**.

---

## Summary Table

| Feature | When It Runs | What It Creates | Default State |
|---|---|---|---|
| **Predict** | On every `push` / `pull_request` | GitHub Check Run with risk score | ✅ Enabled |
| **Diagnose** | On `workflow_run` failure | PR comment with root cause + fix | ✅ Enabled |
| **Act** | After Diagnose completes | GitHub Issue + deploy recommendation | ✅ Enabled (human approval required) |
| **Quality Gates** | Part of Predict | Blocks/warns merge based on score | Warn ≥70, Block ≥90 |
| **Notifications** | All agents | PR comments, checks, issues, summaries | All on |
| **Exclusions** | Before all agents | Skips analysis for matched paths/branches | docs/**, *.md |

---

## Real-World Verified Workflow (Live Test)

**Repository**: `dullasubhash007/devpilot`  
**PR #4**: test branch with intentional CI failure

```
1. Push to test/diagnose-act-e2e branch
   └─▶ DevPilot Predict fires within 5 seconds
       Score: 15/100 (low) ✅
       → PR Check: "Risk Score: 15/100 — LOW"

2. e2e-test-failure workflow runs → fails
   (missing pytest module — intentional)
   └─▶ DevPilot Diagnose fires
       Calls gpt-4.1-mini via Azure AI Foundry
       diagnosis = {
         "root_cause": "pytest module not installed",
         "fix_suggestion": "Add pip install pytest to workflow",
         "file": ".github/workflows/e2e-test-failure.yml",
         "confidence": "high"
       }
       → Posts PR comment with root cause + fix ✅

3. Diagnose → enqueues Act job
   └─▶ DevPilot Act fires
       Calls gpt-4.1-mini: "risk 50/100 → rolling deployment"
       act_decision = {
         "deploy_strategy": "rolling",
         "reasoning": "medium risk - rolling allows gradual rollout"
       }
       → Creates GitHub Issue #7 (labels: bug, devpilot) ✅
       → Updates PR comment with deploy recommendation ✅
```

**All three agents verified live** — view results at:
- **PR comment (Diagnose)**: https://github.com/dullasubhash007/devpilot/pull/4
- **GitHub Issue (Act)**: https://github.com/dullasubhash007/devpilot/issues/7
- **Predict check**: PR #5 — Risk Score: 15/100

---

*DevPilot — Predict. Diagnose. Act. All inside GitHub.*
