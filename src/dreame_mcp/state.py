"""Global state for Dreame MCP."""

_state: dict = {}
# Keys:
#   "client"        -> DreameHomeClient | None (None when not connected)
#   "configured"    -> bool (True when .env/env credentials exist, even if the
#                      robot is currently unreachable — distinct from connected)
#   "connection"    -> dict snapshot {ip, did, has_cloud_creds, cloud_error}
#                      taken at startup so status stays honest after failure
#   "startup_error" -> str | None (why there is no live client, if any)
