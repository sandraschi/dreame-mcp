"""Global state for Dreame MCP."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import DreameHomeClient

_state: dict = {}
# Keys:
#   "client"  -> DreameHomeClient | None
