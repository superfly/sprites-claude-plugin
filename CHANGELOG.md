# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This marketplace ships two independent plugins (`fly` and `sprites`). Installing
Fly does not rename, replace, or migrate Sprites; each keeps its own OAuth
connection and commands.

## [Fly 1.0.0] - 2026-10-28

Initial standalone Fly plugin for Claude Code. Connects to `https://mcp.fly.io`
with browser OAuth, workflow skills, confirmation hooks, and a read-only Sprite
Inspector. Manifest version `1.0.0`.

### Added

- Fly MCP workflows for authorized apps, Machines, volumes, and app secrets
- Read-only IP and certificate inspection
- Managed Postgres workflows and confirmation guards: cluster listing and
  inspection, plans, backups, databases, extensions, and query diagnostics;
  create/fork clusters, create backups and databases, enable extensions
  (deletion and user/password changes remain unsupported)
- PreToolUse confirmation for billable or disruptive changes, secret updates
  (without echoing values), Managed Postgres query-text reads, Postgres writes,
  and any write-shaped tool the guard has not reviewed
- Status and smoke skills (`/fly:status`, `/fly:smoke`) that respect Managed
  Postgres access and list only authorized resources
- Read-only Sprite Inspector mod (`/fly-sprites-inspector`) over the Fly
  connection, with directory icon and runtime disclosures for submission prep
- Guidance for misleading live MCP responses (for example lease conflicts on
  autostopped Machines, secret-tool errors that look like missing grants, and
  Sprite exec routing gaps)
- Independent marketplace entry alongside Sprites; commands and hooks stay
  scoped to the Fly connection

### Notes

- App creation, full deployment workflows, general Machine configuration
  updates, and organization administration are not currently offered
- Tokens stay in the client's OAuth flow; do not paste API tokens into chat
- The Inspector requires Claude Code 2.1.287 or later for the mod pane

## [Sprites 0.2.0] - 2026-10-02

### Added

- Read-only Sprite Inspector pane as a Claude Code mod (`/sprites-inspector`):
  browse Sprites, services, checkpoints, and recent logs; attach a selected
  Sprite (with `sprite_id`) to the conversation
- Inspector uses the plugin's own Sprites MCP connection; lists again on open
  and focus, does not poll, and prefers listing status over potentially stale
  `get_sprite_info` state
- Pagination and filter fixes so refreshes keep a stable view; checkpoint dates
  stay visible beside long comments
- The Inspector pane requires Claude Code 2.1.287 or later. Older clients load
  the rest of the plugin and skip the pane. CI pins that release for mod
  validation and Inspector tests; the previous pin was Claude Code 2.1.224

## [Sprites 0.1.0] - 2026-08-07

### Added

- Initial Claude Code Sprites plugin connecting to `https://sprites.dev/mcp`
- Browser OAuth, workflow skills, `/sprites:status` and `/sprites:smoke`
- PreToolUse confirmation hooks for destructive or risky remote operations
- Marketplace packaging under `superfly/sprites-claude-plugin`

### Changed

- Safety guard and skill docs aligned with the live Sprites MCP API (service
  exposure via `http_port` on `service_create`; drop patterns for tools that do
  not exist; correct checkpoint `comment` parameter; network policy replace
  semantics)
- Manifests and marketplace metadata tidied for strict `claude plugin validate`,
  with CI pinned to Claude Code 2.1.224
