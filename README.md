# DevPilot 🚀

> **Predictive CI/CD Intelligence — AI-native, GitHub-native**

DevPilot is an AI-powered GitHub App that **predicts pipeline failures before they happen**, **diagnoses root causes** when they do, and **autonomously acts** to keep your delivery pipeline flowing — all inside GitHub's native UI.

**Built for the Microsoft Build AI Hackathon 2026** — Track: *AI-Powered Production Function: Reinventing Work*

---

## 🎯 The Problem

Every dev team wastes **45–90 minutes per day** firefighting broken CI/CD pipelines:
- Build fails after 20 minutes → developer reads cryptic logs → guesses cause → fixes → repeats
- Flaky tests, wrong deployment strategies, missed quality gates — all discovered *after the fact*
- Existing tools (Datadog, Harness, LinearB) **observe** but don't **act**

## 💡 Our Solution

DevPilot deploys 3 specialized AI agents that work together inside your GitHub workflow:

| Agent | Powered By | What It Does |
|-------|-----------|--------------|
| 🔮 **Predict** | Azure ML | Scores failure probability *before* the pipeline runs |
| 🔍 **Diagnose** | Azure AI Foundry (GPT-4o-mini) | Root cause analysis + fix suggestions on failure |
| 🤖 **Act** | Semantic Kernel + Azure AI Foundry | Adjusts quality gates, recommends deploy strategy, creates issues |

> **Datadog observes. Harness accelerates. DevPilot predicts, diagnoses, and acts — autonomously.**

---

## 🏗️ Architecture

```
GitHub App  ──▶  Azure Container Apps (webhook)  ──▶  Storage Queues
                                                              │
                 ┌────────────────────────────────────────────┤
                 ▼                          ▼                  ▼
         Azure ML (Predict)    Azure AI Foundry (Diagnose+Act)  Cosmos DB
                 │                          │                  │
                 └──────────────────────────┼──────────────────┘
                                            ▼
                                GitHub Checks / PR Comments / Issues
```

See [docs/architecture/README.md](docs/architecture/README.md) for the detailed diagram.

---

## ⚡ Quick Start

### 1. Install the GitHub App
👉 Install **DevPilot** on your repository via the GitHub App settings.

Register your own instance — see [docs/github-app-setup.md](docs/github-app-setup.md).

### 2. Add `.devpilot.yml` to your repo
```yaml
devpilot:
  predict:
    enabled: true
    failure_threshold: 70
  diagnose:
    enabled: true
    model: gpt-4o-mini
  act:
    auto_create_issue: true
```

See [.devpilot.yml schema](docs/devpilot-yml-schema.md) for the full reference.

### 3. Push code and watch DevPilot work
- 🔮 **Predict score** appears as a GitHub Check on every PR
- 🔍 **Diagnosis comment** posted automatically when a pipeline fails
- 🤖 **Auto-generated issue** with root cause + fix suggestion

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| GitHub Integration | GitHub App, Webhooks, Checks API |
| Webhook Server | Azure Container Apps (FastAPI + Python 3.11) |
| Agent Orchestration | Azure AI Foundry + Semantic Kernel |
| Prediction Model | Azure ML (AutoML / scikit-learn) |
| Language Model | Azure AI Foundry (GPT-4o-mini) |
| API Layer | Azure Container Apps (public HTTPS ingress) |
| Config | Azure App Configuration |
| Secrets | Azure Key Vault |
| Database | Azure Cosmos DB (Serverless) |
| Container Registry | Azure Container Registry |
| IaC | Terraform (Azure Verified Modules) |
| Monitoring | Azure Monitor + App Insights |
| CI/CD | GitHub Actions (OIDC — no stored secrets) |

---

## 📁 Repository Structure

