"""Source health diagnostics and usage recommendations."""

from __future__ import annotations

from typing import Any

from searchpaper.config import ENV_MAPPINGS, load_config
from searchpaper.source_catalog import get_source_descriptor
from searchpaper.sources.registry import source_status


def _key_env_var(source: str) -> str | None:
    """Return the environment variable name that configures a source API key, if any."""
    for env_var, (cfg_key, _) in ENV_MAPPINGS.items():
        if cfg_key.startswith(source):
            return env_var
    return None


def _recommendation(source: str, status: dict[str, Any], descriptor: dict[str, Any]) -> list[str]:
    """Generate actionable recommendations for a source based on its status."""
    recommendations: list[str] = []
    state = status.get("state", "offline")
    key_required = descriptor.get("requires_key", False)
    key_configured = status.get("key_configured", False)

    if state in ("available", "available_with_key_optional"):
        if key_required and not key_configured:
            env_var = _key_env_var(source)
            hint = f"set {env_var}" if env_var else "configure an API key"
            recommendations.append(f"Source is reachable but a key may improve quota; {hint}.")
        else:
            recommendations.append("Source is healthy and ready to use.")
    elif state == "available_with_key_required":
        env_var = _key_env_var(source)
        hint = f"set {env_var}" if env_var else "configure an API key"
        recommendations.append(f"A valid API key is required; {hint}.")
    elif state == "degraded":
        recommendations.append(
            "Source is degraded. Expect slower responses or partial results; consider adding fallback sources."
        )
    elif state == "rate_limited":
        recommendations.append("Rate limit detected. Wait before retrying or configure an API key for higher quota.")
    elif state == "offline":
        recommendations.append(
            "Source appears offline. Check network connectivity, API status page, and any required API key."
        )
    elif state == "not_configured":
        recommendations.append(
            "Source is not configured. Review required credentials or disable it from default sources."
        )
    elif state == "not_implemented":
        recommendations.append("Source is listed in the catalog but has no adapter yet.")

    risk_note = descriptor.get("risk_note")
    if risk_note:
        recommendations.append(f"Usage note: {risk_note}")

    return recommendations


async def explain_source(source: str) -> dict[str, Any]:
    """Return catalog metadata, current health status, and usage recommendations for one source."""
    descriptor = get_source_descriptor(source).model_dump(mode="json")
    status = (await source_status(source)).model_dump(mode="json")
    cfg = load_config()
    key_env_var = _key_env_var(source)
    key_configured = bool(cfg.get(key_env_var.lower())) if key_env_var else False
    status["key_configured"] = key_configured

    return {
        "schema_version": "0.2",
        "object_type": "source_explanation",
        "source": source,
        "descriptor": descriptor,
        "status": status,
        "recommendations": _recommendation(source, status, descriptor),
        "api_docs_url": descriptor.get("api_docs_url"),
    }


async def diagnose_sources(sources: list[str] | None = None) -> dict[str, Any]:
    """Run health diagnostics for selected sources and return an aggregate report."""
    from searchpaper.sources import list_sources

    if sources is None:
        sources = list_sources()

    cfg = load_config()
    entries: list[dict[str, Any]] = []
    healthy = 0
    degraded = 0
    offline = 0

    for source in sources:
        try:
            descriptor = get_source_descriptor(source).model_dump(mode="json")
        except KeyError:
            descriptor = {"name": source, "implemented": False, "requires_key": False}
        try:
            status = (await source_status(source)).model_dump(mode="json")
        except Exception as exc:  # noqa: BLE001
            status = {"source": source, "state": "offline", "message": str(exc)}

        key_env_var = _key_env_var(source)
        status["key_configured"] = bool(cfg.get(key_env_var.lower())) if key_env_var else False

        state = status.get("state", "offline")
        if state in ("available", "available_with_key_optional"):
            healthy += 1
        elif state == "degraded":
            degraded += 1
        else:
            offline += 1

        entries.append(
            {
                "source": source,
                "descriptor": descriptor,
                "status": status,
                "recommendations": _recommendation(source, status, descriptor),
            }
        )

    summary_state = "healthy" if offline == 0 and degraded == 0 else "degraded" if offline == 0 else "unhealthy"

    return {
        "schema_version": "0.2",
        "object_type": "source_diagnosis",
        "summary": {
            "state": summary_state,
            "total": len(sources),
            "healthy": healthy,
            "degraded": degraded,
            "offline": offline,
        },
        "sources": entries,
    }


def diagnose_configuration() -> dict[str, Any]:
    """Inspect local configuration and report missing or misconfigured items."""
    cfg = load_config()
    issues: list[str] = []
    ok: list[str] = []

    for env_var, (cfg_key, _) in ENV_MAPPINGS.items():
        if cfg_key in ("cache_path", "config_path"):
            continue
        value = cfg.get(cfg_key)
        if value:
            ok.append(f"{cfg_key} is configured via {env_var}")
        else:
            issues.append(f"{cfg_key} is not configured ({env_var} not set and missing from config file)")

    return {
        "schema_version": "0.2",
        "object_type": "configuration_diagnosis",
        "config_path": str(cfg.get("config_path", "")),
        "cache_path": str(cfg.get("cache_path", "")),
        "configured_keys": ok,
        "issues": issues,
    }
