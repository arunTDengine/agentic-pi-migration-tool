#!/usr/bin/env python3
"""Desert Peak Solar Farm — spacious, high-fidelity animated IDMP canvas."""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib import error, request

IDMP_URL = os.environ.get("IDMP_URL", "http://localhost:6842").rstrip("/")
IDMP_USER = os.environ.get("IDMP_USER", "")
IDMP_PASSWORD = os.environ.get("IDMP_PASSWORD", "")
IDMP_API_KEY = os.environ.get("IDMP_API_KEY", "")
DASHBOARD_NAME = "Desert Peak Solar Farm — Live Microgrid Board"

# Host dashboard on Solar Power so the story matches the P&ID
HOST = 2026697102008832  # Solar Power
PLANT = 2026697104384512  # Plant_4135001 (optional context)

INVERTERS = [
    {"id": 2026697105871360, "name": "INV-0102", "label": "Inverter Bay A"},
    {"id": 2026697106477568, "name": "INV-0103", "label": "Inverter Bay B"},
    {"id": 2026697107001856, "name": "INV-0104", "label": "Inverter Bay C"},
    {"id": 2026697107628544, "name": "INV-0105", "label": "Inverter Bay D"},
]

# Shared template attribute IDs (resolved per expressionElementId)
ATTR_AC = 2026697095094784
ATTR_DC = 2026697094705664
ATTR_YIELD = 2026697095361024
ATTR_TOTAL = 2026697095619072

CANVAS_W = 5200
CANVAS_H = 2800
REFRESH_MS = 5000
CHART_FROM = "now-6h"  # interesting movement on AC/DC
INV_PITCH = 780  # must exceed metric card width so columns never collide
INV_START = 180
INV_Y = 980
METRIC_W = 300
METRIC_H = 92
METRIC_GAP = 18

ASSETS = {
    "solar": "/static/png/IoT-power(电源)/Concentrated Solar plants 1（聚光太阳能发电厂）.svg",
    "solar2": "/static/png/IoT-power(电源)/Concentrated Solar plants 2（集中太阳能发电厂2）.svg",
    "inverter": "/static/png/IoT-power(电源)/AC drive交流传动).svg",
    "dc": "/static/png/IoT-power(电源)/DC power supply（直流电源）.svg",
    "transformer": "/static/png/IoT-power(电源)/Transformer（变压器）.svg",
    "breaker": "/static/png/IoT-power(电源)/Circuit breaker（断路器）.svg",
    "meter": "/static/png/IoT-power(电源)/Power monitor（电源监视器）.svg",
    "battery": "/static/png/IoT-power(电源)/Uninterruptable power supply（不间断电源）.svg",
    "tower": "/static/png/IoT-power(电源)/Transmission tower（输电塔）.svg",
    "substation": "/static/png/IoT-power(电源)/Simple substation（简易变电站）.svg",
    "wind": "/static/png/IoT-power(电源)/Industrial wind generators 2（工业风力发电机2）.svg",
    "panel": "/static/png/IoT-power(电源)/Simple power panel（简易电源板）.svg",
    "plant": "/static/png/IoT-power(电源)/Power plant（发电厂）.svg",
    "flame": "/static/png/废气处理/火焰（大）.gif",
}

C_DC = "rgb(49, 167, 245)"
C_AC = "rgb(48, 238, 111)"
C_GRID = "rgb(230, 217, 80)"
C_BATT = "rgb(168, 85, 247)"
C_ALERT = "rgb(255, 89, 89)"
C_TEXT = "#c5d0e0"
C_BG = "#121820"
C_PANEL = "#0f1520"


class Client:
    def __init__(self) -> None:
        self.headers = {"Content-Type": "application/json"}
        if IDMP_API_KEY:
            self.headers["Authorization"] = f"Bearer {IDMP_API_KEY}"
            self.call("GET", "/api/v1/elements/search?keyword=&limit=1")
        elif IDMP_USER and IDMP_PASSWORD:
            token = self.call(
                "POST",
                "/api/v1/users/login",
                {"login_name": IDMP_USER, "password": IDMP_PASSWORD},
                auth=False,
            )["token"]
            self.headers["Authorization"] = f"Bearer {token}"
        else:
            raise RuntimeError(
                "Set IDMP_API_KEY, or set both IDMP_USER and IDMP_PASSWORD."
            )

    def call(self, method: str, path: str, body: Any = None, *, auth: bool = True) -> Any:
        data = json.dumps(body).encode() if body is not None else None
        headers = self.headers if auth else {"Content-Type": "application/json"}
        req = request.Request(f"{IDMP_URL}{path}", data=data, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=120) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else {}
        except error.HTTPError as exc:
            raise RuntimeError(f"{method} {path} ({exc.code}): {exc.read().decode()[:500]}") from exc


