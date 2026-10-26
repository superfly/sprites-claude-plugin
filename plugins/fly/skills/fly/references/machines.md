# Apps and Machines

## Discover and inspect

Start with `get_fly_context`. Use `list_apps` with a concrete authorized `org_slug`, then `get_app` and `list_machines` for the intended app. Use the app names and Machine IDs returned by discovery, never inferred IDs.

`get_machine` returns lifecycle metadata without configuration. For troubleshooting, use `list_machine_events` and `wait_for_machine_state`. Only request `get_machine_configuration`, `list_machine_versions`, `list_machine_processes`, `get_machine_metadata`, or `get_machine_metadata_key` when their sensitive content is needed and the grant permits it. Environment, file, metadata, and process-argument values may contain secrets; summarize selectively.

`get_organization` and `get_launch_requirements` can explain eligibility or return browser handoffs. Let the user complete billing, SSO, and terms in the browser.

## Create and change runtime state

- `create_machine` creates a billable Machine in an existing authorized app. Inspect the supplied configuration, region, image, mounts, and exposure. It starts unless `skip_launch` is set. Mounts may require additional volume-write permission. Never retry a lost response without first looking for the created Machine.
- `start_machine`, `stop_machine`, `restart_machine`, `suspend_machine`, and `signal_machine` change running work. Inspect the current state and explain disruption. Stopping a Machine with `auto_destroy` configured can destroy it.
- `cordon_machine` removes a Machine from proxy routing; `uncordon_machine` restores routing. Neither is a substitute for stopping its processes.
- `get_machine_memory`, `set_machine_memory_limit`, and `reclaim_machine_memory` require the server's Machine-management grant. Memory changes can affect availability.
- `delete_machine` permanently destroys the ephemeral root filesystem. Confirm the exact app and Machine; never enable `force` implicitly. Attached volumes are separate resources.
- `delete_app` is broader than deleting one Machine. Inspect the app and its resources before explicit confirmation.

## Execute a command

`exec_machine_command` takes `app_name`, `machine_id`, and `body.command` as an argv array. For example, `body: {"command": ["uname", "-a"]}`. There is no implicit shell: use an explicit shell argv only when the task actually requires shell syntax. Read the current schema for container selection and timeout limits. Never serialize an argv array into a shell string and assume its quoting survives.

A command can read or mutate production data even if its name looks diagnostic. Confirm the operation and keep sensitive output out of chat. Sprite checkpoints cannot protect Machine or volume data.

## Leases and metadata

`get_machine_lease`, `create_machine_lease`, and `release_machine_lease` manage concurrency credentials. Keep returned lease nonces private, use the exact nonce when renewing or releasing, and do not release someone else's lease.

`update_machine_metadata` merges keys and requires `machine_version`. Null or empty values remove keys. A stale version is a conflict: reread the current state and reassess the intended change. Do not loop or overwrite blindly. `set_machine_metadata_key` and `delete_machine_metadata_key` operate on individual keys.

General Machine configuration updates and full deployment workflows are not currently exposed. Use only the tools actually offered in the session.
