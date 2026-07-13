Customer folder submission example
==================================

Submit one subfolder per PI Vision display:

  your-company-migration/
    ops-overview/
      screenshot.png     ← PI Vision screen capture (PNG/JPG)
      tags.csv           ← panel list + PI tags (required)
      display.json       ← display name, element_id, theme (optional)
    p101-pump/
      screenshot.png
      tags.csv
      display.json

Run:
  ./run.sh ingest-folder /path/to/your-company-migration -o scenarios/generated.json
  ./run.sh migrate scenarios/generated.json

tags.csv columns:
  panel_key, title, type, element_id, pi_tags, prompt

pi_tags: separate multiple tags with |  e.g.  tag1|tag2|tag3

chart type values:
  trend, gauge, kpi, bar, pie, scatter, bar-gauge, state
  process, pid, pnid  -> editable IDMP Canvas P&ID

P&ID starter:
  scenarios/examples/pump-train-pnid/

Before using it from the CLI, replace element_id 0 in tags.csv and display.json
with a real ID returned by:
  ./run.sh validate --keyword YOUR_ASSET

Migration Studio can retarget this example automatically after you select an
element returned by the asset search.

Screenshots are stored as reference in the generated scenario.
An AI agent (Cursor) can open them to refine layout and titles before migrate.
