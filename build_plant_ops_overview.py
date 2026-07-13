#!/usr/bin/env python3
"""Build Plant Operations Overview dashboard on IDMP Canvas via REST API."""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib import error, request

IDMP_URL = os.environ.get("IDMP_URL", "http://localhost:6842").rstrip("/")
IDMP_USER = os.environ["IDMP_USER"]
IDMP_PASSWORD = os.environ["IDMP_PASSWORD"]

# GTU Reactors — process manufacturing element
ROOT = 2026702359773696
INV_PUMP = 2026697105871360  # Inverter 0102 — power / energy proxy
INV_MOTOR = 2026697106477568  # Inverter 0103
INV_COMP = 2026697107001856  # Inverter 0104
INV_BOILER = 2026697107628544  # Inverter 0105

THEME = {
    "backgroundColor": "rgba(18, 18, 22, 0.98)",
    "showGridLines": False,
    "backgroundEffect": "none",
    "panelBorderStyle": "solid",
    "panelBorderRadius": 12,
    "panelRowMap": {},
}


class Client:
    def __init__(self) -> None:
        self.headers = {"Content-Type": "application/json"}
        token = self.call(
            "POST",
            "/api/v1/users/login",
            {"login_name": IDMP_USER, "password": IDMP_PASSWORD},
            auth=False,
        )["token"]
        self.headers["Authorization"] = f"Bearer {token}"

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


def attr(host: int, name: str, alias: str, *, child: int | None = None) -> dict[str, Any]:
    if child and child != host:
        q = f"{child}|attributes['{name}']"
    else:
        q = f"attributes['{name}']"
    safe = alias.replace(".", "_").replace(" ", "_")
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
        "alias": safe,
        "checked": True,
        "formula": False,
        "orderBy": None,
        "filter": None,
        "displayUom": None,
        "defaultUomClassId": None,
        "qualityColumn": None,
    }


def interval_window(minutes: str = "5m") -> dict[str, Any]:
    return {
        "windowType": "Interval",
        "timeColumn": "_wstart",
        "timeOffset": None,
        "eventTemplateId": None,
        "eventTemplateAttrExprs": None,
        "interval": minutes,
        "sliding": minutes,
        "fillType": "NONE",
        "fillValues": None,
    }


def chart_panel(
    c: Client,
    host: int,
    name: str,
    ptype: str,
    ya: list[dict[str, Any]],
    *,
    xa: list[dict[str, Any]] | None = None,
    time_from: str = "now-15m",
    time_to: str = "now",
    chart: dict[str, Any] | None = None,
) -> dict[str, int]:
    body: dict[str, Any] = {
        "name": name,
        "panelType": ptype,
        "categories": [5],
        "chart": chart
        or {
            "graph": {"title": name},
            "legend": {"show": True, "placement": "bottom", "showType": "list", "stats": ["last"]},
            "series": {"graphMode": "area" if ptype in ("line", "stat") else "line", "style": "smooth"},
            "standardOptions": {"decimals": 1},
        },
        "yaAttributes": ya,
        "xaAttributes": xa or [],
        "params": {"fromText": time_from, "toText": time_to},
    }
    pid = int(c.call("POST", f"/api/v1/elements/{host}/panels", body)["id"])
    return {"panelId": pid, "elementId": host}


def text_panel(c: Client, host: int, name: str, html: str) -> dict[str, int]:
    pid = int(
        c.call(
            "POST",
            f"/api/v1/elements/{host}/panels",
            {"name": name, "panelType": "text", "textContent": html, "categories": [5]},
        )["id"]
    )
    return {"panelId": pid, "elementId": host}


def cell(p: dict[str, int], col: int, row: int, w: int, h: int) -> dict[str, Any]:
    return {"panelId": p["panelId"], "elementId": p["elementId"], "column": col, "row": row, "width": w, "height": h}


