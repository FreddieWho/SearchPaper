"""Integration manager for SearchPaper agent integrations."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from searchpaper import __version__
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
    return {"schema_version": "0.2", "searchpaper_version": __version__, "installed_targets": {}}


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
                managed_files = [change["path"] for change in result.get("changes", []) if "path" in change]
                state["installed_targets"][t] = {
                    "modes": ["mcp", "skill"],
                    "scope": "user",
                    "installed_at": _now(),
                    "managed_files": managed_files,
                }
        if not dry_run:
            state["searchpaper_version"] = __version__
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

    def needs_migration(self) -> dict[str, Any]:
        """Check whether installed integrations were created by an older SearchPaper version."""
        state = _load_state()
        installed = state.get("installed_targets", {})
        state_version = state.get("searchpaper_version")
        outdated_targets = [t for t, info in installed.items() if info.get("searchpaper_version") != __version__]
        return {
            "schema_version": "0.2",
            "current_version": __version__,
            "state_version": state_version,
            "needs_migration": state_version != __version__ or bool(outdated_targets),
            "outdated_targets": outdated_targets,
            "installed_targets": list(installed.keys()),
        }

    async def migrate(self, target: str, dry_run: bool = False) -> dict[str, Any]:
        """Re-install managed files for selected targets to bring them up to date."""
        targets = list(self.TARGETS.keys()) if target == "all" else [target]
        results: list[dict[str, Any]] = []
        state = _load_state()
        for t in targets:
            module = self.TARGETS.get(t)
            if not module:
                results.append({"target": t, "error": "Unknown target"})
                continue
            if t not in state.get("installed_targets", {}):
                results.append({"target": t, "skipped": True, "reason": "Not previously installed by SearchPaper"})
                continue
            result = module.install(dry_run=dry_run)
            result["target"] = t
            result["migrated"] = True
            results.append(result)
            if not dry_run:
                managed_files = [change["path"] for change in result.get("changes", []) if "path" in change]
                state["installed_targets"][t] = {
                    "modes": ["mcp", "skill"],
                    "scope": "user",
                    "installed_at": _now(),
                    "migrated_at": _now(),
                    "searchpaper_version": __version__,
                    "managed_files": managed_files,
                }
        if not dry_run:
            state["searchpaper_version"] = __version__
            _save_state(state)
        return {"target": target, "dry_run": dry_run, "results": results}

    def doctor(self) -> dict[str, Any]:
        checks = {t: module.doctor() for t, module in self.TARGETS.items()}
        migration = self.needs_migration()
        return {
            "schema_version": "0.2",
            "state_path": str(STATE_PATH),
            "state_exists": STATE_PATH.exists(),
            "needs_migration": migration["needs_migration"],
            "current_version": migration["current_version"],
            "state_version": migration["state_version"],
            "checks": checks,
        }
