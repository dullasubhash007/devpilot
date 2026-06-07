# DevPilot Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      GitHub (User Surface)                       │
│  • PR Checks tab    • PR Comments    • Job Summary    • Issues  │
└────────────────────────────────┬────────────────────────────────┘
                                 │ webhook events
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│           Azure Container Apps — ca-webhook                      │
│   FastAPI server · HMAC validation · routes to Storage Queues   │
│   Public HTTPS · System-assigned Managed Identity               │
└──────────┬───────────────────────────────────────────────────────┘
           │ enqueue to Storage Queue
           ▼
┌──────────────────────────────────────────────────────────────────┐
│           Azure Container Apps — ca-workers                       │
│   Async queue poller (predict-jobs / diagnose-jobs / act-jobs)   │
└──────────┬──────────────────────┬──────────────────┬─────────────┘
           │                      │                  │
           ▼                      ▼                  ▼
  ┌──────────────┐   ┌────────────────────────────────────────┐
  │ Azure ML     │   │         Azure AI Foundry               │
  │ Predict      │   │  Hub → Project → AI Services           │
  │ (serverless) │   │  Diagnose (GPT-4o-mini) + Act (SK)     │
  └──────────────┘   └────────────────────────────────────────┘
           │                      │
           └──────────────────────┼──────────────────────┐
                                  ▼                       │
           ┌──────────────────────────────────────┐       │
           │ Azure Cosmos DB (Serverless)          │       │
           │ pipeline_runs, predictions, diagnoses │       │
           └──────────────────────────────────────┘       │
                                                          ▼
                                            GitHub Checks API + Issues

   🔐 Azure Key Vault          ⚙️ Azure App Configuration
      (secrets)                   (feature flags, config)
   📊 Azure Monitor + App Insights
   📦 Azure Container Registry (acrdevpilotdev4056)
```

## Deployment Modes

| Mode | Compute | Use When |
|---|---|---|
| **Container Apps** (default new tenants) | 2× Container Apps | Free Trial / any subscription — no App Service quota needed |


Toggle via `use_container_apps = true/false` in tfvars.

## Resource Group Layout (Single Subscription)

| Resource Group | Purpose |
|---|---|
| `rg-devpilot-networking` | VNet, NSGs |
| `rg-devpilot-ai` | AI Foundry Hub/Project/AI Services, Azure ML, ACR |
| `rg-devpilot-compute` | Container Apps Environment + Apps (or Functions + APIM) |
| `rg-devpilot-data` | Cosmos DB, Storage Account, Storage Queues |
| `rg-devpilot-security` | Key Vault, App Configuration |
| `rg-devpilot-monitoring` | Log Analytics, App Insights |
| `rg-devpilot-tfstate` | Terraform remote state (separate, bootstrap-only) |

## Agent Responsibilities

### 🔮 Predict Agent
- **Trigger**: `push` / `pull_request` webhook
- **Input**: diff size, files changed, test history, author history, branch age
- **Output**: failure probability score (0–100) + label (low/medium/high/critical)
- **Backend**: Azure ML serverless endpoint; heuristic fallback when unavailable
- **Surface**: GitHub Checks API (✅ success / ⚠️ neutral / ❌ failure)

### 🔍 Diagnose Agent
- **Trigger**: `workflow_run` webhook with `conclusion: failure`
- **Input**: workflow logs (last N lines) + PR diff
- **Output**: structured JSON `{root_cause, fix_suggestion, file, line, confidence}`
- **Backend**: Azure AI Foundry (Hub → Project → AI Services) GPT-4o-mini
- **Surface**: PR comment + Job Summary

### 🤖 Act Agent
- **Trigger**: After Diagnose completes (via act-jobs queue)
- **Input**: Predict score + Diagnose payload + repo config
- **Output**: Actions — create issue, recommend deploy strategy, adjust gates
- **Backend**: Semantic Kernel + Azure AI Foundry orchestration
- **Surface**: GitHub Issue + PR comment update

## Event Flow

```
push / pull_request event
  └─▶ ca-webhook (validate HMAC)
      └─▶ predict-jobs queue
          └─▶ ca-workers (predict_trigger)
              ├─▶ Azure ML / heuristic scorer
              ├─▶ GitHub Checks API (create check run)
              └─▶ Cosmos DB (upsert predict result)

workflow_run failure event
  └─▶ ca-webhook (validate HMAC)
      └─▶ diagnose-jobs queue
          └─▶ ca-workers (diagnose_trigger)
              ├─▶ GitHub API (fetch logs + diff)
              ├─▶ Azure AI Foundry GPT-4o-mini (diagnose)
              ├─▶ GitHub PR comment (post diagnosis)
              ├─▶ Cosmos DB (upsert diagnosis)
              └─▶ act-jobs queue
                  └─▶ ca-workers (act_trigger)
                      ├─▶ Semantic Kernel + AI Foundry (decide actions)
                      ├─▶ GitHub Issues API (create issue)
                      └─▶ Cosmos DB (upsert actions)
```

## Configuration Resolution Chain

```
1. .devpilot.yml in repo (highest priority)
2. Azure App Configuration (global defaults / feature flags)
3. Hardcoded defaults in src/config/defaults.py
```

Secrets are **never** in repo config — fetched at runtime from Azure Key Vault via Managed Identity.

## CI/CD Pipeline

```
PR opened/updated
  └─▶ terraform-plan.yml   → plan infra, post diff as PR comment

Push to master (infra/ changed)
  └─▶ terraform-apply.yml  → apply Terraform automatically
                              (OIDC auth — no stored secrets)

Push to master (src/ changed)
  └─▶ deploy-container-apps.yml → docker build + push to ACR
                                    → update ca-webhook + ca-workers
                                    → verify /health endpoint
```