def fmt(v: Any) -> str:
    if v is None:
        return "--"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


def raw_attr(host: int, name: str, alias: str, *, child: int | None = None) -> dict[str, Any]:
    if child and child != host:
        q = f"{child}|attributes['{name}']"
    else:
        q = f"attributes['{name}']"
    return {
        "uuid": str(uuid.uuid4()),
        "attributeExpression": q,
        "expression": f"${{{q}}}",
        "function": None,
        "parameters": None,
        "tsColumnType": "none",
        "groupBy": False,
        "limits": None,
        "forecast": None,
        "timeShift": None,
        "window": None,
        "alias": alias.replace(".", "_").replace(" ", "_"),
        "checked": True,
        "formula": False,
        "orderBy": None,
        "filter": None,
        "displayUom": None,
        "defaultUomClassId": None,
        "qualityColumn": None,
    }


def line_panel(name: str, title: str, host: int, series: list[tuple[str, str, int]]) -> dict[str, Any]:
    return {
        "name": name,
        "panelType": "line",
        "categories": [5],
        "params": {"fromText": CHART_FROM, "toText": "now"},
        "yaAttributes": [raw_attr(host, a, al, child=c) for a, al, c in series],
        "xaAttributes": [],
        "chart": {
            "graph": {"title": title},
            "legend": {"show": True, "placement": "bottom", "stats": ["last", "min", "max"], "showType": "list"},
            "series": {"graphMode": "area", "style": "smooth", "lineWidth": 2.5, "fillOpacity": 0.22},
            "standardOptions": {"decimals": 2},
        },
    }


def stat_panel(name: str, title: str, host: int, attr: str, alias: str, child: int, *, color: str = "#22c55e") -> dict[str, Any]:
    """Rounded live KPI — decimals enforced so canvas never shows raw floats."""
    return {
        "name": name,
        "panelType": "stat",
        "categories": [5],
        "params": {"fromText": "now-15m", "toText": "now"},
        "yaAttributes": [raw_attr(host, attr, alias, child=child)],
        "xaAttributes": [],
        "chart": {
            "graph": {"title": title},
            "legend": {"show": False},
            "series": {"textMode": "value_and_name", "graphMode": "none"},
            "standardOptions": {"decimals": 2, "color": color},
        },
    }


def text_panel(name: str, html: str) -> dict[str, Any]:
    return {"name": name, "panelType": "text", "textContent": html, "categories": [5]}


def inline(temp_id: int, panel: dict[str, Any]) -> dict[str, Any]:
    return {"tempId": temp_id, "panel": panel}


def panel_card(pid: str, x: float, y: float, w: float, h: float, panel_id: int, name: str) -> dict[str, Any]:
    return {
        "id": pid,
        "name": "lePanelCard",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "panelId": panel_id,
        "elementId": HOST,
        "panelName": name,
    }


def rect(pid: str, x: float, y: float, w: float, h: float, *, bg: str, color: str = "#334155", lw: float = 1) -> dict[str, Any]:
    return {
        "id": pid,
        "name": "rectangle",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "background": bg,
        "color": color,
        "lineWidth": lw,
        "text": "",
        "disableAnchor": True,
    }


def label(pid: str, x: float, y: float, w: float, h: float, text: str, *, size: float = 14, color: str = C_TEXT, weight: str = "normal", align: str = "center") -> dict[str, Any]:
    return {
        "id": pid,
        "name": "text",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "text": text,
        "color": color,
        "fontSize": size,
        "fontWeight": weight,
        "textAlign": align,
        "disableAnchor": True,
    }


def badge(pid: str, x: float, y: float, w: float, h: float, *, color: str) -> dict[str, Any]:
    bg = color.replace("rgb(", "rgba(").replace(")", ", 0.14)")
    return {
        "id": pid,
        "name": "square",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "color": color,
        "background": bg,
        "lineWidth": 1.5,
        "disableAnchor": True,
    }


def image(pid: str, x: float, y: float, w: float, h: float, src: str) -> dict[str, Any]:
    return {"id": pid, "name": "image", "x": x, "y": y, "width": w, "height": h, "image": src, "crossOrigin": "anonymous"}


def live_expr(
    pid: str,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    element_id: int,
    attr: str,
    seed: Any,
    size: float = 32,
    color: str = "#ffffff",
) -> dict[str, Any]:
    """Per-element Formula binding — works even when template attr IDs are shared."""
    return {
        "id": pid,
        "name": "text",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "text": fmt(seed),
        "color": color,
        "fontSize": size,
        "fontWeight": "bold",
        "textAlign": "center",
        "disableAnchor": True,
        "form": [
            {
                "key": "text",
                "name": "value",
                "type": "text",
                "expression": f"${{attributes['{attr}']}}",
                "dataReferenceType": "Formula",
                "expressionElementId": element_id,
            }
        ],
    }


