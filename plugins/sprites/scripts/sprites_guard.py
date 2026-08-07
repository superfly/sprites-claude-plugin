#!/usr/bin/env python3
"""Ask for confirmation before risky Sprites MCP operations.

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
    name = tool_basename(str(payload.get("tool_name", "")))
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}
    serialized = json.dumps(tool_input, sort_keys=True).lower()

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
        command = next(
            (
                value
                for key in ("cmd", "command", "commandLine", "CommandLine")
                if isinstance((value := tool_input.get(key)), str)
            ),
            serialized,
        )
        if matches(command.lower(), CHECKPOINT_COMMANDS):
            ask(
                "This command can make broad persistent changes inside the Sprite. "
                "Create or verify a recent checkpoint before continuing."
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
