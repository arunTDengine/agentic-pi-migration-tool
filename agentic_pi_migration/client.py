"""IDMP REST API client for agentic dashboard migration."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class IdmpClient:
    def __init__(self, base_url: str, login_name: str, password: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._headers: dict[str, str] = {"Content-Type": "application/json"}
        self.login(login_name, password)

    def login(self, login_name: str, password: str) -> None:
        data = self._request(
            "POST",
            "/api/v1/users/login",
            {"login_name": login_name, "password": password},
            auth=False,
        )
        token = data.get("token")
        if not token:
            raise RuntimeError("IDMP login succeeded but no token was returned.")
        self._headers["Authorization"] = f"Bearer {token}"

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        auth: bool = True,
    ) -> Any:
        url = f"{self.base_url}{path}"
        payload = json.dumps(body).encode() if body is not None else None
        headers = self._headers if auth else {"Content-Type": "application/json"}
        req = urllib.request.Request(url, data=payload, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read()
                if not raw:
                    return {}
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"IDMP {method} {path} failed ({exc.code}): {detail}") from exc

    def get_dashboard(self, element_id: int, dashboard_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/elements/{element_id}/dashboards/{dashboard_id}")

    def update_dashboard(
        self,
        element_id: int,
        dashboard_id: int,
        body: dict[str, Any],
    ) -> None:
        self._request("PUT", f"/api/v1/elements/{element_id}/dashboards/{dashboard_id}", body)

    def delete_dashboard(self, element_id: int, dashboard_id: int) -> None:
        self._request("DELETE", f"/api/v1/elements/{element_id}/dashboards/{dashboard_id}")

    def create_panel(self, element_id: int, panel: dict[str, Any]) -> int:
        result = self._request("POST", f"/api/v1/elements/{element_id}/panels", panel)
        return int(result["id"])

    def update_panel(self, element_id: int, panel_id: int, panel: dict[str, Any]) -> None:
        self._request("PUT", f"/api/v1/elements/{element_id}/panels/{panel_id}", panel)

    def delete_panel(self, element_id: int, panel_id: int) -> None:
        self._request("DELETE", f"/api/v1/elements/{element_id}/panels/{panel_id}")

    def get_panel(self, element_id: int, panel_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/elements/{element_id}/panels/{panel_id}")

    def ai_create_panel(self, element_id: int, prompt: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/ai/panels/create",
            {"elementId": element_id, "prompt": prompt, "record": True},
        )

    def search_elements(self, keyword: str, limit: int = 50) -> list[dict[str, Any]]:
        result = self._request("GET", f"/api/v1/elements/search?keyword={keyword}&limit={limit}")
        return result.get("rows", [])
