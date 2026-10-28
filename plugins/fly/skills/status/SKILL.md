---
name: status
description: Check Fly MCP authentication and authorized resource bindings, then list permitted apps, Managed Postgres clusters, and Sprites without mutations or runtime inspection.
disable-model-invocation: true
---

# Fly status

1. Confirm the Fly plugin's MCP tools are available. If missing, verify `fly@sprites` in `/plugin`, run `/reload-plugins`, and inspect `/mcp`. Do not add a second server or install a CLI.
2. Call `get_fly_context`. If authentication is required, direct the user to authenticate the plugin-provided `fly` server in `/mcp`, then retry once.
3. Report the authorized product bindings, per-resource scopes, and Sprite restrictions. Do not print tokens or sensitive values.
4. For authorized Fly app discovery, call `list_apps` with the concrete `org_slug` from the grant. When Managed Postgres listing is available and authorized, call `list_postgres_clusters` for each authorized organization using the live schema. For an authorized Sprites read binding, call `list_sprites`. Follow available continuation tokens, or clearly label the result as a partial page. Check only available and granted products; report the others as unavailable or not granted.
5. Report each check as successful, not granted, authentication required, or failed. An empty list is an authenticated success. A missing or ungranted product does not make the other product fail.

Do not fetch query text or sensitive Machine configuration, wake Sprites through runtime reads, or create, modify, stop, or delete resources. Keep this check on the Fly connection even if the Sprites-only plugin is also enabled.
