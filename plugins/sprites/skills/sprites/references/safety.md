# Safety

Sprites are persistent environments. Files, packages, databases, services, checkpoints, and policies can outlive the Claude Code session.

## Confirm first

- Destroying a Sprite, which permanently deletes its state, services, checkpoints, and URL.
- Restoring a checkpoint, which discards filesystem state created after it.
- Changing the outbound network policy with `policy_network_update`.
- Creating a service with an `http_port`, which puts it behind the Sprite's URL.
- Broad destructive filesystem or database commands.

The plugin's `PreToolUse` hook requests confirmation for these operations and nudges checkpoint creation before risky `exec` commands. Still explain the exact Sprite and impact before issuing the tool call.

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