def anim_h(
    pid: str,
    x: float,
    y: float,
    length: float,
    *,
    color: str,
    span: int = 2,
    reverse: bool = False,
    width: float = 7,
) -> dict[str, Any]:
    return {
        "id": pid,
        "name": "line",
        "type": 1,
        "lineName": "line",
        "x": x,
        "y": y,
        "width": length,
        "height": 0,
        "length": length,
        "lineWidth": width,
        "color": color,
        "anchors": [{"id": "0", "x": 0, "y": 0.5, "start": True}, {"id": "1", "x": 1, "y": 0.5}],
        "lineAnimateType": 1,
        "animateColor": "rgb(255, 255, 255)",
        "animateSpan": span,
        "keepAnimateState": True,
        "autoPlay": True,
        "animateReverse": reverse,
        "animateShadow": False,
        "lineAnimateImages": [],
    }


def anim_v(pid: str, x: float, y: float, length: float, *, color: str, span: int = 2, width: float = 6) -> dict[str, Any]:
    return {
        "id": pid,
        "name": "line",
        "type": 1,
        "lineName": "line",
        "x": x,
        "y": y,
        "width": 0,
        "height": length,
        "length": length,
        "lineWidth": width,
        "color": color,
        "anchors": [{"id": "0", "x": 0.5, "y": 0, "start": True}, {"id": "1", "x": 0.5, "y": 1}],
        "lineAnimateType": 1,
        "animateColor": "rgb(255, 255, 255)",
        "animateSpan": span,
        "keepAnimateState": True,
        "autoPlay": True,
        "animateReverse": False,
        "animateShadow": False,
        "lineAnimateImages": [],
    }


def arrow(pid: str, x: float, y: float, *, color: str, w: float = 56, h: float = 40) -> dict[str, Any]:
    return {
        "id": pid,
        "name": "rightArrow",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "color": color,
        "background": color.replace("rgb(", "rgba(").replace(")", ", 0.25)"),
        "disableAnchor": True,
    }


def fetch_seed(c: Client, element_id: int, attr_ids: list[int]) -> dict[int, Any]:
    rows = c.call("POST", f"/api/v1/elements/{element_id}/attributes/data", attr_ids) or []
    return {int(r["id"]): r.get("value") for r in rows}


def header_html(total_ac: float, total_dc: float) -> str:
    now = datetime.now().strftime("%A, %B %d, %Y · %H:%M:%S")
    return f"""<div style='height:100%;box-sizing:border-box;padding:22px 36px;background:linear-gradient(115deg,#0b1220 0%,#152033 45%,#0f1a14 100%);border:1px solid #334155;border-radius:16px;color:#f8fafc;display:flex;align-items:center;gap:28px'>
<div style='width:72px;height:72px;border-radius:18px;background:linear-gradient(145deg,#0ea5e9,#22c55e);display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:900;color:#041016;letter-spacing:1px;box-shadow:0 0 28px rgba(34,197,94,.35)'>TD</div>
<div style='flex:1'>
<div style='font-size:12px;letter-spacing:3.2px;text-transform:uppercase;color:#38bdf8;font-weight:700'>TDengine IDMP · Renewable Operations</div>
<div style='font-size:34px;font-weight:800;margin-top:6px;letter-spacing:-0.4px'>Desert Peak Solar Farm — Live Microgrid Board</div>
<div style='font-size:15px;color:#94a3b8;margin-top:8px'>PV arrays → DC combiners → inverter bays → transformer → grid export · raw tags · 6h trends</div>
</div>
<div style='display:flex;gap:18px;margin-right:18px'>
<div style='background:rgba(49,167,245,.12);border:1px solid rgba(49,167,245,.35);border-radius:12px;padding:12px 18px;min-width:120px;text-align:center'>
<div style='font-size:11px;color:#7dd3fc;letter-spacing:1px'>Σ DC kW</div>
<div style='font-size:26px;font-weight:800;color:#fff;margin-top:4px'>{total_dc:.1f}</div></div>
<div style='background:rgba(48,238,111,.12);border:1px solid rgba(48,238,111,.35);border-radius:12px;padding:12px 18px;min-width:120px;text-align:center'>
<div style='font-size:11px;color:#86efac;letter-spacing:1px'>Σ AC kW</div>
<div style='font-size:26px;font-weight:800;color:#fff;margin-top:4px'>{total_ac:.1f}</div></div>
</div>
<div style='text-align:right;min-width:220px'>
<div style='font-size:14px;color:#e2e8f0'>{now}</div>
<div style='margin-top:10px;display:flex;align-items:center;justify-content:flex-end;gap:10px'>
<span style='width:12px;height:12px;border-radius:50%;background:#22c55e;box-shadow:0 0 14px #22c55e;display:inline-block'></span>
<span style='color:#22c55e;font-weight:800'>FARM ONLINE</span></div>
<div style='margin-top:6px;font-size:12px;color:#64748b'>{REFRESH_MS // 1000}s refresh · 4 inverter bays</div>
</div></div>"""


