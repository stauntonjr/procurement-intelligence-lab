.PHONY: check check-fast dependabot-validate semantic-preflight actions-supply-chain unit contract integration regression coverage-ratchet package-smoke challenge-validate challenges eval demo github-plan-preflight github-plan-audit github-plan-sync-views

check-fast:
	uv run --extra workflow ruff format --check .
	uv run --extra workflow ruff check .
	uv run --extra workflow pyright
	uv run --extra workflow python tools/check_architecture.py
	uv run --extra workflow python tools/run_challenges.py --validate-only
	$(MAKE) semantic-preflight
	$(MAKE) dependabot-validate
	$(MAKE) actions-supply-chain

semantic-preflight:
	uv run --extra workflow python tools/validate_semantic_change.py --skills --evidence docs/development/semantic-change-evidence.example.json --routing evals/development_agents/skill-routing.json
	uv run --extra workflow pytest -q tests/unit/test_semantic_change_harness.py tests/unit/test_pr_contract.py

dependabot-validate:
	uv run --extra workflow pytest -q tests/unit/test_dependabot_config.py

actions-supply-chain:
	uv run --extra workflow python tools/check_actions_supply_chain.py

unit:
	uv run --extra workflow pytest -q tests/unit

contract:
	uv run --extra workflow pytest -q -m contract

integration:
	uv run --extra workflow pytest -q -m integration

regression:
	uv run --extra workflow pytest -q -m regression

check: check-fast
	uv run --extra workflow pytest --cov=procurement_intelligence_lab --cov-branch --cov-report=term-missing --cov-report=xml --cov-fail-under=85
	uv run --extra workflow python tools/check_coverage_ratchet.py
	@uv run --extra workflow python -c "from pathlib import Path; required=['AGENTS.md','README.md','docs/project/handoff.md','docs/architecture/overview.md','docs/architecture/platform-semantics.md','docs/domains/procurement/semantic-model.md','docs/architecture/evidence-and-ux.md']; missing=[p for p in required if not Path(p).exists()]; print(f'missing: {missing}' if missing else 'architecture checks passed'); raise SystemExit(1 if missing else 0)"

package-smoke:
	uv run --extra workflow python tools/package_smoke.py

challenge-validate:
	uv run --extra workflow python tools/run_challenges.py --validate-only

challenges:
	uv run --extra workflow python tools/run_challenges.py --verify-known-bad --results artifacts/challenges/latest.json

eval:
	uv run --extra workflow python tools/run_challenges.py --validate-only
	@echo 'Development-agent challenge manifests are valid; model benchmark execution remains an explicit authorized activity.'

demo:
	uv run --extra workflow python -m procurement_intelligence_lab

github-plan-preflight:
	uv run --extra workflow python tools/github_planning.py preflight

github-plan-audit:
	uv run --extra workflow python tools/github_planning.py audit

github-plan-sync-views:
	uv run --extra workflow python tools/github_planning.py sync-views --apply
