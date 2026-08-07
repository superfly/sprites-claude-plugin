# Authentication and setup

This plugin connects only to the hosted MCP server at `https://sprites.dev/mcp`. Claude Code handles browser OAuth. Do not install the Sprites CLI or register a second MCP server as a workaround.

## First run

1. Install and enable the plugin.
2. Run `/reload-plugins` or restart Claude Code.
3. Ask Claude to list Sprites, or run `/sprites:status`.
4. If prompted, open `/mcp`, select the plugin-provided `sprites` server, and complete browser OAuth for the correct Fly.io organization.
5. An empty list is success: authentication worked and the organization has no visible Sprites.

## Diagnose by failure class

### Tools missing

If no Sprites tools are available:

1. Confirm `sprites@sprites` is installed and enabled in `/plugin`.
2. Run `/reload-plugins` or restart Claude Code.
3. Inspect `/mcp` for the plugin-provided `sprites` server.
4. For local development, start Claude with `claude --plugin-dir ./plugins/sprites` from this repository.

Do not run `sprite login`, raw API calls, `claude mcp add`, or `npx mcp-remote` to hide a plugin loading problem.

### OAuth incomplete

If tools exist but calls return unauthorized, 401, or authorization required:

1. Open `/mcp` and authenticate the plugin-provided `sprites` server.
2. Select the correct organization and review the connector restrictions.
3. Retry the original MCP call once.

Do not ask the user to paste tokens into prompts or a shell.

### Prefix or create cap

Restricted tokens normally have a non-empty name prefix and may cap Sprite creation. The typical default prefix is `mcp-`, but do not assume it.

- Read the required prefix from an API error.
- If a bare requested name fails, retry once with `{prefix}{name}` when the mapping is clear.
- Report the actual name and remember the prefix during the session.
- If exact bare names are required, explain that choosing Full access during re-authentication removes the prefix and grants unrestricted organization-wide Sprite access.
- For a create cap, stay under it, destroy only with explicit approval, or ask the user to re-authenticate with an adjusted cap.

### Wrong organization or hidden Sprite

If listing works but an expected Sprite is absent, confirm the OAuth organization. Restricted tokens may only reveal names under their configured prefix. Always use exact names returned by `list_sprites`.