def insight_html(seeds: dict[int, dict[int, Any]]) -> str:
    cards = []
    for inv in INVERTERS:
        ac = seeds[inv["id"]].get(ATTR_AC)
        dc = seeds[inv["id"]].get(ATTR_DC)
        yld = seeds[inv["id"]].get(ATTR_YIELD)
        eff = (ac / dc * 100) if isinstance(ac, (int, float)) and isinstance(dc, (int, float)) and dc > 0.05 else None
        color = "#22c55e" if (ac or 0) > 3 else "#38bdf8"
        eff_s = f"{eff:.0f}%" if eff is not None else "—"
        cards.append(
            f"<div style='padding:14px 16px;background:#0b1220;border:1px solid #1e293b;border-left:4px solid {color};border-radius:12px'>"
            f"<div style='font-size:13px;color:#38bdf8;font-weight:800;letter-spacing:.5px'>{inv['name']} · {inv['label']}</div>"
            f"<div style='display:flex;gap:18px;margin-top:10px;flex-wrap:wrap'>"
            f"<div><div style='font-size:11px;color:#64748b'>AC</div><div style='font-size:20px;font-weight:800;color:#fff'>{fmt(ac)}</div></div>"
            f"<div><div style='font-size:11px;color:#64748b'>DC</div><div style='font-size:20px;font-weight:800;color:#fff'>{fmt(dc)}</div></div>"
            f"<div><div style='font-size:11px;color:#64748b'>Yield</div><div style='font-size:20px;font-weight:800;color:#fff'>{fmt(yld)}</div></div>"
            f"<div><div style='font-size:11px;color:#64748b'>η</div><div style='font-size:20px;font-weight:800;color:#fff'>{eff_s}</div></div>"
            f"</div></div>"
        )
    grid = "".join(cards)
    return (
        "<div style='height:100%;box-sizing:border-box;padding:16px 18px;background:#0f1520;border:1px solid #334155;border-radius:14px'>"
        "<div style='font-size:15px;font-weight:800;color:#38bdf8;margin-bottom:12px'>✦ Fleet Insights · Live</div>"
        f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:12px'>{grid}</div></div>"
    )


def legend_html() -> str:
    items = [(C_DC, "DC collection"), (C_AC, "AC generation"), (C_GRID, "Grid export"), (C_BATT, "Storage / UPS"), (C_ALERT, "Protection")]
    chips = "".join(
        f"<div style='display:flex;align-items:center;gap:12px;margin:10px 0'>"
        f"<span style='width:44px;height:7px;border-radius:4px;background:{c};box-shadow:0 0 10px {c}'></span>"
        f"<span style='color:#cbd5e1;font-size:14px'>{lab}</span></div>"
        for c, lab in items
    )
    return (
        "<div style='height:100%;box-sizing:border-box;padding:18px;background:#0f1520;border:1px solid #334155;border-radius:14px'>"
        "<div style='font-size:14px;font-weight:800;color:#38bdf8;letter-spacing:1px;margin-bottom:8px'>ENERGY PATHS</div>"
        + chips
        + "<div style='margin-top:16px;font-size:13px;color:#64748b;line-height:1.55'>Animated dashes = live power flow. Bay KPIs use rounded stat panels (2 decimals).</div></div>"
    )


