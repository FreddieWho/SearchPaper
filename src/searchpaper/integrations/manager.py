"""Integration manager for SearchPaper agent integrations."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from searchpaper.integrations import claude, codex, opencode

STATE_PATH = Path.home() / ".config" / "searchpaper" / "integrations.json"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"schema_version": "0.2", "searchpaper_version": "0.2.0", "installed_targets": {}}


def _save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


class IntegrationManager:
    """Install, uninstall, and diagnose SearchPaper agent integrations."""

    TARGETS = {
        "opencode": opencode,
        "codex": codex,
        "claude": claude,
    }

    async def install(self, target: str, dry_run: bool = False) -> dict[str, Any]:
        targets = list(self.TARGETS.keys()) if target == "all" else [target]
        results: list[dict[str, Any]] = []
        state = _load_state()
        for t in targets:
            module = self.TARGETS.get(t)
            if not module:
                results.append({"target": t, "error": "Unknown target"})
                continue
            result = module.install(dry_run=dry_run)
            results.append(result)
            if not dry_run:
                state["installed_targets"][t] = {
                    "modes": ["mcp", "skill"],
                    "scope": "user",
                    "installed_at": _now(),
                }
        if not dry_run:
            _save_state(state)
        return {"target": target, "dry_run": dry_run, "results": results}

    def status(self) -> dict[str, Any]:
        state = _load_state()
        statuses = {t: module.detect() for t, module in self.TARGETS.items()}
        return {
            "schema_version": state.get("schema_version"),
            "searchpaper_version": state.get("searchpaper_version"),
            "installed_targets": state.get("installed_targets", {}),
            "detected": statuses,
        }

    async def uninstall(self, target: str, dry_run: bool = False) -> dict[str, Any]:
        targets = list(self.TARGETS.keys()) if target == "all" else [target]
        results: list[dict[str, Any]] = []
        state = _load_state()
        for t in targets:
            module = self.TARGETS.get(t)
            if not module:
                results.append({"target": t, "error": "Unknown target"})
                continue
            result = module.uninstall(dry_run=dry_run)
            results.append(result)
            if not dry_run and t in state["installed_targets"]:
                del state["installed_targets"][t]
        if not dry_run:
            _save_state(state)
        return {"target": target, "dry_run": dry_run, "results": results}

    def doctor(self) -> dict[str, Any]:
        checks = {t: module.doctor() for t, module in self.TARGETS.items()}
        return {
            "schema_version": "0.2",
            "state_path": str(STATE_PATH),
            "state_exists": STATE_PATH.exists(),
            "checks": checks,
        }
