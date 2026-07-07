"""bioRxiv source adapter."""

from __future__ import annotations

from searchpaper.sources.preprint import PreprintAdapter
from searchpaper.sources.registry import register


@register("biorxiv")
class BioRxivAdapter(PreprintAdapter):
    name = "biorxiv"
    server = "biorxiv"
