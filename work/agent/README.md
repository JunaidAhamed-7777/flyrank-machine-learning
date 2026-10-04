# Refresh Signal Scout (MVP)

Weekly arXiv-only digest for the FlyRank content-refresh capstone lane.

## Run locally

From the repository root:

```bash
python work/agent/run.py
```

Stdout logs each arXiv fetch (URL, status, bytes, item count), filter counts, and digest paths.

## Tests

```bash
pip install -r work/agent/requirements-dev.txt
pytest work/agent/tests/
```

## Schedule

Workflow definition: `work/agent/workflows/refresh-signal-scout.yml` (`cron: '0 8 * * 1'` Monday 08:00 UTC).

GitHub only runs workflows from `.github/workflows/`. Copy this file there (or symlink) before enabling the cron job.

## Outputs

- `work/agent/digests/YYYY-MM-DD.md`
- `work/agent/digests/index.md` (append-only)

Design record: `spec.md`, `evals.md`, `agent_instructions.md`.
