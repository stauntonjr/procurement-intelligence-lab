.PHONY: check check-fast unit contract integration regression package-smoke challenge-validate challenges eval demo

check-fast:
	uv run ruff format --check .
	uv run ruff check .
	uv run pyright
	uv run python tools/check_architecture.py
	uv run python tools/run_challenges.py --validate-only

unit:
	uv run pytest -q tests/unit

contract:
	uv run pytest -q -m contract

integration:
	uv run pytest -q -m integration

regression:
	uv run pytest -q -m regression

check: check-fast
	uv run pytest --cov=procurement_intelligence_lab --cov-branch --cov-report=term-missing --cov-fail-under=85
	@uv run python -c "from pathlib import Path; required=['AGENTS.md','README.md','docs/project/handoff.md','docs/architecture/overview.md','docs/domain/semantic-model.md','docs/architecture/evidence-and-ux.md']; missing=[p for p in required if not Path(p).exists()]; print(f'missing: {missing}' if missing else 'architecture checks passed'); raise SystemExit(1 if missing else 0)"

package-smoke:
	uv run python tools/package_smoke.py

challenge-validate:
	uv run python tools/run_challenges.py --validate-only

challenges:
	uv run python tools/run_challenges.py

eval:
	uv run python tools/run_challenges.py --validate-only
	@echo 'Development-agent challenge manifests are valid; model benchmark execution remains an explicit authorized activity.'

demo:
	uv run python -m procurement_intelligence_lab
