# Under the hood — how accurate Houston-class dashboards are made

This is what actually happens when you publish, and **exactly what a customer must provide** to get results as accurate as our Houston Refinery Unit 3-1415 demo.

---

## One-sentence truth

**Accuracy does not come from “the AI looking at a screenshot.”**  
It comes from a structured ZIP (layout + tags + screenshot reference), IDMP Agentic panel AI (optionally co-piloted by an external LLM), and live historian bindings — published over REST as an editable Canvas.

---

## Under the hood (publish pipeline)

```text
┌─────────────────────────────────────────────────────────────┐
│  Customer ZIP                                                │
│   screenshot.jpg   ← visual reference (not CV tracing)       │
│   tags.csv         ← which charts + which historian tags     │
│   display.json     ← precise Canvas pens / placements        │
└────────────────────────────┬────────────────────────────────┘
                             │ ingest
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  Migration Studio / CLI                                     │
│   • Optional Global design direction (human text)            │
│   • Optional External LLM (OpenAI) co-pilot                  │
│       rewrites each panel prompt from tags + design text     │
│   • IDMP internal AI  POST /api/v1/ai/panels/create          │
│       builds the real chart panel from that prompt           │
│   • Fallback: bind series directly from tags.csv             │
│   • CanvasBuilder: paint P&ID from display.json (deterministic)│
│   • Optional QA agent: external LLM scores the result        │
└────────────────────────────┬────────────────────────────────┘
                             │ REST only
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  TDengine IDMP                                              │
│   Editable Meta2d Canvas + live Formula / trend panels      │
│   Time window e.g. now-8h → now, refresh ~2s                 │
└─────────────────────────────────────────────────────────────┘
```

### Who does what?

| Piece | Role |
|-------|------|
| **`display.json`** | Source of truth for P&ID geometry (pipes, valves, columns, labels, PV/SP, QC card, panel slots). Same ZIP → same layout. |
| **`tags.csv`** | Source of truth for live charts (titles, types, `element_id`, PI/attribute tags, optional prompt notes). |
| **`screenshot.jpg`** | Human/agent reference while building the ZIP. **Not** computer vision. |
| **Global design direction** | Soft guidance (modern vs old-school, LIVE feel, etc.). Improves prompts; does not invent pipe coordinates. |
| **External LLM (OpenAI)** | Co-pilot: enriches panel prompts for IDMP AI; also can QA the published dashboard. Does **not** invent layout or tag names. |
| **IDMP internal AI** | Creates the actual chart panel objects inside IDMP. |
| **Series fallback** | If IDMP AI is down / fails → tool still creates charts from `pi_tags`. |
| **Historian / demo stream** | Makes numbers move. Empty trends ≠ bad layout; it means no data. |

---

## What a user must add to get dashboards as accurate as ours

Treat these as **required tiers**. Houston accuracy needs all of Tier A + B. Tier C is what makes it look “demo ready.”

### Tier A — must have (or you only get a rough dashboard)

| Deliverable | Why |
|-------------|-----|
| **IDMP element_id** where the tags live | Every panel binds to a real equipment / asset element. |
| **Matching attributes** on that element | Tag names in `tags.csv` must exist as IDMP attributes (or map 1:1). |
| **`tags.csv` with correct columns** | `panel_key`, `title`, `type`, `element_id`, `pi_tags` (pipe-separated), optional `prompt`. |
| **Live (or sim) historian data** | Without inserts/stream, trends and Formula PVs look dead. |
| **Working IDMP login** | REST publish needs `IDMP_URL` + user/password (or API key). |

Minimal `tags.csv` shape:

```csv
panel_key,title,type,element_id,pi_tags,prompt
product_flows,Flow Control Valve Readings,trend,2026702359773696,54FY026A.PV|54FY026B.PV|54FY026C.PV,multi-series FC product flows
feed_flow,Feed Flow,trend,2026702359773696,52FC001.SV|52FC001.PV,scheduled vs actual feed
```