def build_scene(seeds: dict[int, dict[int, Any]]) -> list[dict[str, Any]]:
    pens: list[dict[str, Any]] = []
    pens.append(rect("bg", 0, 0, CANVAS_W, CANVAS_H, bg=C_BG, color=C_BG, lw=0))

    # SLD frame — taller so stacked KPIs breathe
    pens.append(rect("hero-frame", 60, 240, CANVAS_W - 120, 1480, bg=C_PANEL, color="#1e3a5f", lw=1.5))
    pens.append(label("hero-title", 100, 265, 1400, 40, "SINGLE-LINE DIAGRAM · DESERT PEAK 40 MW", size=28, color="#ffffff", weight="bold", align="left"))
    pens.append(
        label(
            "hero-sub",
            100,
            310,
            1800,
            28,
            "Field arrays  →  DC combiners  →  Inverter bays  →  Step-up transformer  →  Grid interconnect",
            size=15,
            color="#94a3b8",
            align="left",
        )
    )

    # PV arrays aligned above inverter columns
    for i in range(4):
        x = INV_START + i * INV_PITCH + 40
        src = ASSETS["solar"] if i % 2 == 0 else ASSETS["solar2"]
        pens.append(image(f"pv-{i}", x, 380, 240, 170, src))
        pens.append(label(f"pv-l-{i}", x, 560, 240, 28, f"PV Array {chr(65 + i)}", size=17, color="#e2e8f0", weight="bold"))
        pens.append(label(f"pv-s-{i}", x, 590, 240, 22, "String field", size=12, color="#64748b"))
        pens.append(anim_v(f"pv-drop-{i}", x + 120, 615, 110, color=C_DC, span=2))

    # Wind to the right of array D
    wind_x = INV_START + 4 * INV_PITCH - 40
    pens.append(image("wind-1", wind_x, 360, 150, 190, ASSETS["wind"]))
    pens.append(label("wind-l", wind_x - 20, 560, 190, 28, "Wind Assist", size=15, color="#e2e8f0", weight="bold"))
    pens.append(anim_v("wind-drop", wind_x + 75, 615, 110, color=C_BATT, span=3))

    # DC bus across all arrays
    dc_bus_w = INV_START + 3 * INV_PITCH + 300 - 140
    pens.append(anim_h("dc-bus", 140, 740, dc_bus_w, color=C_DC, span=2, width=8))
    pens.append(label("dc-bus-l", 140, 758, 300, 24, "DC COLLECTOR BUS", size=13, color=C_DC, weight="bold", align="left"))

    # Combiner centered under arrays B/C
    comb_x = INV_START + 1.5 * INV_PITCH
    pens.append(image("combiner", comb_x, 800, 140, 120, ASSETS["dc"]))
    pens.append(label("combiner-l", comb_x - 30, 930, 200, 24, "DC Combiner", size=15, color="#e2e8f0", weight="bold"))
    pens.append(anim_v("comb-up", comb_x + 70, 740, 60, color=C_DC, span=1))
    pens.append(anim_v("comb-down", comb_x + 70, 920, 50, color=C_DC, span=2))

    # Inverter bays — wide pitch; KPI cards placed via panel_card (not raw floats)
    for i, inv in enumerate(INVERTERS):
        x = INV_START + i * INV_PITCH
        pens.append(image(f"inv-img-{i}", x + 70, INV_Y, 180, 150, ASSETS["inverter"]))
        pens.append(label(f"inv-name-{i}", x, INV_Y + 160, METRIC_W + 40, 30, inv["name"], size=20, color="#ffffff", weight="bold"))
        pens.append(label(f"inv-lab-{i}", x, INV_Y + 192, METRIC_W + 40, 24, inv["label"], size=14, color="#94a3b8"))
        pens.append(anim_v(f"inv-dc-{i}", x + 160, 970, 10, color=C_DC, span=2))
        pens.append(arrow(f"inv-arr-{i}", x + 260, INV_Y + 55, color=C_AC, w=52, h=36))
        # AC riser from below stacked KPIs
        kpi_bottom = INV_Y + 230 + 3 * (METRIC_H + METRIC_GAP)
        pens.append(anim_v(f"ac-rise-{i}", x + 160, kpi_bottom, 40, color=C_AC, span=2))

    ac_y = INV_Y + 230 + 3 * (METRIC_H + METRIC_GAP) + 50
    ac_w = INV_START + 3 * INV_PITCH + 200 - 160
    pens.append(anim_h("ac-bus", 160, ac_y, ac_w, color=C_AC, span=2, width=8))
    pens.append(label("ac-bus-l", 160, ac_y + 16, 280, 24, "AC COLLECTION BUS", size=13, color=C_AC, weight="bold", align="left"))

    # Grid train to the right with breathing room
    train_x = INV_START + 4 * INV_PITCH + 40
    pens.append(anim_h("to-meter", 160 + ac_w, ac_y, train_x - (160 + ac_w) + 40, color=C_AC, span=2))
    pens.append(image("meter", train_x, ac_y - 90, 130, 130, ASSETS["meter"]))
    pens.append(label("meter-l", train_x - 20, ac_y + 50, 180, 24, "Revenue Meter", size=14, color="#e2e8f0", weight="bold"))

    pens.append(anim_h("to-xfmr", train_x + 130, ac_y, 160, color=C_GRID, span=2))
    pens.append(image("xfmr", train_x + 300, ac_y - 110, 160, 170, ASSETS["transformer"]))
    pens.append(label("xfmr-l", train_x + 270, ac_y + 70, 220, 24, "Step-Up XFMR", size=15, color="#e2e8f0", weight="bold"))
    pens.append(label("xfmr-s", train_x + 270, ac_y + 96, 220, 20, "34.5 → 230 kV", size=12, color="#64748b"))

    pens.append(anim_h("to-brk", train_x + 460, ac_y, 150, color=C_ALERT, span=3))
    pens.append(image("brk", train_x + 620, ac_y - 80, 120, 120, ASSETS["breaker"]))
    pens.append(label("brk-l", train_x + 590, ac_y + 50, 180, 24, "Grid Breaker", size=14, color="#e2e8f0", weight="bold"))

    pens.append(anim_h("to-grid", train_x + 740, ac_y, 200, color=C_GRID, span=2))
    pens.append(image("tower", train_x + 960, ac_y - 160, 170, 230, ASSETS["tower"]))
    pens.append(label("tower-l", train_x + 930, ac_y + 80, 230, 28, "GRID EXPORT", size=16, color=C_GRID, weight="bold"))
    pens.append(label("tower-s", train_x + 930, ac_y + 110, 230, 20, "230 kV interconnect", size=12, color="#64748b"))

    # BESS / switchyard above grid train
    pens.append(image("batt", train_x, 780, 150, 130, ASSETS["battery"]))
    pens.append(label("batt-l", train_x - 20, 920, 200, 24, "BESS / UPS", size=15, color="#e2e8f0", weight="bold"))
    pens.append(anim_v("batt-v", train_x + 75, 910, ac_y - 910, color=C_BATT, span=2, width=5))

    pens.append(image("sub", train_x + 400, 780, 170, 150, ASSETS["substation"]))
    pens.append(label("sub-l", train_x + 380, 940, 220, 24, "Switchyard", size=15, color="#e2e8f0", weight="bold"))
    pens.append(anim_v("sub-drop", train_x + 485, 930, ac_y - 930, color=C_ALERT, span=2))

    # SCADA / O&M
    pens.append(image("ctrl", train_x + 750, 360, 150, 130, ASSETS["panel"]))
    pens.append(label("ctrl-l", train_x + 720, 500, 210, 24, "SCADA Node", size=14, color="#e2e8f0", weight="bold"))
    pens.append(image("plant", train_x + 980, 360, 170, 140, ASSETS["plant"]))
    pens.append(label("plant-l", train_x + 960, 510, 210, 24, "O&M Center", size=14, color="#e2e8f0", weight="bold"))

    # Fleet rollup (formatted static summary — live bay KPIs are panels)
    total_ac = sum(float(seeds[i["id"]].get(ATTR_AC) or 0) for i in INVERTERS)
    total_dc = sum(float(seeds[i["id"]].get(ATTR_DC) or 0) for i in INVERTERS)
    total_y = sum(float(seeds[i["id"]].get(ATTR_YIELD) or 0) for i in INVERTERS)
    pens.append(badge("fleet-bg", train_x, 360, 360, 180, color=C_AC))
    pens.append(label("fleet-t", train_x + 16, 375, 330, 26, "FLEET ROLLUP", size=15, color="#86efac", weight="bold", align="left"))
    pens.append(label("fleet-ac", train_x + 16, 415, 110, 40, f"{total_ac:.1f}", size=32, color="#ffffff", weight="bold", align="left"))
    pens.append(label("fleet-ac-u", train_x + 16, 455, 110, 20, "Σ AC kW", size=12, color="#94a3b8", align="left"))
    pens.append(label("fleet-dc", train_x + 130, 415, 110, 40, f"{total_dc:.1f}", size=32, color="#ffffff", weight="bold", align="left"))
    pens.append(label("fleet-dc-u", train_x + 130, 455, 110, 20, "Σ DC kW", size=12, color="#94a3b8", align="left"))
    pens.append(label("fleet-y", train_x + 244, 415, 100, 40, f"{total_y:.1f}", size=32, color="#ffffff", weight="bold", align="left"))
    pens.append(label("fleet-y-u", train_x + 244, 455, 100, 20, "Σ Yield", size=12, color="#94a3b8", align="left"))
    pens.append(label("fleet-n", train_x + 16, 500, 330, 24, "4 inverter bays · raw tags", size=12, color="#64748b", align="left"))

    pens.append(
        label(
            "footer",
            CANVAS_W - 680,
            CANVAS_H - 40,
            640,
            24,
            "TDengine IDMP · Desert Peak Solar · Animated meta2d Canvas",
            size=13,
            color="#475569",
            align="right",
        )
    )
    return pens