```
devpilot/
├── infra/                 # Terraform AVM modules (Azure infrastructure)
│   ├── modules/
│   │   ├── ai-foundry/    # AI Hub + Project + AI Services
│   │   ├── container-apps/# Webhook + Worker Container Apps
│   │   ├── azure-ml/      # ML workspace for Predict agent
│   │   ├── cosmos-db/     # Cosmos DB + Storage + Queues
│   │   └── ...            # keyvault, networking, monitoring, etc.
│   ├── backends/          # Per-environment .tfbackend files (gitignored)
│   ├── parameters/        # Per-environment .tfvars
│   └── scripts/           # bootstrap-backend.ps1, deploy-new-tenant.ps1
├── src/
│   ├── api/               # FastAPI webhook server (Container App)
│   ├── workers/           # Queue worker (Container App)
│   ├── agents/            # Predict, Diagnose, Act agents
│   ├── functions/         # Azure Functions handlers (MCAPS deployment)
│   ├── github/            # GitHub API clients (Checks, PR, Issues)
│   ├── shared/            # Config, Key Vault, Cosmos, logging utils
│   └── config/            # Config schema + defaults
├── .github/workflows/     # CI/CD pipelines
│   ├── terraform-plan.yml        # PR: plan infra, post comment
│   ├── terraform-apply.yml       # Push to master: apply infra
│   ├── deploy-container-apps.yml # Push to master: build + deploy image
│   └── deploy-functions.yml      # Push to master: deploy Azure Functions
├── docs/                  # Architecture, schemas, guides
├── tests/                 # Unit + integration tests
├── Dockerfile             # Multi-stage build for Container Apps
└── .devpilot.yml          # Sample config (DevPilot eats its own dog food)
```

---

## 🚀 Deployment

### Prerequisites
- Azure subscription (Free Trial supported via Container Apps mode)
- Terraform >= 1.6
- Azure CLI logged in (`az login`)
- GitHub App registered (see [docs/github-app-setup.md](docs/github-app-setup.md))

### Deploy to a New Subscription

```powershell
# 1. Bootstrap Terraform backend
cd infra/scripts
.\bootstrap-backend.ps1 -BackendName my-env

# 2. Init + Plan + Apply
cd ..
terraform init -backend-config=backends/my-env.tfbackend
terraform plan  -var-file=parameters/new-tenant-dev.tfvars
terraform apply -var-file=parameters/new-tenant-dev.tfvars
```

> **Free Trial subscriptions**: Set `use_container_apps = true` in your tfvars.
> Container Apps replaces Azure Functions + APIM and has no quota restrictions.

### Deploy via CI/CD (GitHub Actions)
See [.github/workflows/](/.github/workflows/) — push to `master` auto-applies.
GitHub Secrets required: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `TF_BACKEND_CONFIG`.

---

## 🌐 Live Deployment

| Tenant | Subscription | Mode |
|---|---|---|
| MCAPS (subhashdulla@microsoft.com) | ef71fd3a | Azure Functions + APIM |
| AI Hackathon (aihackathon26@outlook.com) | 71548670 | Azure Container Apps |

**Webhook URL (AI Hackathon tenant):**
```
https://ca-webhook-dev-pbrv5.bluepebble-41adbc9a.eastus2.azurecontainerapps.io/devpilot/webhook
```

---

## 📊 Evaluation Criteria Alignment (Microsoft Build AI 2026)

| Criteria | Weight | DevPilot Strategy |
|---|---|---|
| AI Integration & Intelligence Design | 25% | 3 specialized agents — Azure ML + AI Foundry + Semantic Kernel |
| System Architecture & Engineering Quality | 25% | Terraform AVM, Landing Zone principles, event-driven, OIDC CI/CD |
| Communication, Presentation & UX | 15% | 100% GitHub-native UX — no context switching |
| Prototype Readiness & Scalability | 15% | Fully deployed on 2 Azure tenants, IaC, multi-env, live demo |
| Problem Depth & Product Clarity | 10% | Measurable MTTR reduction, real pain point |
| Market Understanding & Product Fit | 10% | Clear gap vs Datadog/Harness — actively *acts* |

---

## 🧠 AI Tools Disclosure

Per hackathon rules, the following AI tools were used in development:
- **GitHub Copilot** — Code completion, refactoring, and pair programming
- **Azure OpenAI GPT-4o** — Architecture brainstorming and documentation drafting
- All architectural decisions, agent design, and core engineering were done by the human team.

---

## 👥 Team

| Name | Role |
|------|------|
| Subhash Naidu Dulla | Lead Engineer |

---

## 📝 License

MIT License — see [LICENSE](LICENSE).

---

## 🙏 Acknowledgements

- **Microsoft Build AI Hackathon 2026** for the challenge
- **Azure Verified Modules (AVM)** team for the IaC foundation
- The open-source community
