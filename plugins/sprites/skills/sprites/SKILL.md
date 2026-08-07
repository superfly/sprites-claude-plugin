---
name: sprites
description: Use Sprites to create, list, inspect, operate, and clean up isolated cloud development environments from Claude Code.
---

# Sprites

Use this skill when the user asks Claude Code to work with Sprites, remote development environments, cloud sandboxes, or the Sprites MCP server.

Sprites are persistent, isolated Linux environments with their own filesystem, URL, services, checkpoints, and network policy. Claude Code runs outside the Sprite. Use the hosted Sprites MCP tools supplied by this plugin as the control plane.

## Golden path

Call the Sprites MCP tools directly. Do not use the local shell, curl, a nested Claude process, the Sprites CLI, `claude mcp add`, or a second MCP bridge for normal Sprites work.

If the tools are missing, explain that the plugin MCP server is not loaded and direct the user to `/plugin`, `/reload-plugins`, or a Claude Code restart. If a tool reports authorization is required, direct the user to `/mcp`, let Claude Code complete browser OAuth, and retry the original call once. Read [references/auth-and-setup.md](references/auth-and-setup.md) for diagnosis.

Keep local and remote contexts distinct:

- Claude Code workspace: the local repository and shell.
- Sprites MCP server: the API used to operate Sprites.
- Sprite filesystem: remote state reached only through Sprite-scoped MCP tools.

## Tool map

Use the smallest direct tool:

- List and create: `list_sprites`, `create_sprite`.
- Destroy: `destroy_sprite`, only after explicit delete/destroy/remove intent and the plugin confirmation prompt.
- One-off commands: `exec`; inspect or stop sessions with `exec_list` and `exec_kill`.
- Services: `service_list`, `service_get`, `service_create`, `service_start`, `service_stop`, and `service_logs`.
- Checkpoints: `checkpoint_create`, `checkpoint_list`, `checkpoint_get`, and `checkpoint_restore`.
- Network policy: `policy_network_get` and `policy_network_update`. Update replaces the entire rule set, so read the current policy first and send the merged rules.

Sprite-scoped tools take a `sprite` parameter naming the target; `create_sprite` and `destroy_sprite` take `name`. If the user did not specify a Sprite, call `list_sprites` and select an obvious match; ask only when more than one plausible target remains.

Sprite-level tools are generated from the Sprite environment API and can change between versions. Treat the tools actually offered in the session as authoritative: if a name above is missing, use the closest available tool rather than insisting on this list, and if an unfamiliar tool appears, read its schema instead of assuming it is unsupported.

## Operating principles

1. Discover read-only state first.
2. Reuse a Sprite when it clearly belongs to the same task; create one when asked or when isolation is important.
3. Create a checkpoint before package upgrades, migrations, bulk edits, service rewrites, network changes, or destructive work.
4. Use `exec` for short commands and services for long-running processes.
5. Verify with tests, health checks, status, or logs.
6. Report exact Sprite, checkpoint, service, and URL identifiers.

Restricted OAuth access normally requires a name prefix such as `mcp-`. Try a user-provided name as written. If the API returns a required prefix, retry once with that prefix when unambiguous and report the actual name. Full access removes the prefix but grants unrestricted access to every Sprite in the organization; do not present it as a risk-free prefix toggle.

## References

- Read [references/compute.md](references/compute.md) for builds, tests, or remote task environments.
- Read [references/files.md](references/files.md) before transferring or generating files inside a Sprite.
- Read [references/services.md](references/services.md) before creating or changing long-running services.
- Read [references/safety.md](references/safety.md) before destructive, checkpoint-restore, public-exposure, or network-policy work.
