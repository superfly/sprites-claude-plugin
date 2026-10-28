#!/usr/bin/env python3
"""Ask for confirmation before risky operations on the Fly plugin's MCP server.

Claude Code passes hook input as JSON on stdin. Safe calls produce no output,
which leaves Claude's normal permission policy unchanged. Risky calls return a
PreToolUse `ask` decision so the user sees the exact tool call before it runs.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any


# Keyed on the bare tool name the server actually exposes. Sprite-level tools are
# generated from the Sprite environment API and can change between versions, so the
# patterns tolerate separator drift but do not invent tools that have never existed.
DESTRUCTIVE_TOOLS = (
    (
        r"^(create_postgres_cluster|fork_postgres_cluster)$",
        "This creates a billable Managed Postgres cluster. Confirm the organization, "
        "plan, configuration, and source cluster for a fork. Provisioning is asynchronous; "
        "verify readiness before further writes. No MPG deletion tool is available for cleanup.",
    ),
    (
        r"^create_postgres_backup$",
        "Confirm the Managed Postgres cluster and backup request. Check for an existing "
        "backup in progress, and verify completion before relying on the backup.",
    ),
    (
        r"^(create_postgres_database|enable_postgres_extension)$",
        "This changes Managed Postgres database state. Confirm the ready cluster, "
        "database, and requested database creation or extension. Check current state "
        "before retrying an uncertain result; these tools do not provide deletion or rollback.",
    ),
    (
        r"^delete_app$",
        "Deleting a Fly app permanently removes the app and can disrupt or delete "
        "its resources. Inspect it first and confirm the exact app and organization.",
    ),
    (
        r"^delete_machine$",
        "Deleting a Machine destroys its ephemeral root filesystem. Attached "
        "volumes are separate resources. Confirm the app, Machine, and force setting.",
    ),
    (
        r"^delete_volume$",
        "Deleting a volume permanently destroys its data. Verify its attachments "
        "and any completed snapshot, then confirm the exact app and volume.",
    ),
    (
        r"^(create_machine|create_volume|extend_volume)$",
        "This operation creates or increases billable Fly resources. Confirm the "
        "app, region, configuration, and capacity. Volume growth cannot be undone.",
    ),
    (
        r"^(start_machine|stop_machine|restart_machine|suspend_machine|signal_machine|"
        r"cordon_machine|uncordon_machine|set_machine_memory_limit|reclaim_machine_memory)$",
        "This changes a Machine's runtime or traffic routing and may interrupt "
        "application work. Confirm the exact app, Machine, and intended effect. "
        "Stopping a Machine can also trigger its existing auto_destroy setting.",
    ),
    (
        r"^(update_machine_metadata|set_machine_metadata_key|delete_machine_metadata_key|update_volume)$",
        "Confirm the target app and resource and the intended configuration change. "
        "Check current state and preserve unrelated settings.",
    ),
    (
        r"^(create_machine_lease|release_machine_lease)$",
        "This changes a Machine lease used for concurrency control. Confirm the "
        "app and Machine, and keep the lease nonce private.",
    ),
    (
        r"^(set_app_secret|update_app_secrets|delete_app_secret)$",
        "Confirm the app and secret names being set or removed without repeating "
        "secret values. Null entries in a bulk update delete secrets. Changes may "
        "affect application behavior; inspect metadata afterward.",
    ),
    (
        r"^exec_machine_command$",
        "This command runs on a Fly Machine and can read or change application "
        "data. Confirm the app, Machine, and argv. Keep sensitive output private; "
        "Sprite checkpoints do not protect Machine or volume data.",
    ),
    (
        r"^file_delete$",
        "Deleting a Sprite file or directory can discard persistent data. Confirm "
        "the Sprite, path, recursive and root flags, and any required checkpoint.",
    ),
    (
        r"^(file_rename|file_copy)$",
        "Confirm the Sprite, source, and destination, including whether an existing "
        "destination may be overwritten. Checkpoint important data first.",
    ),
    (
        r"^(exec_kill|service_stop)$",
        "This interrupts running work in a Sprite. Confirm the Sprite and the "
        "specific session or service before stopping it.",
    ),
    (
        r"^destroy[_-]?sprite$",
        "Destroying a Sprite permanently deletes its filesystem, services, "
        "checkpoints, and URL. There is no undo. Confirm the exact Sprite name.",
    ),
    (
        r"^checkpoint[_-]?restore$",
        "Restoring a checkpoint discards every filesystem change made after it. "
        "Confirm the Sprite and the checkpoint id.",
    ),
    (
        r"^policy[_-]?network[_-]?update$",
        "Updating the network policy replaces the entire rule set rather than "
        "merging into it. Confirm that these rules are the complete intended "
        "policy, read back from policy_network_get.",
    ),
)

CHECKPOINT_COMMANDS = (
    r"\brm\s+-rf\b",
    r"\bdrop\s+database\b",
    r"\btruncate\s+table\b",
    r"\bdelete\s+from\b",
    r"\b(db:)?migrate\b",
    r"\bprisma\s+migrate\b",
    r"\balembic\s+upgrade\b",
    r"\brails\s+db:migrate\b",
    r"\bnpm\s+(install|update|audit\s+fix)\b",
    r"\bpnpm\s+(install|update|add|up)\b",
    r"\byarn\s+(install|upgrade|add)\b",
    r"\bpip\s+install\b",
    r"\buv\s+(pip\s+)?install\b",
    r"\bapt(-get)?\s+(install|upgrade|dist-upgrade)\b",
    r"\bdnf\s+(install|upgrade)\b",
    r"\bapk\s+add\b",
)


def read_payload() -> dict[str, Any]:
    try:
        raw = sys.stdin.read()
        value = json.loads(raw) if raw.strip() else {}
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def matches(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def destructive_reason(name: str) -> str | None:
    for pattern, reason in DESTRUCTIVE_TOOLS:
        if re.search(pattern, name, re.IGNORECASE):
            return reason
    return None


def tool_basename(name: str) -> str:
    return name.rsplit("__", maxsplit=1)[-1].lower()


def command_text(tool_input: dict[str, Any]) -> str:
    """Support both current argv and legacy string Sprite exec inputs."""
    for key in ("cmd", "command", "commandLine", "CommandLine"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, list) and all(isinstance(arg, str) for arg in value):
            return " ".join(value)
    return ""


def ask(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def main() -> int:
    payload = read_payload()
    tool_name = str(payload.get("tool_name", ""))
    # Both plugins can be installed. Never apply Fly's policy to another server.
    if not tool_name.startswith("mcp__plugin_fly_fly__"):
        return 0
    name = tool_basename(tool_name)
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}

    reason = destructive_reason(name)
    if reason is not None:
        ask(reason)
        return 0

    # `http_port` is what puts a service behind the Sprite's URL. Without it the
    # proxy keeps routing to port 8080, so the port is the exposure signal.
    if name == "service_create" and tool_input.get("http_port") not in (None, ""):
        ask(
            "This service will answer on the Sprite's URL because http_port is "
            f"set to {tool_input.get('http_port')!r}. The URL requires "
            "authentication unless the Sprite was configured otherwise. Confirm "
            "the Sprite and that the service exposes nothing sensitive."
        )
        return 0

    if name == "exec":
        command = command_text(tool_input)
        if matches(command.lower(), CHECKPOINT_COMMANDS):
            ask(
                "This command can make broad persistent changes inside the Sprite. "
                "Create or verify a recent checkpoint before continuing."
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
