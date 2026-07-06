# Customer Folder Specification

## Structure

One subfolder per PI Vision display:

```
acme-migration/
├── ops-overview/
│   ├── screenshot.png
│   ├── tags.csv
│   └── display.json
└── p101-pump/
    ├── screenshot.png
    ├── tags.csv
    └── display.json
```

Single-display flat folder is also supported (tags at root).

## tags.csv

Required columns (header row):

| Column | Required | Description |
|--------|----------|-------------|
| panel_key | yes | Unique key for layout |
| title | yes | Professional SCADA panel title |
| type | yes | trend, gauge, kpi, bar, pie, scatter, bar-gauge, state |
| element_id | yes* | IDMP element ID (*or set in display.json) |
| pi_tags | yes | PI tags, pipe-separated: `tag1\|tag2` |
| prompt | no | AI panel prompt override |

Example:

```csv
panel_key,title,type,element_id,pi_tags,prompt
vibration,Vibration Severity Index,gauge,2023515242121480,vibration_mm_s,gauge with alarm at 6 mm/s
trend,Hydraulic Performance Trend,trend,2023515242121480,suction_pressure_psi|discharge_pressure_psi,line chart last 15 minutes
```

## display.json

```json
{
  "name": "P-101 Mechanical Performance Monitor",
  "element_id": 2023515242121480,
  "dashboard_id": null,
  "theme": "rotating",
  "refresh_seconds": 15,
  "description": "Optional description"
}
```

Themes: `control-room`, `rotating`, `process`

## screenshot.png

- Formats: PNG, JPG, WEBP, GIF
- Used as `reference_screenshot` in generated scenario
- Agent should open and compare layout to PI Vision before migrate
