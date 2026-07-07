"""medRxiv source adapter."""

from __future__ import annotations

from searchpaper.sources.preprint import PreprintAdapter
from searchpaper.sources.registry import register


@register("medrxiv")
class MedRxivAdapter(PreprintAdapter):
    name = "medrxiv"
    server = "medrxiv"