def nav_html() -> str:
    items = [
        ("Overview", True),
        ("Production", False),
        ("Utilities", False),
        ("Maintenance", False),
        ("Quality", False),
        ("Energy", False),
        ("Reports", False),
        ("Settings", False),
    ]
    rows = []
    for label, active in items:
        bg = "#599CE7" if active else "transparent"
        fg = "#191c22" if active else "#94a3b8"
        weight = "600" if active else "400"
        rows.append(
            f"<div style='padding:10px 8px;margin:2px 0;border-radius:6px;"
            f"background:{bg};color:{fg};font-size:12px;font-weight:{weight};"
            f"letter-spacing:0.3px'>{label}</div>"
        )
    return (
        "<div style='height:100%;background:#141414;padding:12px 8px;"
        "border-right:1px solid #2a2a2e;color:#e4e4e4'>"
        "<div style='font-size:10px;letter-spacing:1.5px;text-transform:uppercase;"
        "color:#599CE7;margin-bottom:16px;padding:0 4px'>Navigation</div>"
        + "".join(rows)
        + "</div>"
    )


def header_html() -> str:
    now = datetime.now().strftime("%A, %B %d, %Y  %H:%M:%S")
    return f"""<div style='padding:12px 18px;background:#1a1a1f;border:1px solid #2a2a2e;
border-radius:10px;color:#e4e4e4;display:flex;align-items:center;gap:16px'>
<div style='width:44px;height:44px;border-radius:8px;background:#252530;border:1px solid #3a3a42;
display:flex;align-items:center;justify-content:center;font-size:10px;color:#599CE7;font-weight:600'>LOGO</div>
<div style='flex:1'>
<div style='font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#94a3b8'>
Real-Time Manufacturing Performance</div>
<div style='font-size:22px;font-weight:600;margin-top:2px;color:#f3f4f6'>Plant Operations Overview</div>
</div>
<div style='text-align:right;font-size:12px;color:#94a3b8'>
<div>{now}</div>
<div style='margin-top:6px'><span style='display:inline-block;width:8px;height:8px;
border-radius:50%;background:#22c55e;margin-right:6px'></span>
<span style='color:#22c55e;font-weight:600'>Plant Online</span></div>
<div style='margin-top:4px;font-size:11px'>Last update: live · 15s refresh</div>
</div></div>"""


def plant_layout_html() -> str:
    equip = [
        ("Tank T-101", "72%", "142 m³", "healthy"),
        ("Pump P-102", "Run", "142 L/min", "warning"),
        ("Heat Exch. HX-201", "Auto", "74.6 °C", "healthy"),
        ("Conveyor CV-01", "Run", "14,250 u/d", "healthy"),
        ("Motor M-301", "Run", "41.5 A", "healthy"),
        ("Valve V-405", "Open", "68%", "healthy"),
        ("Boiler B-501", "Fire", "8.3 bar", "warning"),
    ]
    colors = {"healthy": "#22c55e", "warning": "#eab308", "critical": "#ef4444"}
    boxes = []
    for i, (name, status, value, health) in enumerate(equip):
        col = i % 3
        row = i // 3
        x = 20 + col * 95
        y = 20 + row * 72
        hc = colors[health]
        boxes.append(
            f"""<g transform='translate({x},{y})'>
<rect width='82' height='58' rx='6' fill='#1e1e24' stroke='#3a3a42' stroke-width='1'/>
<circle cx='72' cy='10' r='4' fill='{hc}'/>
<text x='8' y='18' fill='#e4e4e4' font-size='9' font-weight='600'>{name}</text>
<text x='8' y='32' fill='#94a3b8' font-size='8'>{status}</text>
<text x='8' y='46' fill='#599CE7' font-size='9' font-weight='600'>{value}</text>
</g>"""
        )
    arrows = """
<defs><marker id='arr' markerWidth='6' markerHeight='6' refX='5' refY='3' orient='auto'>
<polygon points='0 0, 6 3, 0 6' fill='#599CE7' opacity='0.7'/></marker></defs>
<line x1='102' y1='49' x2='115' y2='49' stroke='#599CE7' stroke-width='1.5' marker-end='url(#arr)' opacity='0.6'/>
<line x1='197' y1='49' x2='210' y2='49' stroke='#599CE7' stroke-width='1.5' marker-end='url(#arr)' opacity='0.6'/>
<line x1='102' y1='121' x2='115' y2='121' stroke='#599CE7' stroke-width='1.5' marker-end='url(#arr)' opacity='0.6'/>
<line x1='197' y1='121' x2='210' y2='121' stroke='#599CE7' stroke-width='1.5' marker-end='url(#arr)' opacity='0.6'/>
"""
    return (
        "<div style='padding:8px;background:#141414;border-radius:8px;height:100%'>"
        "<div style='font-size:11px;letter-spacing:1px;text-transform:uppercase;"
        "color:#94a3b8;margin-bottom:6px'>Plant Layout — Process Flow</div>"
        f"<svg viewBox='0 0 310 230' width='100%' height='210' "
        f"style='background:#121218;border-radius:6px;border:1px solid #2a2a2e'>"
        + arrows
        + "".join(boxes)
        + "</svg></div>"
    )


