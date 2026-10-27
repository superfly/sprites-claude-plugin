# Sprites through Fly MCP

Sprites are persistent remote Linux environments, separate from the local workspace and from Fly Machines. Always use this plugin's Fly MCP connection for this workflow.

## Select or create

Call `get_fly_context` and inspect the Sprites binding and restrictions. Use `list_sprites`, `search_sprite_mentions`, or `open_sprite_inspector` for discovery. Follow continuation tokens when more results are available; a partial page is not the full inventory. Use `get_sprite_info` for metadata without waking the Sprite.

The `/fly-sprites-inspector` pane's most recent selection names a `sprite` and `sprite_id`. Pass that ID alongside the name on Sprite-scoped tools so a deleted and recreated environment is rejected. Do not substitute another Sprite after a stale identity error; select again. Runtime reads, logs, and file operations may wake a Sprite, so request them deliberately.

Reuse an obvious task environment when suitable. For `create_sprite`, check the required prefix and creation cap first. Creation and destruction use `name`; Sprite-scoped tools use `sprite`. `destroy_sprite` requires explicit intent and confirmation of the exact target.

## Commands and files

Use `exec` for finite, non-interactive work; `exec_list` inspects sessions and `exec_kill` stops a selected session. Prefer `cmd` as an argv array, such as `["python3", "-c", "print('hello world')"]`. The string form is split on whitespace, so it is unsuitable for arguments with spaces or complex quoting. Read the live schema before constructing arguments.

Use the dedicated file tools rather than shell quoting tricks:

- `file_list` and `file_read` inspect directories and contents.
- `file_write` takes `sprite`, `path`, `workingDir`, and `content`. Use `encoding: "utf8"` for literal text or `"base64"` for encoded bytes without a data URL prefix; `mkdir` can create parents. Writes support up to 16 MiB of file content, subject to transport limits. Include `sprite_id` when known.
- `file_delete` takes explicit `recursive` and `asRoot` flags. Confirm the path and scope before deletion.
- `file_rename` and `file_copy` take `source` and `dest`; inspect the destination before overwriting. Use the current schema for required flags, including `workingDir` and `asRoot`.

`exec` returns the command's output but not its exit status; judge success from the output and say the status was not reported.

If `exec` or a file tool fails with "is not assigned to compute" while `get_sprite_info` shows the Sprite running, the server cannot yet route runtime calls to that Sprite's platform. Retrying will not help: report the Sprite name and ID rather than recreating or destroying it.

For repositories, cloning is usually simpler than transferring many individual files. Use an authorized private-code access method; never invent credentials. Create or verify a checkpoint before package upgrades, migrations, bulk changes, or overwriting important data.

## Services and logs

Use `service_list` and `service_get` before changing existing work. `service_create` creates or updates a service definition; use `service_start` and `service_stop` for lifecycle, and `service_logs` for bounded inspection. Prefer services over a forever-running `exec`.

Setting `http_port` exposes the service through the Sprite URL and triggers confirmation. Without it, the proxy may still route to port 8080: omitting `http_port` is not proof that a service is unreachable. Check existing routing and URL authentication. Never expose arbitrary files, environment dumps, credentials, admin/debug endpoints, or raw logs.

## Checkpoints and policy

Use `checkpoint_create`, `checkpoint_list`, and `checkpoint_get` to create and inspect filesystem checkpoints. Confirm completion before relying on a checkpoint. `checkpoint_restore` discards later filesystem changes and needs explicit confirmation. These snapshots are not backups of Fly Machine or volume state.

`policy_network_update` replaces the entire outbound policy. First call `policy_network_get`, merge the requested change into the current rules, and send the complete intended set. Never send only a new rule while assuming a merge.

After an operation, verify the relevant file, exit status, service state, checkpoint, or policy and report exact resource identifiers. If a mutation's outcome is unknown, inspect before retrying.
