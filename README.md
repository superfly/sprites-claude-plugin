# Sprites for Claude Code

Use [Sprites](https://sprites.dev) from Claude Code as persistent, isolated Linux development environments for builds, tests, sandboxes, previews, and long-running services.

This repository is a Claude Code plugin marketplace containing the `sprites` plugin. The plugin bundles the hosted Sprites MCP server, browser OAuth, workflow skills, explicit status and smoke-test commands, confirmation hooks for risky remote operations, and a read-only Sprite Inspector pane. No Sprites CLI is required.

## Install

Add this repository as a marketplace, then install the plugin:

```text
/plugin marketplace add superfly/sprites-claude-plugin
/plugin install sprites@sprites
/reload-plugins
```

For local development from this checkout:

```sh
claude --plugin-dir ./plugins/sprites
```

Or exercise the marketplace installation flow locally:

```text
/plugin marketplace add .
/plugin install sprites@sprites
/reload-plugins
```

## First use

1. Run `/sprites:status` or ask Claude to list your Sprites.
2. Open `/mcp` if Claude Code requests authorization.
3. Select the plugin-provided `sprites` server and complete browser OAuth for the intended Fly.io organization.
4. Review the connector's name-prefix, create-cap, and access settings. Restricted access with a non-empty prefix such as `mcp-` is the safer default.

An empty Sprite list means the integration is authenticated and working.

## What it provides

- Hosted MCP access at `https://sprites.dev/mcp`.
- Automatic workflow guidance for creating, inspecting, and operating Sprites.
- `/sprites:status` for a read-only integration and authentication check.
- `/sprites:smoke` for list → create → exec → approved cleanup.
- `/sprites-inspector` for a read-only pane to browse Sprites, their services, checkpoints, and logs, and to point Claude at one.
- Confirmation prompts before destroying a Sprite, restoring a checkpoint, replacing the network policy, or serving a new service on the Sprite's URL.
- Checkpoint prompts before risky remote package installs, migrations, or broad destructive commands.

With the plugin enabled, Claude can:

- List, create, and explicitly destroy Sprites.
- Run commands, tests, builds, and diagnostics remotely.
- Manage services, logs, checkpoints, and network policy.
- Keep risky or dependency-heavy work off the local machine.

## How it works

Claude Code remains on the local machine. The plugin's MCP server is the control plane for remote environments:

- Local workspace is not the Sprite filesystem.
- Remote one-off commands use Sprites MCP `exec` tools.
- Long-running processes use Sprites services.
- Reversible filesystem snapshots use checkpoints.
- Outbound access is governed by each Sprite's network policy.

There is no dedicated MCP file-upload tool. Prefer cloning a repository into the Sprite. For small generated files, the bundled skill documents a base64 transfer pattern that avoids fragile shell quoting.

## Sprite Inspector

`/sprites-inspector [name prefix]` opens a pane beside the conversation in the terminal and in the Code tab of the Claude desktop app. It is a [Claude Code mod](https://code.claude.com/docs/en/plugins/mods/overview), the counterpart of the Inspector the hosted server offers MCP App hosts, and calls the same read-only tools over the plugin's own MCP connection:

- Browse and filter Sprites by name prefix (`open_sprite_inspector`), 20 at a time.
- Select a Sprite to see its organization, creation date, status, and URL (`get_sprite_info`, which does not wake it).
- Load its services and checkpoints (`service_list`, `checkpoint_list`) and the last 100 lines of a service's logs (`service_logs`). These calls may wake a cold Sprite, so they run only when asked.
- **Use in chat** tells Claude which Sprite you mean, with its `sprite_id`, so later calls are checked against that exact Sprite rather than a deleted and recreated one with the same name.

The pane never changes a Sprite. It lists again when it is opened and when it regains focus, and does not poll.

Mods need Claude Code 2.1.287 or later. Older versions load the rest of the plugin and skip the pane. Where nothing can draw a pane, such as the VS Code extension's chat panel or `claude -p`, the command answers with a text listing instead.

In auto mode, Claude Code puts the pane's MCP calls to the auto-mode classifier, which has no request of yours to judge a button press by, and refuses them. Allow the pane's read-only tools in your settings to use it there:

```json
{
  "permissions": {
    "allow": [
      "mcp__plugin_sprites_sprites__open_sprite_inspector",
      "mcp__plugin_sprites_sprites__get_sprite_info",
      "mcp__plugin_sprites_sprites__service_list",
      "mcp__plugin_sprites_sprites__checkpoint_list",
      "mcp__plugin_sprites_sprites__service_logs"
    ]
  }
}
```

## OAuth restrictions

Restricted connector tokens use a non-empty Sprite-name prefix and may limit how many Sprites the connector can create. The usual default is `mcp-`, but Claude learns the actual rule from API responses rather than assuming it.

Choosing Full access removes the prefix restriction and grants unrestricted access to every Sprite in the organization. Use it only when organization-wide control is intentional.

## Client attribution

The plugin sends two fixed, privacy-safe [client-signals](https://github.com/superfly/client-signals) headers on requests to the hosted MCP server:

```text
Fly-Client-Agent: claude-code
Fly-Client-Interactive: false
```

`claude-code` is the canonical client-signals marker. `Fly-Client-Interactive` is the instrumentation sentinel required before the marker is considered; the fixed `false` value reflects that a static MCP manifest cannot measure terminal attachment per request. The headers contain nothing user-, machine-, organization-, or repository-specific. They are advisory aggregate analytics only and are never used for authentication, authorization, gating, or rate limiting.

## Safety

Treat Sprite state as durable. A Sprite URL requires authentication by default, and none of the plugin's MCP tools can make it public — that is a separate `--url-auth public` change made outside the plugin. Still, anything a service serves on its `http_port` is reachable at that URL, so do not expose secrets, environment dumps, tokens, arbitrary files, admin/debug endpoints, or unfiltered logs over HTTP.

Destroying a Sprite is irreversible. Restoring a checkpoint discards newer filesystem state. `policy_network_update` replaces the whole outbound rule set rather than merging, so the plugin's skill tells Claude to read the current policy and send merged rules. The plugin asks for confirmation before each of these and before a service is given an `http_port`.

## Troubleshooting

If Sprites tools are missing:

1. Confirm `sprites@sprites` is installed and enabled in `/plugin`.
2. Run `/reload-plugins` or restart Claude Code.
3. Open `/mcp` and confirm the plugin-provided `sprites` server is present.

If the server is present but unauthorized, authenticate it in `/mcp` and retry the original request. Do not install the Sprites CLI, run `sprite login`, add a second MCP server, or paste access tokens into the shell as a workaround.

For development-time validation:

```sh
python3 scripts/check_repository.py
python3 -m unittest discover -s tests -v
claude plugin validate ./plugins/sprites
claude plugin validate .
claude plugin test ./plugins/sprites
```

`claude plugin test` runs the Sprite Inspector's tests against a stand-in for the MCP server, so it needs no network or sign-in.

## Repository layout

```text
.claude-plugin/marketplace.json  Marketplace catalog
plugins/sprites/
  .claude-plugin/plugin.json     Plugin manifest
  .mcp.json                      Hosted MCP configuration
  hooks/hooks.json               Claude Code safety hook and mod registration
  hooks/register.tsx             Sprite Inspector mod
  types/index.d.ts               The mod's state contract
  tests/                         Sprite Inspector mod tests
  scripts/sprites_guard.py       Dependency-free hook implementation
  skills/                        Workflow skills and references
```