def build_panels() -> tuple[dict[str, int], list[dict[str, Any]]]:
    tid: dict[str, int] = {"header": -2, "legend": -3, "ai": -4}
    inlines = [
        inline(tid["header"], text_panel("Header", "<div>loading</div>")),
        inline(tid["legend"], text_panel("Legend", legend_html())),
        inline(tid["ai"], text_panel("Insights", "<div>loading</div>")),
    ]
    # Per-bay rounded KPI stats (no raw float dumps)
    for i, inv in enumerate(INVERTERS):
        tid[f"ac{i}"] = -10 - i
        tid[f"dc{i}"] = -20 - i
        tid[f"yd{i}"] = -40 - i
        tid[f"t{i}"] = -30 - i
        inlines.append(
            inline(
                tid[f"ac{i}"],
                stat_panel(f"{inv['name']} AC", "AC Output kW", HOST, "AC power", f"AC_{inv['name']}", inv["id"], color="#22c55e"),
            )
        )
        inlines.append(
            inline(
                tid[f"dc{i}"],
                stat_panel(f"{inv['name']} DC", "DC Input kW", HOST, "DC power", f"DC_{inv['name']}", inv["id"], color="#38bdf8"),
            )
        )
        inlines.append(
            inline(
                tid[f"yd{i}"],
                stat_panel(f"{inv['name']} Yield", "Daily Yield", HOST, "Daily yield", f"Y_{inv['name']}", inv["id"], color="#eab308"),
            )
        )
        inlines.append(
            inline(
                tid[f"t{i}"],
                line_panel(
                    f"{inv['name']} Power",
                    f"{inv['name']} · AC / DC / Yield · 6h raw",
                    HOST,
                    [
                        ("AC power", f"AC_{inv['name']}", inv["id"]),
                        ("DC power", f"DC_{inv['name']}", inv["id"]),
                        ("Daily yield", f"Y_{inv['name']}", inv["id"]),
                    ],
                ),
            )
        )
    return tid, inlines