def ai_panel_html() -> str:
    insights = [
        "Boiler efficiency has decreased 4% over the past 12 hours.",
        "Pump P-102 vibration has increased compared to baseline.",
        "Production is projected to exceed today's target.",
        "Two assets require preventive maintenance within seven days.",
    ]
    items = "".join(
        f"<div style='padding:8px 10px;margin:4px 0;background:#1e1e24;"
        f"border-left:3px solid #599CE7;border-radius:4px;font-size:12px;color:#cbd5e1'>{t}</div>"
        for t in insights
    )
    return (
        "<div style='padding:10px;background:#141414;border-radius:8px;height:100%'>"
        "<div style='font-size:13px;font-weight:600;color:#599CE7;margin-bottom:8px'>"
        "AI Operational Assistant</div>"
        + items
        + "<div style='margin-top:10px;padding:8px 12px;background:#1a1a1f;"
        "border:1px solid #3a3a42;border-radius:6px;font-size:12px;color:#64748b'>"
        "Ask AI about your plant…</div></div>"
    )


def gauge_chart(title: str) -> dict[str, Any]:
    return {
        "graph": {"title": title},
        "legend": {"show": False},
        "threshold": {
            "mode": "absolute",
            "steps": [
                {"color": "#ef4444", "value": None},
                {"color": "#eab308", "value": 60},
                {"color": "#22c55e", "value": 85},
            ],
        },
        "standardOptions": {"decimals": 1, "min": 0, "max": 100},
    }


def purge_partial(c: Client, host: int, prefix: str) -> None:
    for p in c.call("GET", f"/api/v1/elements/{host}/panels") or []:
        if (p.get("name") or "").startswith(prefix):
            try:
                c.call("DELETE", f"/api/v1/elements/{host}/panels/{p['id']}")
            except RuntimeError:
                pass
    for d in c.call("GET", f"/api/v1/elements/{host}/dashboards") or []:
        if (d.get("name") or "") == "Plant Operations Overview":
            c.call("DELETE", f"/api/v1/elements/{host}/dashboards/{d['id']}")


