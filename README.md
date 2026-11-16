# Fly.io plugins for Claude Code

This marketplace contains two independent plugins:

| Plugin | Install | MCP server | Documentation |
| --- | --- | --- | --- |
| Fly | `/plugin install fly@sprites` | `https://mcp.fly.io` | [Fly plugin](plugins/fly/README.md) |
| Sprites | `/plugin install sprites@sprites` | `https://sprites.dev/mcp` | [Sprites plugin](plugins/sprites/README.md) |

Add the marketplace with `/plugin marketplace add superfly/sprites-claude-plugin`, then install the plugin you want. The marketplace keeps its `sprites` identifier. The Fly plugin is a separate package with its own OAuth connection and `/fly:status` and `/fly:smoke` commands. It covers existing Fly apps, Machines, volumes, secrets, Managed Postgres, and Sprites. Both plugins can be installed; nothing renames, replaces, or migrates an existing Sprites installation.

The Fly plugin source is under `plugins/fly/` for a separate directory submission. Adding it here does not publish it to Anthropic's directory. See its [README](plugins/fly/README.md) for supported operations, setup, and validation.

The following documentation describes the Sprites-only plugin.

## Sprites for Claude Code

Use [Sprites](https://sprites.dev) from Claude Code as persistent, isolated Linux development environments for builds, tests, sandboxes, previews, and long-running services.

This repository is a Claude Code plugin marketplace containing the `sprites` plugin. The plugin bundles the hosted Sprites MCP server, browser OAuth, workflow skills, and explicit status and smoke-test commands. It ships no hooks or other executable code. No Sprites CLI is required.

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
- Skill guidance that has Claude ask you before destroying a Sprite, restoring a checkpoint, replacing the network policy, or serving a new service on the Sprite's URL, and create a checkpoint before risky package installs, migrations, or broad destructive commands.

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

Treat Sprite state as durable. A Sprite URL requires authentication by default, and none of the plugin's MCP tools can make it public — that is a separate `--url-auth public` change made outside the plugin. Still, anything a service serves on its `http_port` is reachable at that URL, so do not expose secrets, environment dumps, tokens, arbitrary files, admin/debug endpoints, or unfiltered logs over HTTP.

Destroying a Sprite is irreversible. Restoring a checkpoint discards newer filesystem state. `policy_network_update` replaces the whole outbound rule set rather than merging, so the plugin's skill tells Claude to read the current policy and send merged rules. The plugin's skill tells Claude to ask you before each of these and before giving a service an `http_port`. That is guidance to Claude, not an enforced prompt; Claude Code's tool approvals and the server's authorization still apply.

## Troubleshooting

If Sprites tools are missing:

1. Confirm `sprites@sprites` is installed and enabled in `/plugin`.
2. Run `/reload-plugins` or restart Claude Code.
3. Open `/mcp` and confirm the plugin-provided `sprites` server is present.

If the server is present but unauthorized, authenticate it in `/mcp` and retry the original request. Do not install the Sprites CLI, run `sprite login`, add a second MCP server, or paste access tokens into the shell as a workaround.

For development-time validation, with Claude Code 2.1.299 or later:

```sh
python3 scripts/check_repository.py
python3 -m unittest discover -s tests -v
claude plugin validate ./plugins/sprites --strict
claude plugin validate ./plugins/sprites --profile directory
claude plugin validate . --strict
```

## Repository layout

```text
.claude-plugin/marketplace.json  Marketplace catalog
plugins/sprites/
  .claude-plugin/plugin.json     Plugin manifest
  .mcp.json                      Hosted MCP configuration
  skills/                        Workflow skills and references
```
