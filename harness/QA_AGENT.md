# External LLM QA agent (harness)

After migrate, an optional **quality-check agent** scores the generated IDMP Canvas/panel against the customer folder (screenshot + tags + `display.json`) and the migration report.

## Quick start

```bash
# 1) Migrate (writes reports/latest.json)
./harness/run-agent-workflow.sh full scenarios/examples/houston-refinery-pivision

# 2) Or QA an existing report
export QA_LLM_API_KEY=sk-...          # or OPENAI_API_KEY / ANTHROPIC_API_KEY
export QA_LLM_PROVIDER=openai         # or anthropic
export QA_LLM_MODEL=gpt-4.1

./run.sh qa reports/houston-refinery-pivision.json \
  --folder scenarios/examples/houston-refinery-pivision \
  -o reports/houston-qa.json
```

Structural-only (no LLM key):

```bash
./run.sh qa reports/houston-refinery-pivision.json \
  --folder scenarios/examples/houston-refinery-pivision \
  --structural-only
```

## What it checks

| Layer | What |
|-------|------|
| **Structural** | Live panels, URL present, `now-*` → `now` window, no diagonal pipes, no archived 20xx footer dates, tags present |
| **LLM judge** | Topology, precision, live data, modernity, completeness, demo-readiness (rubric in `agentic_pi_migration/qa/rubric.py`) |

Vision models can receive the reference screenshot when `--folder` includes `screenshot.*`.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | `pass` (or `needs_review` with `--allow-review`) |
| 2 | `fail` |
| 3 | `needs_review` |

Does **not** change migrate — it only reviews what was published.
