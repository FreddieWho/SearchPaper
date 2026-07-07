"""Legacy MCP server entry point for ``paper_search``.

Delegates to the canonical ``searchpaper.mcp_server``. New integrations should
use ``searchpaper serve --mcp`` or configure the ``searchpaper`` MCP server
instead.
"""

import warnings

from searchpaper.mcp_server import main

warnings.warn(
    "paper_search.server is deprecated; use searchpaper.mcp_server instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["main"]
