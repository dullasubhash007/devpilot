# DevPilot Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      GitHub (User Surface)                       │
│  • PR Checks tab    • PR Comments    • Job Summary    • Issues  │
└────────────────────────────────┬────────────────────────────────┘
                                 │ webhook + API
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Azure API Management (APIM)                     │
│           Validates GitHub webhook signature + rate limit        │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              Azure Functions (Python 3.11)                       │
│   webhook_handler → routes to predict / diagnose / act triggers │
└──────────┬──────────────────┬──────────────────────────────────┘
           │                  │
           ▼                  ▼
   ┌──────────────┐   ┌────────────────────────────────────────┐
   │ Azure ML     │   │         Azure AI Foundry               │
   │ Predict      │   │  Hub → Project → AI Services           │
   │ (serverless) │   │  Diagnose (GPT-4o-mini) + Act          │
   └──────────────┘   │  + Semantic Kernel orchestration       │
           │          └────────────────────────────────────────┘
           │                  │
           └──────────────────┼──────────────────┘
                              ▼
           ┌──────────────────────────────────────┐
           │ Azure Cosmos DB (Serverless)         │
           │ pipeline runs, predictions, actions  │
           └──────────────────────────────────────┘

   🔐 Azure Key Vault          ⚙️ Azure App Configuration
      (secrets)                   (feature flags, endpoints)

   📊 Azure Monitor + App Insights (observability across all)
```

## Resource Group Layout (Single Subscription)

| Resource Group | Purpose |
|---|---|
| `rg-devpilot-networking` | VNet, NSGs, Service Endpoints |
| `rg-devpilot-ai` | AI Foundry Hub + Project + AI Services, Azure ML |
| `rg-devpilot-compute` | Functions, Container Apps, APIM |
| `rg-devpilot-data` | Cosmos DB, Storage, AI Search |
| `rg-devpilot-security` | Key Vault, App Configuration |
| `rg-devpilot-monitoring` | Log Analytics, App Insights |

## Agent Responsibilities

### 🔮 Predict Agent
- **Trigger**: `push` / `pull_request` webhook
- **Input**: diff size, files changed, test history, author history
- **Output**: failure probability (0–100)
- **Backend**: Azure ML serverless endpoint (scikit-learn / AutoML)
- **Surface**: GitHub Checks API (yellow ⚠️ or red ❌ check)

### 🔍 Diagnose Agent
- **Trigger**: `workflow_run` webhook with `conclusion: failure`
- **Input**: workflow logs + diff + test output (chunked)
- **Output**: structured JSON `{root_cause, fix_suggestion, file, line}`
- **Backend**: Azure AI Foundry (Hub → Project → AI Services) GPT-4o-mini with structured outputs
- **Surface**: PR comment + Job Summary

### 🤖 Act Agent
- **Trigger**: After Diagnose completes
- **Input**: Predict score + Diagnose payload + repo config
- **Output**: Decisions (adjust gate? create issue? recommend deploy?)
- **Backend**: Semantic Kernel + Azure AI Foundry orchestration
- **Surface**: GitHub Issue + PR comment update + Checks status

## Configuration Resolution Chain

```
1. Read .devpilot.yml from repo (highest priority)
2. Merge with Azure App Configuration (global defaults)
3. Fall back to hardcoded defaults in src/config/defaults.py
```

Secrets are **never** in repo config — fetched at runtime from Azure Key Vault using managed identity.
