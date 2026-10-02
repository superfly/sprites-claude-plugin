#!/usr/bin/env python3
"""Dependency-free validation for the Claude plugin repository."""

from __future__ import annotations

import json
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SKIPPED = {".git", "__pycache__", ".pytest_cache", ".ruff_cache"}
TEXT_SUFFIXES = {".json", ".md", ".py", ".svg", ".ts", ".tsx", ".txt", ".yaml", ".yml"}
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HTML_SRC = re.compile(r"""<(?:img|source)\b[^>]*?\bsrc=["']([^"']+)["']""", re.IGNORECASE)


class DuplicateKeyError(ValueError):
    pass


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate key {key!r}")
        result[key] = value
    return result


def files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file() and not SKIPPED.intersection(path.relative_to(ROOT).parts)
    )


def local_markdown_target(raw: str) -> str | None:
    value = raw.strip()
    if value.startswith("<") and value.endswith(">"):
        value = value[1:-1]
    elif " " in value:
        value = value.split(" ", maxsplit=1)[0]
    value = urllib.parse.unquote(value.split("#", maxsplit=1)[0])
    if not value or value.startswith(("http://", "https://", "mailto:")):
        return None
    return value


def validate_skill(path: Path, text: str, errors: list[str]) -> None:
    relative = path.relative_to(ROOT)
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        errors.append(f"{relative}: missing YAML frontmatter")
        return
    frontmatter = text[4:].split("\n---\n", maxsplit=1)[0]
    name = re.search(r"^name:\s*([^\n]+)$", frontmatter, re.MULTILINE)
    description = re.search(r"^description:\s*([^\n]+)$", frontmatter, re.MULTILINE)
    if name is None or name.group(1).strip(' "\'') != path.parent.name:
        errors.append(f"{relative}: name must match directory {path.parent.name!r}")
    if description is None or not description.group(1).strip(' "\''):
        errors.append(f"{relative}: description must be non-empty")


def main() -> int:
    errors: list[str] = []
    repository_files = files()

    for path in repository_files:
        relative = path.relative_to(ROOT)
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            errors.append(f"{relative}: invalid UTF-8 ({exc})")
            continue
        if text and not text.endswith("\n"):
            errors.append(f"{relative}: missing final newline")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if line != line.rstrip():
                errors.append(f"{relative}:{line_number}: trailing whitespace")

        if path.suffix == ".json":
            try:
                json.loads(text, object_pairs_hook=unique_object)
            except (json.JSONDecodeError, DuplicateKeyError) as exc:
                errors.append(f"{relative}: invalid JSON ({exc})")
        elif path.suffix == ".svg":
            try:
                ET.fromstring(text)
            except ET.ParseError as exc:
                errors.append(f"{relative}: invalid SVG ({exc})")

        if path.suffix == ".md":
            for pattern in (MARKDOWN_LINK, HTML_SRC):
                for match in pattern.finditer(text):
                    target = local_markdown_target(match.group(1))
                    if target is not None and not (path.parent / target).resolve().exists():
                        errors.append(f"{relative}: broken local link {target!r}")
        if path.name == "SKILL.md":
            validate_skill(path, text, errors)

    guard = ROOT / "plugins/sprites/scripts/sprites_guard.py"
    if guard.exists() and not guard.stat().st_mode & 0o111:
        errors.append(f"{guard.relative_to(ROOT)}: hook script is not executable")

    if errors:
        print("Repository validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Validated {len(repository_files)} repository files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