def place_cards(panel_map: dict[int, int]) -> list[dict[str, Any]]:
    p = panel_map
    cards = [
        panel_card("header", 60, 40, CANVAS_W - 120, 170, p[-2], "Header"),
        panel_card("legend", 60, 2380, 780, 340, p[-3], "Legend"),
        panel_card("ai", 900, 2380, CANVAS_W - 960, 340, p[-4], "Insights"),
    ]
    # Stacked KPI column under each inverter — never overlaps neighboring bay
    for i, inv in enumerate(INVERTERS):
        x = INV_START + i * INV_PITCH
        y0 = INV_Y + 230
        cards.append(panel_card(f"ac{i}", x, y0, METRIC_W, METRIC_H, p[-10 - i], f"{inv['name']} AC"))
        cards.append(panel_card(f"dc{i}", x, y0 + METRIC_H + METRIC_GAP, METRIC_W, METRIC_H, p[-20 - i], f"{inv['name']} DC"))
        cards.append(panel_card(f"yd{i}", x, y0 + 2 * (METRIC_H + METRIC_GAP), METRIC_W, METRIC_H, p[-40 - i], f"{inv['name']} Yield"))

    # Trends with wide gaps
    trend_w = 1180
    gap = 100
    start = 60
    trend_y = 1980
    for i, inv in enumerate(INVERTERS):
        x = start + i * (trend_w + gap)
        cards.append(panel_card(f"t{i}", x, trend_y, trend_w, 360, p[-30 - i], f"{inv['name']} Power"))
    return cards

def chart_payload(pens: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "x": 0,
        "y": 0,
        "scale": 1,
        "pens": pens,
        "width": CANVAS_W,
        "height": CANVAS_H,
        "background": C_BG,
        "color": C_TEXT,
        "theme": "dark",
        "grid": False,
        "lineWidth": 7,
        "lineCross": True,
        "networkInterval": 5,
        "locked": 0,
        "version": "1.1.19",
    }


def purge(c: Client) -> None:
    """Delete only an earlier copy of this example and its embedded panels."""
    dashboards = c.call("GET", f"/api/v1/elements/{HOST}/dashboards") or []
    for summary in dashboards:
        if summary.get("name") != DASHBOARD_NAME:
            continue

        dashboard_id = int(summary["id"])
        dashboard = c.call(
            "GET", f"/api/v1/elements/{HOST}/dashboards/{dashboard_id}"
        )
        panel_ids = {
            int(item["panelId"])
            for item in dashboard.get("panels") or []
            if item.get("panelId") is not None
        }
        panel_ids.update(
            int(pen["panelId"])
            for pen in (dashboard.get("chart") or {}).get("pens") or []
            if pen.get("name") == "lePanelCard" and pen.get("panelId") is not None
        )

        c.call(
            "DELETE", f"/api/v1/elements/{HOST}/dashboards/{dashboard_id}"
        )
        for panel_id in panel_ids:
            try:
                c.call(
                    "DELETE", f"/api/v1/elements/{HOST}/panels/{panel_id}"
                )
            except RuntimeError:
                pass


