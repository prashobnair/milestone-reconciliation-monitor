# Contributing

Use synthetic data only. Set up with `uv sync --group dev`; run `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy --strict src`, and `uv run pytest --cov=milestone_monitor --cov-branch --cov-fail-under=80`. Core coverage must reach 90%. Open a PR; do not push directly to main. Put requirement IDs, test evidence, and any deviation in its body.
