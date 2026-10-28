![Fly.io](assets/fly-icon.svg)

# Fly

Manage Fly.io apps, Machines, volumes, app secrets, Managed Postgres, and Sprites from Claude Code through the hosted [Fly MCP](https://mcp.fly.io). The plugin includes workflow guidance, browser OAuth, confirmation hooks, and a read-only Sprite Inspector. No Fly or Sprites CLI is required.

## Install

From this repository's marketplace:

```text
/plugin marketplace add superfly/sprites-claude-plugin
/plugin install fly@sprites
/reload-plugins
```

The marketplace identifier is still `sprites`; `fly` is a separate plugin. Installing it does not rename, replace, disable, or migrate the Sprites plugin. Both can be installed, with independent connections and commands. When both are enabled, specify which plugin to use; the Fly workflows use the Fly connection and do not fall back to a different grant.

For development from the repository root:

```sh
claude --plugin-dir ./plugins/fly
```

## First use

Run `/fly:status`. If authorization is requested, open `/mcp`, select the plugin-provided `fly` server, and complete browser consent. Choose the organizations, existing apps, Managed Postgres, and Sprites permissions needed for your work. The status command reports the authorized resource bindings and restrictions before listing permitted resources. Product access is independent; Managed Postgres workflows run only when the tools are available and the grant permits them. Empty lists are valid; an ungranted product is reported as unavailable.

New tools do not expand your grant. The server enforces access, and Claude's tool approvals are an additional control. Tokens are handled by the client's OAuth flow; never paste tokens into chat or shell commands.

## Commands and workflows

- Ask Claude to inspect or operate an authorized Fly resource. The `fly` skill covers account context, apps, Machines, volumes, secrets, Managed Postgres, networking metadata, and Sprites.
- `/fly:status` checks authorization and lists resources without mutations or Sprite runtime reads.
- `/fly:smoke` checks authorized read paths. `/fly:smoke --create-sprite` additionally creates a disposable Sprite, writes and reads a small file, and runs a command. Cleanup needs explicit approval; `--keep` retains it.
- `/fly-sprites-inspector [name prefix]` browses Sprites over the Fly connection. Services, checkpoints, and logs load only on request and may wake a Sprite. **Use in chat** attaches the exact Sprite ID to the conversation.

Current Fly MCP operations cover existing apps, Machine creation and lifecycle, leases, memory and metadata, volumes and snapshots, secret updates, Managed Postgres clusters, plans, backups, databases, extensions and query diagnostics, and the full Sprites tool set including file operations. IP addresses and certificates are read-only. Managed Postgres tools do not delete resources, change users or passwords, or return passwords. See the [Managed Postgres workflow](skills/fly/references/postgres.md) for provisioning, completion checks, and handling sensitive query text. App creation, full deployment workflows, general Machine configuration updates, and organization administration are not currently offered. See the [tool reference](skills/fly/references/tools.md) and the live server schemas for the exact available operations.

## Runtime and data handling

The remote server is `https://mcp.fly.io`. Calls send the arguments needed for the requested operation to Fly.io and its product backends; those arguments can include commands, file content, and secret values when the user requests those operations. The plugin adds no separate telemetry service or credential store. It sends the fixed client attribution headers `Fly-Client-Agent: claude-code` and `Fly-Client-Interactive: false`, containing no user, machine, repository, or organization identifiers.

The Inspector stores selected Sprite metadata and explicitly requested logs in Claude Code's session state. Using **Use in chat** appends the selected resource identity to the conversation. Treat logs and command output as potentially sensitive, and avoid exposing configuration values or secrets in summaries.

### Inspector tool calls and local hooks

The Inspector calls five read-only tools through the declared `fly` MCP connection, directly from its UI handlers:

| Tool | When called | Arguments sent to Fly |
| --- | --- | --- |
| `open_sprite_inspector` | Opening the Inspector, searching, loading another page, or refreshing after focus returns | Name prefix and pagination token |
| `get_sprite_info` | Selecting a Sprite | Sprite name and ID |
| `service_list` and `checkpoint_list` | Requesting runtime details | Sprite name and ID |
| `service_logs` | Requesting a service's logs | Sprite name and ID, service name, 100-line limit, and `0s` streaming duration |

These calls do not require a model-generated tool request. The mod does not execute shell commands, read workspace files, or send data to another server. It reads its own session state to build these arguments. It displays tool results as data; returned text does not choose tools or executable code. Log display is limited to 10,000 characters. Opening an HTTPS link is a separate user action.

The mod's `session.start` handler registers `/fly-sprites-inspector` and resets pending UI requests after reload. Its `command.run` handler handles only that command, and its `ui.render` handler draws only the Inspector pane. **Use in chat** appends a resource identity and instructions to verify it through Fly before operating on it; it does not execute an operation.

The separate Python `PreToolUse` hook reads the proposed tool name and arguments from standard input, checks only the Fly plugin's Claude Code tool namespace, and emits an approval request for the operations described below. It does not run the proposed command, read workspace files, make network requests, or store the input. It adds no package installation step.

The Inspector requires Claude Code 2.1.287 or later. It falls back to a text listing when a pane cannot be drawn. The hook and mod run in Claude Code; they are not a substitute for server authorization on other Claude surfaces. The confirmation hook requires Python 3.

In Claude Code auto mode, Inspector button calls may need explicit permission. Allow only its read-only tools if desired:

```json
{
  "permissions": {
    "allow": [
      "mcp__plugin_fly_fly__open_sprite_inspector",
      "mcp__plugin_fly_fly__get_sprite_info",
      "mcp__plugin_fly_fly__service_list",
      "mcp__plugin_fly_fly__checkpoint_list",
      "mcp__plugin_fly_fly__service_logs"
    ]
  }
}
```

## Operational safeguards

The hook requests confirmation for destructive operations, billable Machine/volume creation or expansion, Machine lifecycle and configuration changes, Managed Postgres cluster creation/forking, backup and database creation, extension changes, leases, Machine exec, secret changes, Sprite file deletion/copy/move, stopping Sprite work, checkpoint restores, network-policy replacement, and services configured with an HTTP port. Recognized risky Sprite exec commands prompt for a checkpoint. Other calls retain Claude's normal permission policy; the hook is not a complete shell analyzer or authorization boundary.

Before making changes, identify the exact app, organization, Machine, volume, Managed Postgres cluster/database, or Sprite. After a write times out, inspect the result before retrying: the operation may already have completed. Sprite checkpoints do not back up Fly Machine root filesystems, volumes, or Managed Postgres data.

See [authentication](skills/fly/references/auth.md), [operational safety](skills/fly/references/safety.md), [Fly MCP documentation](https://mcp.fly.io), [Fly.io privacy policy](https://fly.io/legal/privacy-policy/), and [support](https://fly.io/support/).

## Validation

From the repository root, with Claude Code 2.1.287 or later:

```sh
python3 scripts/check_repository.py
python3 -m unittest discover -s tests -v
claude plugin validate ./plugins/fly --strict
claude plugin validate . --strict
claude plugin test ./plugins/fly
```

The Inspector tests use a stand-in MCP server. These checks do not establish live OAuth or resource-operation success; use an authorized test account for those checks before directory submission. This folder is a standalone plugin bundle for a separate submission. It does not migrate the existing Sprites listing.
