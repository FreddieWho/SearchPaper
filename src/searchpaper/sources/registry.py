"""Source adapter registry."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from searchpaper.schemas import SourceStatus

if TYPE_CHECKING:
    from searchpaper.sources.base import SourceAdapter

_SOURCE_CLASSES: dict[str, type[SourceAdapter]] = {}


def register(name: str, cls: type[SourceAdapter] | None = None) -> type[SourceAdapter] | Any:
    """Register an adapter class under ``name``.

    Can be used as ``@register("name")`` or ``register("name", AdapterClass)``.
    """

    def _decorator(klass: type[SourceAdapter]) -> type[SourceAdapter]:
        _SOURCE_CLASSES[name] = klass
        return klass

    if cls is not None:
        return _decorator(cls)
    return _decorator


def list_sources() -> list[str]:
    return sorted(_SOURCE_CLASSES.keys())


def get_adapter(name: str, **kwargs: object) -> SourceAdapter:
    """Instantiate an adapter by name."""
    name = name.lower().strip()
    if name not in _SOURCE_CLASSES:
        raise KeyError(f"Unknown source adapter: {name}")
    return _SOURCE_CLASSES[name](**kwargs)


def has_adapter(name: str) -> bool:
    return name.lower().strip() in _SOURCE_CLASSES


async def source_status(name: str, **kwargs: object) -> SourceStatus:
    adapter = get_adapter(name, **kwargs)
    try:
        return await adapter.status()
    finally:
        await adapter.aclose()


async def all_source_statuses(**kwargs: object) -> list[SourceStatus]:
    results: list[SourceStatus] = []
    for name in list_sources():
        try:
            results.append(await source_status(name, **kwargs))
        except Exception as exc:
            results.append(
                SourceStatus(
                    source=name,
                    state="offline",
                    message=f"Status check failed: {exc}",
                )
            )
    return results
