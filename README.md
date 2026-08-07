# Sprites for Claude Code

Use [Sprites](https://sprites.dev) from Claude Code as persistent, isolated Linux development environments for builds, tests, sandboxes, previews, and long-running services.

This repository is a Claude Code plugin marketplace containing the `sprites` plugin. The plugin bundles the hosted Sprites MCP server, browser OAuth, workflow skills, explicit status and smoke-test commands, and confirmation hooks for risky remote operations. No Sprites CLI is required.

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
- Confirmation prompts before destroying or restoring state, changing policy, or widening service exposure.
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

Treat Sprite state as durable and every Sprite URL as potentially internet-accessible. Do not expose secrets, environment dumps, tokens, arbitrary files, admin/debug endpoints, or unfiltered logs over HTTP.

Destroying a Sprite is irreversible. Restoring a checkpoint discards newer filesystem state. The plugin asks for confirmation before these actions and before changes that widen access.

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
```

## Repository layout

```text
.claude-plugin/marketplace.json  Marketplace catalog
plugins/sprites/
  .claude-plugin/plugin.json     Plugin manifest
  .mcp.json                      Hosted MCP configuration
  hooks/hooks.json               Claude Code safety hook
  scripts/sprites_guard.py       Dependency-free hook implementation
  skills/                        Workflow skills and references
```
