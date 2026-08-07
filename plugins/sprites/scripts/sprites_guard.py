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


DESTRUCTIVE_TOOLS = (
    r"destroy[_-]?sprite$",
    r"delete[_-]?sprite$",
    r"checkpoint[_-]?restore$",
    r"restore[_-]?(sprite|checkpoint)$",
    r"delete[_-]?checkpoint$",
    r"policy[_-]?network[_-]?(update|set)$",
    r"update[_-]?network[_-]?policy$",
    r"privilege[_-]?policy",
    r"resource[_-]?policy",
)

EXPOSURE_PATTERNS = (
    r"make[_-]?public",
    r'"?(is[_-]?)?public(_?url)?"?\s*:\s*(true|"true")',
    r'"?expose[_-]?(service|port|url)"?\s*:\s*(true|"true")',
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

    if matches(name, DESTRUCTIVE_TOOLS):
        ask(
            "This Sprites action may irreversibly destroy or rewind state, or "
            "change network/resource policy. Confirm the exact Sprite and scope."
        )
        return 0

    if matches(serialized, EXPOSURE_PATTERNS):
        ask(
            "This Sprites action appears to widen service exposure. Confirm the "
            "intended audience, authentication, Sprite, and port before continuing."
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
