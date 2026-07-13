# Houston PI Vision → IDMP Canvas — DEMO PACK

**Use this ZIP (not the built-in example):**  
`~/Desktop/houston-refinery-pivision-demo.zip`

**Migration Studio:** http://127.0.0.1:8765  
**Under the hood / what customers must provide:** see `README.md` in this folder (also `~/Desktop/Houston-Under-The-Hood.md`).
**Start live data before you publish** (leave this terminal open):

```bash
cd ~/tdengine-idmp-deployment/agentic-pi-migration
python3 scenarios/examples/houston-refinery-pivision/start-demo-data.py
```

---

## Demo click path (do this live)

1. Open Migration Studio → Connect to `http://localhost:6842` (your usual login)
2. Upload **`houston-refinery-pivision-demo.zip`**
3. Paste the **Global design direction** prompt below
4. Check **Create new**
5. Leave **External LLM helps IDMP create panels** checked (uses your OpenAI key as co-pilot)
6. Click **Publish / Migrate** — watch the loading log (co-pilot → IDMP AI → QA)
7. Open the returned Canvas dashboard URL
8. Say the talk track while pointing at feed → column → outlets → live trends

---

## How the external LLM helps IDMP’s internal AI (say this if asked)

Two different AIs — they don’t replace each other:

| Role | What it is | What it does |
|------|------------|--------------|
| **External LLM** | OpenAI (`QA_LLM_API_KEY`) in Migration Studio | Co-pilot — rewrites each panel prompt using title, tags, design direction, and live time window |
| **IDMP internal AI** | IDMP `POST /api/v1/ai/panels/create` | Builds the real panel (type, series, chart chrome) inside IDMP |
| **Fallback** | `tags.csv` series bindings | If IDMP AI fails, panels are still created from tags |

**Talk line (15s):**

> “OpenAI doesn’t create the IDMP panel — it co-pilots the brief.  
> It turns our tags and design direction into a tight prompt for IDMP’s own panel AI.  
> IDMP builds the panel; if that misses, we fall back to the tag map so the demo still goes live.”

```text
tags + prompt + design direction
        ↓
External LLM  →  stronger IDMP prompt
        ↓
IDMP internal AI  →  creates panel
        ↓
(if fail) series from tags.csv
```

After publish, the same external LLM can **QA** the result (loading UI streams score, issues, fixes).

---

## Prompt (paste into “Global design direction”)

```text
Recreate PI Vision Houston Refinery Unit 3-1415 as a MODERN precision P&ID on TDengine IDMP — same exact process elements and topology as the screenshot, but zero old-school SCADA look. Deep slate canvas, soft rounded stage, thin hairline chrome, tag chips on valves/columns/pump, glass PV/SP cards, polished Feed QC data table, Plant/Storage destination pills, fast cyan animated pipelines, and LIVE badges. Keep every element and the precise left-to-right flow: feed Sched/Actual into C-1309, LC-780 mid transfer, side column, FC-009, P-24/09A pump, then FC-010 (Plant) / FC-011 / FC-012 (Storage) on an orthogonal header. Bind live PV/SP Formula readings with gpm units. Place Flow Control Valve Readings top-right and Feed Flow bottom-right. Time window now-8h → now, 2s refresh. Prefer IDMP 3D symbols (ball valves, storage-tank vessels). Result should feel like a 2026 operator console: modern, ready, razor-precise — not a 2010s PI Vision clone. After publish, an external LLM QA agent can quality-check the generated IDMP panel/Canvas against the screenshot + tags + display plan (topology, live bindings, modernity, demo-readiness) via ./run.sh qa <report.json> --folder <customer-folder>.
```

---

## What you say (≈ 2 minutes)

### 1) Setup beat — while Studio is open (15s)

> “Customers don’t want us to rebuild PI Vision by hand.  
> They hand us a folder — screenshot plus tags — we zip it, drop it here, and migrate.”

Upload the ZIP as you say this.

### 2) Prompt beat (10s)

> “This global design direction tells the agent the visual intent.  
> The exact layout still comes from `display.json` in the ZIP — screenshot + tags + Canvas plan.”

Paste the prompt.

### 3) Publish beat (20s)

> “Create new — and leave external LLM assist on.  
> OpenAI co-pilots the prompts; IDMP’s internal AI creates the panels.  
> Then the QA agent scores what we published.”

Click Publish. Point at the loading log while co-pilot / IDMP AI / QA run.

### 4) Open the Canvas (20s)

> “This is Houston Refinery Unit 3-1415 — the same operator mental model as PI Vision, now inside IDMP.”

Point left → right:

> “Feed in… main column C-1309… LC-780… side column… pump P-24/09A… three product lines to Plant and Storage.”

### 5) Live data beat (20s)

> “These aren’t static labels. PV and SP are live Formula bindings on GTU historian tags — updating every couple of seconds.”

Point at **Flow Control Valve Readings**, then **Feed Flow**:

> “Same trend story PI Vision had — product valves up here, feed scheduled vs actual down here.”

### 6) Editable proof (25s)

Open the Canvas editor:

> “Critical difference from a PNG or a GIF: this is a native Meta2d Canvas.  
> Every pipe, valve, and value is editable. We migrated — we didn’t freeze a picture.”

Optional:

> “Screenshot for likeness. Tags for live data. Canvas for ownership.”

### 7) Close (15s)

> “So the pitch is simple: keep the display operators already trust, put it on TDengine IDMP with live history, and leave it editable for the plant team.  
> Happy to walk the ZIP contents or a tag binding next.”

---

## Fallback lines

**If trends look empty:**

> “Data simulator wasn’t running — one second…”  
Then start `start-demo-data.py` and refresh.

**If publish says name already exists:**

> “We’ll create under a fresh name.”  
Re-publish with **Create new** still checked, or rename the display in Studio if shown.

**If someone asks “does ChatGPT create the dashboard?”:**

> “No — it co-pilots the panel prompts. IDMP’s own panel AI creates the charts. Layout comes from the ZIP’s Canvas plan.”

**If someone asks “is this computer vision?”:**

> “No — screenshot-guided. The ZIP carries the structured Canvas plan and tag map. That’s how we get exact, repeatable migrations.”
