# Extended Agent Context

## Architecture

```
Customer PI Vision assets          TDengine IDMP (running)
        │                                    │
        ├─ screenshot.png (reference)      ├─ elements / attributes
        └─ tags.csv (authoritative)        └─ TDengine data
                    │                              │
                    └──── ingest-folder ───────────┘
                              │
                              ▼
                        scenario.json
                              │
                              ▼
                     AgenticPiMigrator
                     (AI panels + layout)
                              │
                              ▼
                      Live dashboards
```

## Tag mapping examples (Summit Creek oil)

| PI / historian tag | IDMP element | Attribute |
|--------------------|--------------|-----------|
| `...EAGLE_FORD_A.P101.vibration_mm_s` | SCE-AST-EFA-P101 | vibration_mm_s |
| `...EAGLE_FORD_A.WH101.oil_flow_bpd` | SCE-AST-EFA-WH101 | oil_flow_bpd |
| Fleet total oil | SCE-AST-EFA-STATION | total_oil_production_bpd |

Discover element IDs:

```bash
./run.sh validate --keyword SCE
```

## Panel defaults applied by migrator

- `params.fromText`: `now-15m`
- `params.toText`: `now`
- Window interval: `30s` for time-series panels
- Dashboard refresh: 15 seconds
- Legend placement: bottom

## Layout guidelines (24-column grid)

| Row purpose | Typical layout |
|-------------|----------------|
| Header | col=0, w=24, h=2 |
| KPI row (3) | 8+8+8 |
| Main trend | 16 + side panel 8 |
| Bottom pair | 12+12 |

Avoid left-half stacking (w=12 only) with empty right side.

## Agent refinement checklist (when screenshots present)

- [ ] Open each `reference_screenshot` in scenario JSON
- [ ] Match panel titles to PI Vision display names
- [ ] Ensure chart type diversity (not all line/bar)
- [ ] Remove tables unless user requests
- [ ] Confirm element_id per panel matches tag owner equipment
- [ ] Run migrate, then verify URLs in report

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Empty charts | Start data simulator; verify tag → attribute mapping |
| Login failed | Check IDMP_USER / IDMP_PASSWORD |
| Panel 400 on save | Duplicate panel name — use unique internal names |
| Wrong layout | Edit `layout` in scenario JSON or display.json |
