#!/usr/bin/env python3
"""Precision-grid Houston Unit 3-1415 Canvas — orthogonal pipes only."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


def _pi_style_clock(moment: datetime) -> str:
    """PI Vision-like: 7/13/2026 3:18:04 PM"""
    return moment.strftime("%-m/%-d/%Y %-I:%M:%S %p")

ELEMENT_ID = 2026702359773696
DASHBOARD_ID = None
DISPLAY_NAME = "Houston Refinery Unit 3-1415 (ZIP Demo)"

WIDTH = 1920
HEIGHT = 1000

# Modern ops console — deep slate + electric cyan (not old PI Vision grey boards)
BG = "#0a0e14"
SURFACE = "#101820"
SURFACE_2 = "#15202c"
FRAME = "#243447"
TEXT = "#eef3f8"
MUTED = "#8b9eb0"
CYAN = "#4cc9ff"
LIVE = "#3dff9a"
PIPE = "#5eb8ff"
ACCENT = "#2a9df4"
HAIR = "#1e2c3c"
VALVE = "/static/png/IoT-valve symbols（阀门符号）/3-D Ball valve（三维球阀）.svg"
COLUMN = "/static/png/IoT-water tank（水槽）/Storage tank（储罐）.svg"
PUMP_BODY = "/static/png/IoT-water tank（水槽）/Drum（滚筒）.svg"


def snap(value: float, step: int = 10) -> float:
    return float(round(value / step) * step)


def rect(
    pen_id: str,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    background: str,
    color: str = FRAME,
    line_width: float = 1.5,
    radius: float = 0,
    dash: list[float] | None = None,
) -> dict[str, Any]:
    pen: dict[str, Any] = {
        "id": pen_id,
        "name": "rectangle",
        "x": snap(x),
        "y": snap(y),
        "width": snap(w),
        "height": snap(h),
        "background": background,
        "color": color,
        "lineWidth": line_width,
        "borderRadius": radius,
        "text": "",
        "disableAnchor": True,
    }
    if dash:
        pen["lineDash"] = dash
    return pen


def label(
    pen_id: str,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    *,
    size: float = 15,
    color: str = TEXT,
    align: str = "left",
    weight: str = "normal",
) -> dict[str, Any]:
    return {
        "id": pen_id,
        "name": "text",
        "x": snap(x),
        "y": snap(y),
        "width": w,
        "height": h,
        "text": text,
        "color": color,
        "fontSize": size,
        "fontWeight": weight,
        "textAlign": align,
        "disableAnchor": True,
    }


def hv(
    pens: list[dict[str, Any]],
    pen_id: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    color: str = PIPE,
    width: float = 3,
    animated: bool = True,
    dashed: bool = False,
) -> None:
    """Draw a single strictly horizontal or vertical segment."""
    x1, y1, x2, y2 = snap(x1), snap(y1), snap(x2), snap(y2)
    assert x1 == x2 or y1 == y2, f"non-orthogonal segment {pen_id}: {(x1,y1)}→{(x2,y2)}"
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    start_x = 0.0 if x1 <= x2 else 1.0
    end_x = 1.0 - start_x
    start_y = 0.0 if y1 <= y2 else 1.0
    end_y = 1.0 - start_y
    if dx == 0:
        start_x = end_x = 0.5
    if dy == 0:
        start_y = end_y = 0.5
    pen: dict[str, Any] = {
        "id": pen_id,
        "name": "line",
        "type": 1,
        "lineName": "line",
        "x": min(x1, x2),
        "y": min(y1, y2),
        "width": max(dx, 1),
        "height": max(dy, 1),
        "lineWidth": width,
        "color": color,
        "anchors": [
            {"id": "0", "x": start_x, "y": start_y, "start": True},
            {"id": "1", "x": end_x, "y": end_y},
        ],
        "lineAnimateType": 1,
        "animateColor": LIVE,
        "animateSpan": 1,
        "keepAnimateState": True,
        "autoPlay": animated,
        "animateShadow": True,
    }
    if dashed:
        pen["lineDash"] = [6, 5]
    pens.append(pen)


def route(
    pens: list[dict[str, Any]],
    prefix: str,
    points: list[tuple[float, float]],
    *,
    dashed: bool = False,
    width: float = 3,
) -> None:
    """Draw an orthogonal polyline through snapped points (axis-aligned elbows only)."""
    for index in range(len(points) - 1):
        x1, y1 = points[index]
        x2, y2 = points[index + 1]
        x1, y1, x2, y2 = snap(x1), snap(y1), snap(x2), snap(y2)
        if x1 == x2 and y1 == y2:
            continue
        if x1 != x2 and y1 != y2:
            # Force elbow: horizontal then vertical.
            mid = (x2, y1)
            hv(pens, f"{prefix}-{index}a", x1, y1, mid[0], mid[1], dashed=dashed, width=width)
            hv(pens, f"{prefix}-{index}b", mid[0], mid[1], x2, y2, dashed=dashed, width=width)
        else:
            hv(pens, f"{prefix}-{index}", x1, y1, x2, y2, dashed=dashed, width=width)


def image(
    pen_id: str,
    x: float,
    y: float,
    w: float,
    h: float,
    source: str,
) -> dict[str, Any]:
    return {
        "id": pen_id,
        "name": "image",
        "x": snap(x),
        "y": snap(y),
        "width": w,
        "height": h,
        "image": source,
        "crossOrigin": "anonymous",
        "disableAnchor": True,
    }


def live(
    pen_id: str,
    x: float,
    y: float,
    w: float,
    h: float,
    attr: str,
    placeholder: str,
    *,
    size: float = 15,
    color: str = LIVE,
) -> dict[str, Any]:
    pen = label(pen_id, x, y, w, h, placeholder, size=size, weight="bold", color=color)
    pen["form"] = [
        {
            "key": "text",
            "name": "value",
            "type": "text",
            "expression": f"${{attributes['{attr}']}}",
            "dataReferenceType": "Formula",
            "expressionElementId": ELEMENT_ID,
        }
    ]
    return pen


def feed_qc_card(pens: list[dict[str, Any]]) -> None:
    """Modern Feed QC data card — precision table, not a flat PI Vision text blob."""
    x, y, w, h = 36, 590, 320, 250
    rows = [
        ("Characterization Factor", "11.46"),
        ("API Gravity", "24"),
        ("Heavy Metals", "1,827 ppm"),
        ("Sulfur", "0.798 wt%"),
        ("Conradson Carbon", "0.3 wt%"),
        ("Final Boiling Point", "1,015.2 °F"),
        ("Initial Boiling Point", "406.6 °F"),
    ]
    pens.extend(
        [
            rect("qc-glow", x - 2, y - 2, w + 4, h + 4, background=HAIR, color=CYAN, line_width=1.25, radius=14),
            rect("qc", x, y, w, h, background=SURFACE, color=FRAME, line_width=1, radius=12),
            rect("qc-head", x, y, w, 40, background=SURFACE_2, color=SURFACE_2, line_width=0, radius=12),
            # Squared bottom of rounded header so it meets the body cleanly
            rect("qc-head-sq", x, y + 24, w, 16, background=SURFACE_2, color=SURFACE_2, line_width=0),
            rect("qc-head-accent", x, y + 10, 3, 20, background=CYAN, color=CYAN, line_width=0, radius=2),
            label("qc-title", x + 14, y + 10, 160, 22, "FEED QC", size=13, color=TEXT, weight="bold"),
            rect("qc-live-bg", x + w - 78, y + 10, 66, 20, background="#0f2a22", color=LIVE, line_width=1, radius=10),
            label("qc-live", x + w - 78, y + 11, 66, 18, "● LIVE", size=11, color=LIVE, align="center", weight="bold"),
        ]
    )
    row_y = y + 50
    for index, (name, value) in enumerate(rows):
        if index % 2 == 0:
            pens.append(
                rect(
                    f"qc-row-{index}",
                    x + 10,
                    row_y - 3,
                    w - 20,
                    24,
                    background="#121c28",
                    color="#121c28",
                    line_width=0,
                    radius=6,
                )
            )
        pens.extend(
            [
                label(f"qc-k-{index}", x + 16, row_y, 168, 18, name, size=11, color=MUTED),
                label(f"qc-v-{index}", x + 178, row_y, 122, 18, value, size=12, color=TEXT, align="right", weight="bold"),
            ]
        )
        row_y += 26


def tip(pens: list[dict[str, Any]], pen_id: str, x: float, y: float) -> None:
    pens.append(
        {
            "id": pen_id,
            "name": "rightArrow",
            "x": snap(x),
            "y": snap(y) - 5,
            "width": 14,
            "height": 10,
            "color": CYAN,
            "background": CYAN,
            "disableAnchor": True,
        }
    )


def column(
    pens: list[dict[str, Any]],
    pen_id: str,
    x: float,
    y: float,
    w: float,
    h: float,
    trays: int,
) -> tuple[float, float, float, float]:
    """Place a 3D vertical vessel with a modern nameplate."""
    x, y, w, h = snap(x), snap(y), snap(w), snap(h)
    pens.append(
        rect(
            f"{pen_id}-silhouette",
            x + w * 0.18,
            y + 8,
            w * 0.64,
            h - 16,
            background="#7d8896",
            color="#c5ced8",
            line_width=1,
            radius=w * 0.32,
        )
    )
    pens.append(image(f"{pen_id}-body", x, y, w, h, COLUMN))
    for i in range(1, min(trays, 8) + 1):
        ty = y + (i / (min(trays, 8) + 1)) * h
        hv(
            pens,
            f"{pen_id}-tray-{i}",
            x + w * 0.28,
            ty,
            x + w * 0.72,
            ty,
            color="#5a6570",
            width=1.25,
            animated=False,
        )
    # Modern nameplate chip above vessel
    pens.extend(
        [
            rect(
                f"{pen_id}-tag",
                x + (w - 72) / 2,
                y - 30,
                72,
                22,
                background=SURFACE_2,
                color=CYAN,
                line_width=1,
                radius=6,
            ),
            label(
                f"{pen_id}-name",
                x + (w - 72) / 2,
                y - 28,
                72,
                18,
                "C-1309",
                size=12,
                color=CYAN,
                align="center",
                weight="bold",
            ),
        ]
    )
    return x + w / 2, y, y + h / 2, y + h


def valve(
    pens: list[dict[str, Any]],
    pen_id: str,
    x: float,
    y: float,
    *,
    label_text: str,
    label_dy: float = 22,
) -> None:
    """3D ball valve with a tight modern tag chip."""
    pens.extend(
        [
            image(pen_id, x, y - 14, 56, 28, VALVE),
            rect(
                f"{pen_id}-chip",
                x - 6,
                y + label_dy - 2,
                68,
                20,
                background=SURFACE_2,
                color=FRAME,
                line_width=1,
                radius=5,
            ),
            label(
                f"{pen_id}-name",
                x - 6,
                y + label_dy,
                68,
                16,
                label_text,
                size=11,
                color=CYAN,
                align="center",
                weight="bold",
            ),
        ]
    )


def pump_symbol(pens: list[dict[str, Any]], x: float, y: float) -> None:
    """Compact centrifugal-style pump + modern nameplate."""
    pens.extend(
        [
            image("pump-body", x - 22, y - 30, 44, 60, PUMP_BODY),
            {
                "id": "pump-hub",
                "name": "circle",
                "x": x - 14,
                "y": y - 14,
                "width": 28,
                "height": 28,
                "background": "#a8b4c0",
                "color": "#e8eef4",
                "lineWidth": 2,
                "disableAnchor": True,
            },
            rect("pump-nozzle", x + 12, y - 6, 22, 12, background="#8a959f", color="#d7dee8", line_width=1, radius=3),
            rect("pump-chip", x - 46, y + 32, 92, 22, background=SURFACE_2, color=FRAME, line_width=1, radius=6),
            label("pump-name", x - 46, y + 34, 92, 18, "P-24/09A", size=12, color=CYAN, align="center", weight="bold"),
        ]
    )


def pvsp(
    pens: list[dict[str, Any]],
    prefix: str,
    x: float,
    y: float,
    pv_attr: str,
    sp_attr: str | None,
    pv: str,
    sp: str,
) -> None:
    """Modern PV/SP glass card — precise tabular readouts."""
    pens.append(
        rect(
            f"{prefix}-card",
            x - 8,
            y - 6,
            150,
            50,
            background="rgba(16,24,32,0.92)",
            color=FRAME,
            line_width=1,
            radius=8,
        )
    )
    pens.extend(
        [
            label(f"{prefix}-pl", x, y, 28, 16, "PV", size=11, align="left", color=MUTED),
            live(f"{prefix}-pv", x + 30, y - 1, 70, 18, pv_attr, pv, size=14, color=LIVE),
            label(f"{prefix}-pu", x + 102, y, 32, 16, "gpm", size=11, color=MUTED),
            label(f"{prefix}-sl", x, y + 20, 28, 16, "SP", size=11, align="left", color=MUTED),
        ]
    )
    if sp_attr:
        pens.append(live(f"{prefix}-sp", x + 30, y + 19, 70, 18, sp_attr, sp, size=14, color=CYAN))
    else:
        pens.append(label(f"{prefix}-sp", x + 30, y + 19, 70, 18, sp, size=14, weight="bold", color=CYAN))
    pens.append(label(f"{prefix}-su", x + 102, y + 20, 32, 16, "gpm", size=11, color=MUTED))


def build_pens() -> list[dict[str, Any]]:
    pens: list[dict[str, Any]] = [
        rect("bg", 0, 0, WIDTH, HEIGHT, background=BG, color=BG, line_width=0),
        # Soft modern stage — thin hairline, large radius (not heavy old-school bezel)
        rect("frame", 20, 56, 1880, 860, background=SURFACE, color=FRAME, line_width=1, radius=16),
        label("title", 40, 72, 420, 26, "Houston Refinery", size=18, weight="bold"),
        label("subtitle", 40, 96, 320, 18, "Unit 3-1415  ·  Distillation", size=12, color=MUTED),
        rect("live-chip", 460, 74, 86, 24, background="#0f2a22", color=LIVE, line_width=1, radius=12),
        label("live-chip-t", 460, 76, 86, 20, "● LIVE", size=12, color=LIVE, align="center", weight="bold"),
        label("live-sub", 556, 78, 300, 18, "streaming historian  ·  2s refresh", size=11, color=MUTED),
    ]

    # ---- Equipment anchors (10px grid) — same precise topology as PI Vision ----
    main_x, main_y, main_w, main_h = 260, 150, 100, 400
    main_cx, main_top, main_mid, main_bot = column(pens, "main", main_x, main_y, main_w, main_h, 11)

    side_x, side_y, side_w, side_h = 620, 240, 110, 260
    side_cx, side_top, side_mid, side_bot = column(pens, "side", side_x, side_y, side_w, side_h, 6)

    # Feed Sched / Actual — modern KPI strip
    pens.extend(
        [
            rect("feed-badge", 40, 198, 180, 62, background=SURFACE_2, color=FRAME, line_width=1, radius=10),
            rect("feed-accent", 40, 208, 3, 42, background=CYAN, color=CYAN, line_width=0, radius=2),
            label("sched-l", 54, 206, 52, 18, "SCHED", size=11, color=MUTED),
            live("sched", 108, 204, 64, 20, "52FC001.SV", "2,536", size=15, color=CYAN),
            label("sched-u", 174, 208, 36, 16, "gpm", size=11, color=MUTED),
            label("actual-l", 54, 232, 52, 18, "ACTUAL", size=11, color=MUTED),
            live("actual", 108, 230, 64, 20, "52FC001.PV", "2,540", size=15, color=LIVE),
            label("actual-u", 174, 234, 36, 16, "gpm", size=11, color=MUTED),
        ]
    )

    route(pens, "feed", [(40, main_mid), (main_x, main_mid)], width=5)
    tip(pens, "feed-tip", main_x - 18, main_mid)

    oh_y = 120
    route(
        pens,
        "oh",
        [
            (side_cx, side_top),
            (side_cx, oh_y),
            (main_cx, oh_y),
            (main_cx, main_top),
        ],
        dashed=True,
        width=3,
    )

    mid_y = 340
    route(pens, "mid", [(main_x + main_w, mid_y), (side_x, mid_y)], width=3)
    valve(pens, "lc-valve", 480, mid_y, label_text="LC-780")
    pvsp(pens, "lc780", 450, mid_y - 62, "54FC007.PV", "54FC007.SV", "2,489", "2,600")

    fc009_y = mid_y
    fc009_x = side_x + side_w
    route(pens, "fc009-run", [(fc009_x, fc009_y), (fc009_x + 160, fc009_y)], width=3)
    valve(pens, "fc009-valve", fc009_x + 40, fc009_y, label_text="FC-009")
    pvsp(pens, "fc009", fc009_x + 110, fc009_y - 50, "54FC001.PV", "54FC001.SV", "298", "300")

    pump_x = 780
    pump_y = 700
    header_x = 1100
    route(
        pens,
        "bottoms",
        [
            (side_cx, side_bot),
            (side_cx, pump_y),
            (header_x, pump_y),
        ],
        width=3,
    )
    pump_symbol(pens, pump_x, pump_y)

    branch_ys = [360, 470, 600]
    outlets = [
        ("FC-010", "Plant", "54FY026A.PV", "1,000", branch_ys[0]),
        ("FC-011", "", "54FY026B.PV", "900", branch_ys[1]),
        ("FC-012", "Storage", "54FY026C.PV", "900", branch_ys[2]),
    ]
    route(pens, "hdr", [(header_x, branch_ys[0]), (header_x, pump_y)], width=3)

    valve_x = 1380
    end_x = 1860
    for index, (tag, dest, attr, sp, by) in enumerate(outlets, start=1):
        route(pens, f"br{index}", [(header_x, by), (end_x, by)], width=3)
        tip(pens, f"br{index}-tip", end_x - 2, by)
        pens.extend(
            [
                # Soft valve pad — no dashed “old SCADA” box
                rect(
                    f"br{index}-box",
                    valve_x - 8,
                    by - 26,
                    64,
                    52,
                    background="rgba(16,24,32,0.55)",
                    color=FRAME,
                    line_width=1,
                    radius=10,
                ),
                image(f"br{index}-valve", valve_x - 4, by - 14, 56, 28, VALVE),
                rect(
                    f"br{index}-chip",
                    valve_x - 6,
                    by + 20,
                    60,
                    18,
                    background=SURFACE_2,
                    color=FRAME,
                    line_width=1,
                    radius=5,
                ),
                label(
                    f"br{index}-tag",
                    valve_x - 6,
                    by + 21,
                    60,
                    16,
                    tag,
                    size=11,
                    color=CYAN,
                    align="center",
                    weight="bold",
                ),
            ]
        )
        if dest:
            pens.extend(
                [
                    rect(
                        f"br{index}-dest-bg",
                        valve_x + 70,
                        by - 28,
                        72,
                        20,
                        background="#132536",
                        color=ACCENT,
                        line_width=1,
                        radius=6,
                    ),
                    label(
                        f"br{index}-dest",
                        valve_x + 70,
                        by - 27,
                        72,
                        18,
                        dest.upper(),
                        size=11,
                        weight="bold",
                        color=CYAN,
                        align="center",
                    ),
                ]
            )
        pvsp(pens, f"br{index}", valve_x + 160, by - 20, attr, None, "945", sp)

    feed_qc_card(pens)

    end = datetime.now()
    start = end - timedelta(hours=8)
    pens.extend(
        [
            rect("timebar", 20, 930, 1880, 50, background="#070b10", color=FRAME, line_width=1, radius=10),
            label("t0", 40, 944, 280, 20, _pi_style_clock(start), size=12, color=MUTED),
            rect("t8-pill", 870, 940, 100, 24, background=SURFACE_2, color=CYAN, line_width=1, radius=12),
            label("t8", 870, 943, 100, 18, "8h · LIVE", size=12, color=CYAN, align="center", weight="bold"),
            label("t1", 1460, 944, 260, 20, _pi_style_clock(end), size=12, color=LIVE, align="right"),
            rect("now", 1760, 938, 72, 28, background=LIVE, color=LIVE, line_width=0, radius=14),
            label("now-t", 1760, 943, 72, 18, "NOW", size=12, color="#042016", align="center", weight="bold"),
        ]
    )
    return pens


def panel_placements() -> list[dict[str, Any]]:
    return [
        {"panel": "product_flows", "x": 980, "y": 90, "w": 520, "h": 230},
        {"panel": "feed_flow", "x": 1120, "y": 760, "w": 480, "h": 150},
    ]


def main() -> None:
    output = Path(__file__).with_name("display.json")
    display: dict[str, Any] = {
        "name": DISPLAY_NAME,
        "description": "Modern precision Canvas of PI Vision Houston Unit 3-1415 — live, editable, operator-ready.",
        "element_id": ELEMENT_ID,
        "dashboard_type": "canvas",
        "theme": "process",
        "refresh_seconds": 2,
        "time_from": "now-8h",
        "time_to": "now",
        "header_html": (
            "<div style='height:100%;box-sizing:border-box;padding:8px 18px;"
            "display:flex;align-items:center;gap:14px;"
            "background:linear-gradient(90deg,#070b10,#101820 50%,#0c1a16);"
            "border-bottom:1px solid #243447;color:#eef3f8;"
            "font-family:ui-sans-serif,system-ui,-apple-system,sans-serif'>"
            "<div style='font-size:13px;font-weight:700;letter-spacing:.08em;text-transform:uppercase'>"
            "TDengine IDMP</div>"
            "<div style='width:1px;height:16px;background:#243447'></div>"
            "<div style='font-size:12px;color:#8b9eb0'>Modern P&amp;ID · Unit 3-1415</div>"
            "<div style='margin-left:auto;display:flex;align-items:center;gap:10px'>"
            "<span style='padding:3px 10px;border-radius:999px;background:#0f2a22;"
            "border:1px solid #3dff9a;color:#3dff9a;font-size:11px;font-weight:700;"
            "letter-spacing:.04em'>● LIVE</span>"
            f"<span style='font-size:11px;color:#8b9eb0;font-variant-numeric:tabular-nums'>"
            f"now-8h → now · {_pi_style_clock(datetime.now())}</span>"
            "<span style='font-size:11px;color:#4cc9ff'>precision Canvas</span>"
            "</div></div>"
        ),
        "canvas": {
            "width": WIDTH,
            "height": HEIGHT,
            "background": BG,
            "text_color": TEXT,
            "line_width": 4,
            "network_interval": 1,
            "header_placement": {"x": 20, "y": 8, "w": 1880, "h": 40},
            "pens": build_pens(),
            "panel_placements": panel_placements(),
        },
    }
    if DASHBOARD_ID:
        display["dashboard_id"] = DASHBOARD_ID
    for pen in display["canvas"]["pens"]:
        if pen.get("name") == "line":
            w, h = float(pen["width"]), float(pen["height"])
            if w > 1 and h > 1:
                raise AssertionError(f"Diagonal line slipped through: {pen['id']} {w}x{h}")
    output.write_text(json.dumps(display, indent=2), encoding="utf-8")
    print(f"Wrote {output} with {len(display['canvas']['pens'])} pens (all ortho)")


if __name__ == "__main__":
    main()