def main() -> None:
    c = Client()
    host = ROOT
    p: dict[str, dict[str, int]] = {}

    print("Building Plant Operations Overview on IDMP Canvas…")
    purge_partial(c, host, "Plant Operations")
    purge_partial(c, host, "Navigation")
    purge_partial(c, host, "OEE")
    purge_partial(c, host, "Production")
    purge_partial(c, host, "Energy")
    purge_partial(c, host, "Active")
    purge_partial(c, host, "Machine")
    purge_partial(c, host, "Average")
    purge_partial(c, host, "Alarm")
    purge_partial(c, host, "Pump")
    purge_partial(c, host, "Motor")
    purge_partial(c, host, "Compressor")
    purge_partial(c, host, "Boiler")
    purge_partial(c, host, "Pressure")
    purge_partial(c, host, "Temperature")
    purge_partial(c, host, "Flow")
    purge_partial(c, host, "Power")
    purge_partial(c, host, "Equipment")
    purge_partial(c, host, "Plant Layout")
    purge_partial(c, host, "AI Operational")

    p["nav"] = text_panel(c, host, "Navigation Rail", nav_html())
    p["header"] = text_panel(c, host, "Plant Operations Header", header_html())
    p["plant"] = text_panel(c, host, "Plant Layout", plant_layout_html())
    p["ai"] = text_panel(c, host, "AI Operational Assistant", ai_panel_html())

    # ── KPI row (6 stat cards) ──
    p["kpi_oee"] = chart_panel(
        c, host, "OEE", "stat",
        [attr(host, "54FC007.PV", "OEE_pct", child=host), attr(host, "54FC007.SV", "Target", child=host)],
        chart={"graph": {"title": "Overall Equipment Effectiveness"}, "series": {"textMode": "value_and_name"}},
    )
    p["kpi_prod"] = chart_panel(
        c, host, "Production Rate", "stat",
        [attr(host, "54FC001.PV", "Production", child=host)],
        chart={"graph": {"title": "Production Rate (units/day est.)"}, "series": {"textMode": "value_and_name"}},
    )
    p["kpi_energy"] = chart_panel(
        c, host, "Energy Consumption", "stat",
        [attr(host, "AC power", "Power_MW", child=INV_PUMP)],
        chart={"graph": {"title": "Energy Consumption (MW)"}, "series": {"textMode": "value_and_name"}},
    )
    p["kpi_alarms"] = chart_panel(
        c, host, "Active Alarms", "stat",
        [attr(host, "54PI014.PV", "Alarms", child=host)],
        chart={"graph": {"title": "Active Alarms"}, "series": {"textMode": "value_and_name"}},
    )
    p["kpi_avail"] = chart_panel(
        c, host, "Machine Availability", "stat",
        [attr(host, "54PC011.SV", "Availability", child=host)],
        chart={"graph": {"title": "Machine Availability (%)"}, "series": {"textMode": "value_and_name"}},
    )
    p["kpi_temp"] = chart_panel(
        c, host, "Average Temperature", "stat",
        [attr(host, "54PI036.PV", "Temperature", child=host)],
        chart={"graph": {"title": "Average Temperature (°C)"}, "series": {"textMode": "value_and_name"}},
    )

    # ── Main charts ──
    prod_ya = [attr(host, "54FC001.PV", "HDS_Feed", child=host)]
    prod_ya[0]["window"] = interval_window("15m")
    p["prod_trend"] = chart_panel(
        c, host, "Production Overview — 24 Hour", "line",
        prod_ya,
        time_from="now-24h",
        time_to="now",
        chart={
            "graph": {"title": "Production Rate — Last 24 Hours"},
            "legend": {"show": True, "placement": "bottom"},
            "series": {"graphMode": "area", "style": "smooth", "lineWidth": 2},
        },
    )

    util_ya = [
        attr(host, "54FC007.PV", "SHU_Flow", child=host),
        attr(host, "54FC061.PV", "HDS_Flow", child=host),
        attr(host, "52FC001.PV", "Gastail", child=host),
        attr(host, "54FC015.PV", "Aux_Flow", child=host),
    ]
    p["equip_util"] = chart_panel(
        c, host, "Equipment Utilization", "bar",
        util_ya,
        chart={"graph": {"title": "Equipment Utilization by Unit"}, "legend": {"show": True, "placement": "bottom"}},
    )

    # Alarm table — live process tags as proxy columns
    alarm_ya = [
        attr(host, "54PI014.PV", "Reactor_P", child=host),
        attr(host, "54PI036.PV", "HDS_P", child=host),
        attr(host, "54PI091.PV", "PC091", child=host),
        attr(host, "54FC007.PV", "Flow", child=host),
    ]
    p["alarms"] = chart_panel(
        c, host, "Alarm Summary", "table",
        alarm_ya,
        time_from="now-1h",
        time_to="now",
        chart={
            "graph": {"title": "Recent Alarms"},
            "format": "YYYY-MM-DD HH:mm:ss",
            "legend": {"show": False},
        },
    )

    # Health radial gauges
    p["health_pump"] = chart_panel(
        c, host, "Pump Health", "gauge",
        [attr(host, "Daily yield", "Pump_Health", child=INV_PUMP)],
        chart=gauge_chart("Pump Health"),
    )
    p["health_motor"] = chart_panel(
        c, host, "Motor Health", "gauge",
        [attr(host, "Daily yield", "Motor_Health", child=INV_MOTOR)],
        chart=gauge_chart("Motor Health"),
    )
    p["health_comp"] = chart_panel(
        c, host, "Compressor Health", "gauge",
        [attr(host, "Daily yield", "Comp_Health", child=INV_COMP)],
        chart=gauge_chart("Compressor Health"),
    )
    p["health_boiler"] = chart_panel(
        c, host, "Boiler Health", "gauge",
        [attr(host, "54PC091A.PV", "Boiler_Health", child=host)],
        chart=gauge_chart("Boiler Health"),
    )

    trend_specs = [
        ("trend_press", "Pressure Trend", "54PI014.PV", "Pressure_bar", "now-6h", host),
        ("trend_temp", "Temperature Trend", "54PI036.PV", "Temp_C", "now-6h", host),
        ("trend_flow", "Flow Trend", "54FC007.PV", "Flow_Lmin", "now-6h", host),
        ("trend_power", "Power Consumption", "AC power", "Power_MW", "now-6h", INV_PUMP),
    ]
    for key, title, attr_name, alias, tf, child in trend_specs:
        ya = [attr(host, attr_name, alias, child=child)]
        ya[0]["window"] = interval_window("5m")
        p[key] = chart_panel(
            c, host, title, "line",
            ya,
            time_from=tf,
            time_to="now",
            chart={
                "graph": {"title": title},
                "legend": {"show": False},
                "series": {"graphMode": "line", "style": "smooth"},
            },
        )

    layout = [
        cell(p["nav"], 0, 0, 2, 28),
        cell(p["header"], 2, 0, 22, 2),
        cell(p["kpi_oee"], 2, 2, 4, 3),
        cell(p["kpi_prod"], 6, 2, 3, 3),
        cell(p["kpi_energy"], 9, 2, 3, 3),
        cell(p["kpi_alarms"], 12, 2, 3, 3),
        cell(p["kpi_avail"], 15, 2, 4, 3),
        cell(p["kpi_temp"], 19, 2, 5, 3),
        cell(p["prod_trend"], 2, 5, 10, 7),
        cell(p["plant"], 12, 5, 6, 7),
        cell(p["alarms"], 18, 5, 6, 4),
        cell(p["health_pump"], 18, 9, 3, 3),
        cell(p["health_motor"], 21, 9, 3, 3),
        cell(p["health_comp"], 18, 12, 3, 3),
        cell(p["health_boiler"], 21, 12, 3, 3),
        cell(p["equip_util"], 2, 12, 10, 4),
        cell(p["trend_press"], 2, 16, 5, 5),
        cell(p["trend_temp"], 7, 16, 5, 5),
        cell(p["trend_flow"], 12, 16, 5, 5),
        cell(p["trend_power"], 17, 16, 7, 5),
        cell(p["ai"], 17, 21, 7, 4),
    ]

    body = {
        "name": "Plant Operations Overview",
        "description": (
            "Executive manufacturing operations dashboard — KPIs, production trends, "
            "plant layout, alarms, equipment health, and AI insights. Built via IDMP REST API."
        ),
        "panels": layout,
        "params": {
            "refreshInterval": 15,
            "fromText": "now-15m",
            "toText": "now",
        },
        "chart": THEME,
    }

    result = c.call("POST", f"/api/v1/elements/{host}/dashboards", body)
    did = int(result["id"])
    url = f"{IDMP_URL}/explorer/dashboard?id={did}"

    report = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "dashboard_id": did,
        "element_id": host,
        "name": "Plant Operations Overview",
        "url": url,
        "panel_count": len(layout),
    }
    report_path = os.path.join(os.path.dirname(__file__), "reports/plant-operations-overview.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    print(f"\nDashboard created: {url}")
    print(f"Report: {report_path}")
    print(f"Panels: {len(layout)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
