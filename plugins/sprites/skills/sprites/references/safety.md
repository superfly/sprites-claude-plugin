# Safety

Sprites are persistent environments. Files, packages, databases, services, checkpoints, and policies can outlive the Claude Code session.

## Confirm first

- Destroying a Sprite, which permanently deletes its state, services, checkpoints, and URL.
- Restoring a checkpoint, which discards filesystem state created after it.
- Deleting checkpoints.
- Widening network, privilege, or resource policy.
- Making a service public or adding a new internet-reachable surface.
- Broad destructive filesystem or database commands.

The plugin's `PreToolUse` hook requests confirmation for these operations and nudges checkpoint creation before risky `exec` commands. Still explain the exact Sprite and impact before issuing the tool call.

## Checkpoint first

Create a checkpoint before package upgrades, lockfile churn, database migrations, bulk file operations, service definition changes, network policy changes, and experiments with generated or untrusted code. Use a reason such as `before-node-upgrade` or `before-db-migration`.

## Secrets and exposure

- Prefer environment-variable injection to writing secrets into repository or web-root files.
- Do not hard-code credentials or copy tokens into prompts, shell history, or service definitions.
- Treat every Sprite URL as potentially internet-accessible.
- Do not expose debug endpoints, arbitrary files, environment variables, credentials, raw logs, or user data.
- Prefer restricted OAuth tokens and a task-specific name prefix. Full access is organization-wide access, not merely a naming preference.
