# Dreame D20 Pro API token (miio) — historical reference

> **dreame-mcp v0.2+** uses **DreameHome cloud** credentials (`DREAME_USER`, `DREAME_PASSWORD`) and does **not** require `DREAME_IP` / `DREAME_TOKEN` for normal operation.  
> This page remains for **local miIO** workflows, other tools, or older documentation.

The Dreame D20 Pro can use the miio protocol for **local** control on some firmware. To get **DREAME_TOKEN** (and the robot IP for **DREAME_IP**), one practical path is via **Home Assistant**.

## Why Home Assistant

- Dreame/Xiaomi cloud token extraction tools (e.g. Xiaomi cloud tokens extractor) exist but are brittle and depend on cloud login.
- **Home Assistant** has a maintained [Dreame Vacuum integration](https://www.home-assistant.io/integrations/dreame_vacuum/) that discovers the robot and obtains or uses the local token as part of the setup flow.
- Once the vacuum is added in HA, you can read the token (and IP) from the HA device/entity configuration or from the integration’s config entry data.

## Steps (outline)

1. **Install and run Home Assistant** (e.g. HA OS, Core, or supervised).
2. **Add the Dreame Vacuum integration** (Settings → Devices & services → Add integration → search “Dreame”).
3. **Complete the HA setup** (follow HA’s prompts; it may use cloud or local discovery).
4. **Get the token and IP**  
   - From the integration’s config entry: in HA, the Dreame integration often stores the miio token in the config entry data.  
   - Use a HA helper (e.g. “Developer tools → Services” or a custom template) or inspect the `.storage` config to read the token and device IP.  
   - Alternatively, use a “Xiaomi Miio” or “Dreame” token-extractor that works with HA-discovered devices if documented in the integration.
5. **Configure dreame-mcp**: set **DREAME_IP** to the robot’s IP and **DREAME_TOKEN** to the token, then restart the MCP server.

## References

- [Home Assistant – Dreame Vacuum](https://www.home-assistant.io/integrations/dreame_vacuum/)
- [python-miio](https://github.com/rytilahti/python-miio) — library used by many Xiaomi ecosystem tools (dreame-mcp v0.2+ cloud path does not depend on it)

If you have a working HA setup and the Dreame integration installed, the token is typically available from the integration’s stored config; exact steps depend on your HA version and the integration’s UI.
