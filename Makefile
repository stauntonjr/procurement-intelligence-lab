.PHONY: check eval demo
check:
	uv run ruff format --check .
	uv run ruff check .
	uv run pyright
	uv run pytest
	@uv run python -c "from pathlib import Path; required=['AGENTS.md','README.md','docs/architecture/overview.md','docs/domain/semantic-model.md','docs/architecture/evidence-and-ux.md']; missing=[p for p in required if not Path(p).exists()]; print(f'missing: {missing}' if missing else 'architecture checks passed'); raise SystemExit(1 if missing else 0)"
eval:
	@echo 'M0 evaluation harness is scaffolded; benchmark manifests are not yet populated.'
demo:
	@echo 'M0 demo: no product features yet. Next demo is the one-synthetic-XLSX BOM vertical slice.'