### Tier B — required for Houston-level **layout accuracy**

| Deliverable | Why |
|-------------|-----|
| **`display.json` Canvas plan** | Orthogonal pipes, equipment positions, labels, PV/SP Formula pens, QC card, panel placements (`x,y,w,h`). This is why ours matches the PI Vision mental model pixel-tight. |
| **`screenshot.jpg` of the source PI Vision** | So operators/agents can verify likeness while authoring `display.json`. |
| **`dashboard_type: "canvas"`** | Forces editable P&ID Canvas (not a generic grid). |
| **Time window + refresh** | e.g. `time_from: "now-8h"`, `time_to: "now"`, `refresh_seconds: 2` for a LIVE feel. |
| **Panel placements that clear equipment** | Trends must not cover risers/valves (ours: product trends top-right, feed trend bottom-right). |

Without a real `display.json`, Studio can still publish charts from tags — but you will **not** get a precise P&ID twin.

### Tier C — polish that makes it look modern / demo-ready (what we added beyond PI Vision)

| Deliverable | Why |
|-------------|-----|
| **Global design prompt** | Modern slate, LIVE badges, no old-school SCADA chrome. |
| **External LLM assist on** | Better panel prompts into IDMP AI (`QA_LLM_API_KEY` + checkbox in Studio). |
| **IDMP 3D symbols** | Ball valves / storage-tank vessels in the Canvas pens. |
| **Animated pipes + LIVE chrome** | Pipe `autoPlay` / animate colors; footer `now-* → now` (never frozen 2020 dates). |
| **QA agent after publish** | External LLM scores topology, live data, modernity, demo-readiness. |
| **Optional `start-demo-data.py`** | Seeds/streams GTU tags so the room sees motion. |

---

## What you do **not** need

| Myth | Reality |
|------|---------|
| “Upload a screenshot and AI redraws it” | No. Screenshot is reference only. |
| “ChatGPT builds the dashboard” | No. It co-pilots **prompts**; IDMP AI (or tag series) builds panels; `display.json` builds the P&ID. |
| “One magic prompt is enough” | Prompt alone → vague results. Accuracy needs tags + layout plan. |
| “docker exec into IDMP” | Tool uses REST/SQL only. |

---

## Customer checklist (hand this out)

Copy this list for the next plant display:

- [ ] PI Vision **screenshot** of the target display  
- [ ] Export / list of **historian tags** with units and meaning  
- [ ] Confirmed **IDMP element_id** and attribute names (mapped from those tags)  
- [ ] `tags.csv` with one row per live chart  
- [ ] `display.json` Canvas plan (or ask us/an agent to author it from the screenshot grid)  
- [ ] Data flowing in TSDB for those attributes  
- [ ] Design direction text (modern / LIVE / match brand)  
- [ ] Optional: `QA_LLM_API_KEY` for co-pilot + QA  

Pack as:

```text
my-display/
  screenshot.jpg
  tags.csv
  display.json
```

Zip the folder → Migration Studio → Create new → Publish.

---

## Why our Houston demo looks so accurate

1. **Layout was authored**, not inferred — `generate-layout.py` → `display.json` with a 10px grid and orthogonal routing.  
2. **Tags matched a real GTU element** with live attributes.  
3. **Panel slots were measured** so trends don’t fight the P&ID.  
4. **External LLM + IDMP AI** polish the charts; **QA** catches dead panels / old dates / broken live window.  
5. **Demo data stream** keeps PV/SP and trends moving during the talk.

Reproduce that accuracy on another unit: bring the same **three files + live tags**, not a longer prompt.

---

## Related files

| File | Use |
|------|-----|
| `DEMO_SCRIPT.md` | Talk track + paste prompt |
| `houston-refinery-pivision-demo.zip` | Ready customer-shaped pack |
| `harness/FOLDER_SPEC.md` | Formal folder / CSV schema |
| `harness/QA_AGENT.md` | External LLM QA harness |
