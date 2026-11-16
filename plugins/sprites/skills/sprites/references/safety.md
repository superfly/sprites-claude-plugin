# Safety

Sprites are persistent environments. Files, packages, databases, services, checkpoints, and policies can outlive the Claude Code session.

## Confirm first

Before each of these calls, tell the user the exact Sprite and the impact, then wait for their explicit approval in the conversation. A request that already names the operation and the exact Sprite counts as approval for that call only; it does not cover a later call or a different Sprite.

- `destroy_sprite`, which permanently deletes the Sprite's state, services, checkpoints, and URL.
- `checkpoint_restore`, which discards filesystem state created after the checkpoint.
- `policy_network_update`, which replaces the whole outbound network policy.
- `service_create` with an `http_port`, which puts the service behind the Sprite's URL.
- `exec` running broad destructive filesystem or database commands, such as `rm -rf`, `DROP DATABASE`, `TRUNCATE TABLE`, or a bulk `DELETE FROM`.

Before `exec` runs package installs or upgrades (`npm`, `pnpm`, `yarn`, `pip`, `uv`, `apt`, `dnf`, `apk`) or database migrations, create or verify a recent checkpoint.

These are instructions to Claude, not an enforced control. Claude Code's tool approvals and the server's authorization still apply. Reason about the actual operation: a different shell command can have the same effect as one listed here.

## Checkpoint first

Create a checkpoint before package upgrades, lockfile churn, database migrations, bulk file operations, service definition changes, network policy changes, and experiments with generated or untrusted code. `checkpoint_create` takes an optional `comment`; use it for a recognizable label such as `before-node-upgrade` or `before-db-migration`.

## Network policy is replaced, not merged

Outbound access is unrestricted by default. `policy_network_update` takes the complete `rules` array and replaces whatever is in force, so read the current policy with `policy_network_get` first, merge the change into those rules, and send the full set. Sending only the new rule silently drops every existing one.

## Secrets and exposure

- Prefer environment-variable injection to writing secrets into repository or web-root files.
- Do not hard-code credentials or copy tokens into prompts, shell history, or service definitions.
- A Sprite URL requires authentication by default, and no MCP tool in this plugin can make it public; that is a deliberate `--url-auth public` change made outside the plugin. Do not assume a URL is private if the user may have flipped it.
- Anything a service serves on its `http_port` is reachable at that URL. Do not expose debug endpoints, arbitrary files, environment variables, credentials, raw logs, or user data.
- Prefer restricted OAuth tokens and a task-specific name prefix. Full access is organization-wide access, not merely a naming preference.
