---
name: status
description: Check whether the Sprites MCP integration is loaded and authenticated, then list visible Sprites without creating or destroying anything.
disable-model-invocation: true
---

# Sprites status

Perform a read-only health check:

1. Confirm the plugin-provided Sprites MCP tools are available.
2. If missing, tell the user to verify `sprites@sprites` in `/plugin`, run `/reload-plugins`, and inspect `/mcp`. Do not install the Sprites CLI or add another MCP server.
3. Call `list_sprites`.
4. If authorization is required, ask the user to authenticate the plugin-provided server in `/mcp`, then retry once.
5. Report success as a compact list of names, status, and URLs. An empty list is a successful authenticated result.

Do not create, mutate, stop, restore, or destroy anything.
