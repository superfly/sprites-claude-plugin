# Volumes and snapshots

Use `get_fly_context`, then `list_volumes` and `get_volume` for the authorized app. Check the exact volume ID, region, attachment, and state before making changes. Listing hides deletion-state volumes by default; with `summary: true`, byte and block statistics are omitted, not zero.

- `create_volume` creates billable storage. Confirm size, region, and configuration. This tool does not restore or fork another volume; those require separate source-resource authorization.
- `update_volume` changes the supported volume settings. Read current state and preserve unrelated settings.
- `extend_volume` increases capacity and charges; volumes cannot be shrunk. Confirm the final size. Its result, like `create_volume`'s, reports zero block and byte statistics; read `get_volume` for real usage.
- `create_volume_snapshot` schedules a snapshot for an attached, ready volume. Creation is asynchronous and may return no snapshot ID. Follow with `list_volume_snapshots` to identify the snapshot and verify completion before relying on it. While its `status` is `running`, `created_at` reads `0001-01-01T00:00:00Z` and `size` and `volume_size` are placeholders; wait for `created` before reporting them.
- `delete_volume` permanently deletes persistent data. Verify attachments and detach through an authorized supported workflow before deletion. If the required detach operation is unavailable, explain the prerequisite instead of inventing an MCP tool or forcing deletion.

Do not treat an accepted snapshot request as a completed backup. A Sprite checkpoint is unrelated to a Fly volume snapshot. For uncertain writes, inspect state before retrying, especially creation and extension.