def verify(c: Client, panel_ids: list[int], seeds: dict[int, dict[int, Any]]) -> dict[str, Any]:
    report: dict[str, Any] = {"panels_live": [], "panels_fail": [], "expr_ok": []}
    for pid in panel_ids:
        panel = c.call("GET", f"/api/v1/elements/{HOST}/panels/{pid}")
        if panel.get("panelType") == "text":
            continue
        body = dict(panel)
        body["params"] = {"fromText": CHART_FROM, "toText": "now"}
        try:
            result = c.call("POST", f"/api/v1/elements/{HOST}/panels/query", body)
            rows = result[0]["data"] if result else []
            if rows:
                report["panels_live"].append({"name": panel["name"], "points": len(rows), "last": rows[-1]})
            else:
                report["panels_fail"].append(panel["name"])
        except RuntimeError as exc:
            report["panels_fail"].append(f"{panel['name']}: {exc}")

    for inv in INVERTERS:
        body = {"expression": "${attributes['AC power']}", "dataReferenceType": "Formula"}
        val = c.call("POST", f"/api/v1/elements/{inv['id']}/attributes/evaluate-expression", body)
        report["expr_ok"].append({"inv": inv["name"], "ac": val.get("value"), "seed": seeds[inv["id"]].get(ATTR_AC)})
    return report


def main() -> None:
    c = Client()
    print("Building Desert Peak Solar Farm canvas (spacious + high fidelity)…")
    purge(c)

    seeds: dict[int, dict[int, Any]] = {}
    for inv in INVERTERS:
        seeds[inv["id"]] = fetch_seed(c, inv["id"], [ATTR_AC, ATTR_DC, ATTR_YIELD, ATTR_TOTAL])
        print(f"  {inv['name']}: AC={fmt(seeds[inv['id']].get(ATTR_AC))} DC={fmt(seeds[inv['id']].get(ATTR_DC))} Y={fmt(seeds[inv['id']].get(ATTR_YIELD))}")

    total_ac = sum(float(seeds[i["id"]].get(ATTR_AC) or 0) for i in INVERTERS)
    total_dc = sum(float(seeds[i["id"]].get(ATTR_DC) or 0) for i in INVERTERS)

    tid, inlines = build_panels()
    # inject live header/insights html
    for item in inlines:
        if item["tempId"] == -2:
            item["panel"] = text_panel("Header", header_html(total_ac, total_dc))
        if item["tempId"] == -4:
            item["panel"] = text_panel("Insights", insight_html(seeds))

    scene = build_scene(seeds)
    create_body = {
        "name": DASHBOARD_NAME,
        "description": "High-fidelity animated solar microgrid canvas — PV→inverter→grid with live Formula tag bindings and 6h fleet trends.",
        "type": "CANVAS",
        "params": {"refreshInterval": REFRESH_MS, "fromText": CHART_FROM, "toText": "now"},
        "chart": chart_payload(scene),
        "newInlinePanels": inlines,
        "panels": [],
    }
    result = c.call("POST", f"/api/v1/elements/{HOST}/dashboards", create_body)
    did = int(result["id"])
    panel_map = {int(k): int(v) for k, v in (result.get("panelIdMap") or {}).items()}

    all_pens = scene + place_cards(panel_map)
    c.call(
        "PUT",
        f"/api/v1/elements/{HOST}/dashboards/{did}",
        {
            "name": create_body["name"],
            "description": create_body["description"],
            "type": "CANVAS",
            "params": create_body["params"],
            "chart": chart_payload(all_pens),
            "panels": [],
        },
    )

    check = verify(c, list(panel_map.values()), seeds)
    view = f"{IDMP_URL}/explorer/dashboard?id={did}"
    edit = f"{IDMP_URL}/explorer/canvas-dashboard-create/{did}"
    report = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "dashboard_id": did,
        "element_id": HOST,
        "scenario": "Desert Peak Solar Farm",
        "view_url": view,
        "edit_url": edit,
        "canvas": f"{CANVAS_W}x{CANVAS_H}",
        "pens": len(all_pens),
        "verify": check,
    }
    path = os.path.join(os.path.dirname(__file__), "reports/plant-operations-canvas.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    print(f"\nReady — Solar Microgrid Board")
    print(f"  View: {view}")
    print(f"  Edit: {edit}")
    print(f"  Pens: {len(all_pens)} · Charts live: {len(check['panels_live'])} · Expr OK: {len(check['expr_ok'])}")
    if check["panels_fail"]:
        print("  Chart issues:", check["panels_fail"])
    print(f"  Report: {path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
