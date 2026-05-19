# Contributing to DevPilot

Thanks for your interest! DevPilot is a Microsoft Build AI Hackathon 2026 project. We welcome contributions during and after the hackathon.

## Development Setup

```bash
# 1. Clone
git clone <repo-url>
cd devpilot

# 2. Python env
python -m venv .venv
.\.venv\Scripts\Activate.ps1     # PowerShell on Windows
pip install -r src/functions/requirements.txt

# 3. Copy env
cp .env.example .env
# Fill in Azure values

# 4. Run tests
pytest tests/
```

## Coding Standards
- Python 3.11+, PEP 8 (use `ruff`)
- Type hints required on public functions
- Tests for any new behavior

## Commit Style
Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`

## PR Checklist
- [ ] Tests added/updated
- [ ] Docs updated if behavior changed
- [ ] `terraform fmt` / `terraform validate` pass for infra changes
- [ ] No secrets committed
