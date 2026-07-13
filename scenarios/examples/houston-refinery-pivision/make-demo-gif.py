#!/usr/bin/env python3
"""Capture a short looping GIF of the live Houston Canvas for demos."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "houston-refinery-demo.gif"
DASHBOARD_ID = int(os.environ.get("HOUSTON_DASHBOARD_ID", "2028111455094912"))
FRAMES = int(os.environ.get("DEMO_GIF_FRAMES", "8"))
INTERVAL = float(os.environ.get("DEMO_GIF_INTERVAL", "1.0"))


def login(base: str, user: str, password: str) -> str:
    body = json.dumps({"login_name": user, "password": password}).encode()
    req = urllib.request.Request(
        f"{base}/api/v1/users/login",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    return data.get("access_token") or data["token"]


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Need playwright in this environment.", file=sys.stderr)
        return 1
    try:
        from PIL import Image
    except ImportError:
        os.system(f"{sys.executable} -m pip install -q pillow")
        from PIL import Image

    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

    base = os.environ.get("IDMP_URL", "http://localhost:6842").rstrip("/")
    token = login(base, os.environ["IDMP_USER"], os.environ["IDMP_PASSWORD"])
    auth = f"Bearer {token}"

    frame_dir = Path("/tmp/houston-gif-frames")
    frame_dir.mkdir(parents=True, exist_ok=True)
    for old in frame_dir.glob("*.png"):
        old.unlink()

    editor = f"/canvas-dashboard-create/{DASHBOARD_ID}?ids=%2F1%2F2026702359773696"

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1600, "height": 900})
        context.add_cookies([{"name": "tda_token", "value": auth, "url": base}])
        context.add_init_script(
            """(token) => {
              sessionStorage.setItem('tda_token_local', token);
              localStorage.setItem('apiPath', '/api/v1');
            }""",
            auth,
        )
        context.route(
            "**/canvas-dashboard-create/**",
            lambda route: (
                route.continue_(
                    url=route.request.url.replace("/canvas-dashboard-create", "")
                )
                if any(
                    part in route.request.url
                    for part in ("/js/", "/css/", "/static/", "/api/")
                )
                else route.continue_()
            ),
        )
        page = context.new_page()
        page.goto(f"{base}/", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(4000)
        page.evaluate(
            """(path) => {
              history.pushState({}, '', path);
              dispatchEvent(new PopStateEvent('popstate', { state: history.state }));
            }""",
            editor,
        )
        page.wait_for_timeout(12000)
        page.evaluate(
            """() => {
              const canvasContainer = document.querySelector('.meta-2d-canvas');
              if (canvasContainer) {
                Object.assign(canvasContainer.style, {
                  position: 'fixed', inset: '0', zIndex: '999999',
                  width: '100vw', height: '100vh', background: '#1b2230',
                });
                if (window.meta2d) {
                  window.meta2d.resize();
                  window.meta2d.fitView(true, 20);
                  window.meta2d.render();
                }
              }
            }"""
        )
        page.wait_for_timeout(1500)
        paths: list[Path] = []
        for index in range(FRAMES):
            path = frame_dir / f"frame-{index:02d}.png"
            page.screenshot(path=str(path), full_page=False)
            paths.append(path)
            print(f"frame {index + 1}/{FRAMES}", flush=True)
            time.sleep(INTERVAL)
        browser.close()

    images = [Image.open(p).convert("P", palette=Image.ADAPTIVE, colors=128) for p in paths]
    images[0].save(
        OUT,
        save_all=True,
        append_images=images[1:],
        duration=int(INTERVAL * 1000),
        loop=0,
        optimize=True,
    )
    desktop = Path.home() / "Desktop" / OUT.name
    desktop.write_bytes(OUT.read_bytes())
    print(f"Wrote {OUT}")
    print(f"Also copied to {desktop}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
