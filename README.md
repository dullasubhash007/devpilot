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
| 🔍 **Diagnose** | Azure OpenAI (GPT-4o-mini) | Root cause analysis + fix suggestions on failure |
| 🤖 **Act** | Semantic Kernel + Azure AI Foundry | Adjusts quality gates, recommends deploy strategy, creates issues |

> **Datadog observes. Harness accelerates. DevPilot predicts, diagnoses, and acts — autonomously.**

---

## 🏗️ Architecture

```
GitHub App  ──▶  Azure API Management  ──▶  Azure Functions
                                                  │
                ┌─────────────────────────────────┼─────────────────┐
                ▼                                 ▼                 ▼
        Azure ML (Predict)          Azure OpenAI (Diagnose)   AI Foundry (Act)
                │                                 │                 │
                └─────────────► Azure Cosmos DB ◄─────────────────┘
                                       │
                            GitHub Checks / PR Comments / Job Summary
```

See [docs/architecture/](docs/architecture/) for the detailed diagram.

---

## ⚡ Quick Start

### 1. Install the GitHub App
👉 [Install DevPilot on your repo](#) *(coming soon)*

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
| Agent Orchestration | Azure AI Foundry + Semantic Kernel |
| Prediction Model | Azure ML (AutoML / scikit-learn) |
| Language Model | Azure OpenAI GPT-4o-mini |
| Backend | Azure Functions (Python 3.11) |
| API Layer | Azure API Management (Consumption) |
| Config | Azure App Configuration |
| Secrets | Azure Key Vault |
| Database | Azure Cosmos DB (Serverless) |
| IaC | Terraform (Azure Verified Modules) |
| Monitoring | Azure Monitor + App Insights |
| CI/CD | GitHub Actions |

---

## 📁 Repository Structure

```
devpilot/
├── infra/                 # Terraform AVM modules (Azure infrastructure)
├── src/
│   ├── agents/            # Predict, Diagnose, Act agents
│   ├── functions/         # Azure Functions handlers
│   ├── github/            # GitHub API clients (Checks, PR, Issues)
│   ├── shared/            # Common utilities
│   └── config/            # Config loading (.devpilot.yml + App Config)
├── .github/workflows/     # CI/CD pipelines
├── docs/                  # Architecture, schemas, guides
├── tests/                 # Unit + integration tests
└── .devpilot.yml          # Sample config (DevPilot eats its own dog food)
```

---

## 🚀 Deployment

### Prerequisites
- Azure subscription (free tier OK; ~$60–120/mo at full scale)
- Terraform >= 1.6
- Azure CLI logged in (`az login`)
- GitHub App registered (see [docs/github-app-setup.md](docs/github-app-setup.md))

### Deploy Azure Infrastructure
```bash
cd infra
terraform init
terraform plan -var-file=parameters/dev.tfvars
terraform apply -var-file=parameters/dev.tfvars
```

### Deploy Functions
```bash
cd src/functions
func azure functionapp publish <function-app-name>
```

---

## 📊 Evaluation Criteria Alignment (Microsoft Build AI 2026)

| Criteria | Weight | DevPilot Strategy |
|---|---|---|
| AI Integration & Intelligence Design | 25% | 3 specialized agents — Azure ML + OpenAI + Semantic Kernel |
| System Architecture & Engineering Quality | 25% | Terraform AVM, Landing Zone principles, event-driven |
| Communication, Presentation & UX | 15% | 100% GitHub-native UX — no context switching |
| Prototype Readiness & Scalability | 15% | Fully deployed, IaC, multi-env, demo on live repo |
| Problem Depth & Product Clarity | 10% | Measurable MTTR reduction, real pain point |
| Market Understanding & Product Fit | 10% | Clear gap vs Datadog/Harness — actively *acts* |

---

## 🧠 AI Tools Disclosure

Per hackathon rules, the following AI tools were used in development:
- **GitHub Copilot** — Code completion and refactoring
- **Azure OpenAI GPT-4o** — Architecture brainstorming and documentation drafting
- All architectural decisions, agent design, and core engineering were done by the human team.

---

## 👥 Team

| Name | Role |
|------|------|
| *Team Member 1* | *Role* |
| *Team Member 2* | *Role* |

---

## 📝 License

MIT License — see [LICENSE](LICENSE).

---

## 🙏 Acknowledgements

- **Microsoft Build AI Hackathon 2026** for the challenge
- **Azure Verified Modules (AVM)** team for the IaC foundation
- The open-source community
