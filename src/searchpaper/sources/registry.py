"""Source adapter registry."""

from __future__ import annotations

import asyncio
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


_STATUS_TIMEOUT_SECONDS = 10.0


async def source_status(name: str, **kwargs: object) -> SourceStatus:
    adapter = get_adapter(name, **kwargs)
    try:
        return await asyncio.wait_for(adapter.status(), timeout=_STATUS_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        return SourceStatus(
            source=name,
            state="degraded",
            message=f"Status check timed out after {_STATUS_TIMEOUT_SECONDS}s",
        )
    except Exception as exc:  # noqa: BLE001
        return SourceStatus(
            source=name,
            state="offline",
            message=f"Status check failed: {exc}",
        )
    finally:
        await adapter.aclose()


async def all_source_statuses(**kwargs: object) -> list[SourceStatus]:
    coros = [source_status(name, **kwargs) for name in list_sources()]
    results = await asyncio.gather(*coros, return_exceptions=True)
    statuses: list[SourceStatus] = []
    for name, result in zip(list_sources(), results):
        if isinstance(result, SourceStatus):
            statuses.append(result)
        else:
            statuses.append(
                SourceStatus(
                    source=name,
                    state="offline",
                    message=f"Status check failed: {result}",
                )
            )
    return statuses
