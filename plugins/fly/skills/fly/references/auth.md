# Authentication and resource scope

Use only the plugin-provided `fly` HTTP MCP server at `https://mcp.fly.io`. Claude Code handles browser OAuth.

## First use and missing tools

1. Verify `fly@sprites` is installed and enabled in `/plugin`.
2. Run `/reload-plugins` or restart Claude Code.
3. Inspect `/mcp` and authenticate the plugin-provided `fly` server when requested.
4. Complete browser consent for the intended organizations, existing apps, and Sprites permissions. Organization SSO may require browser verification.
5. Call `get_fly_context` and report the authorized bindings and restrictions.

For local development, load `./plugins/fly` with `claude --plugin-dir` from the repository root. The marketplace retains the historical `sprites` identifier; that is not the plugin's server name.

## Authorization failures

If a call is rejected before execution because authentication is required, direct the user to `/mcp` to complete sign-in and retry once. For a timed-out mutation, inspect state before any retry. If access was revoked, complete fresh consent rather than copying an old token.

If a resource is missing or a tool is denied, inspect `get_fly_context`. Listing organizations does not grant access to their apps. A grant may cover Fly apps without Sprites, Sprites without Fly apps, or both. An ungranted product is not a broken connection. Do not switch to the Sprites-only connection to work around a Fly grant restriction.

## Sprite restrictions

Read `name_prefix`, `max_sprites_total`, and any label restrictions from the Sprites binding before creation. Use only permitted names and check visible existing Sprites before creating another. Do not assume `mcp-` or infer restrictions from all tools being visible. If a user-specified name needs a prefix, explain the required actual name; do not silently change an exact-name requirement.

Never delete someone else's Sprite to make room under a creation cap. Ask for an appropriate grant change only when necessary for the user's requested work. Broader access grants more resource control, not just shorter names.
