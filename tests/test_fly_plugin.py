from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/fly"
SAFETY = PLUGIN / "skills/fly/references/safety.md"
TOOLS = PLUGIN / "skills/fly/references/tools.md"
# Writes the safety reference leaves to Claude Code's normal permission policy.
# `exec` and `service_create` are confirmed only for some inputs.
REVIEWED_WRITES = {"checkpoint_create", "create_sprite", "create_volume_snapshot", "file_write",
                   "service_create", "service_start", "exec"}
READ_TOOL = re.compile(r"^(get|list|search|open|wait)_|_(get|list|read|logs|info)$")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def confirmation_table() -> set[str]:
    """Tool names in the Tools column of the safety reference's confirmation table."""
    text = SAFETY.read_text()
    section = text.split("## Confirm before these calls", maxsplit=1)[1].split("\n## ", maxsplit=1)[0]
    names: set[str] = set()
    for row in re.findall(r"^\|([^\n]+)\|$", section, re.MULTILINE):
        cells = [cell.strip() for cell in row.split("|")]
        if len(cells) >= 2:
            names.update(re.findall(r"`([a-z_]+)`", cells[1]))
    return names


class FlyPackagingTests(unittest.TestCase):
    def test_plugins_coexist_without_migration(self) -> None:
        marketplace = load_json(ROOT / ".claude-plugin/marketplace.json")
        self.assertEqual(marketplace["name"], "sprites")
        self.assertNotIn("renames", marketplace)
        self.assertNotIn("forceRemoveDeletedPlugins", marketplace)
        entries = {entry["name"]: entry for entry in marketplace["plugins"]}
        self.assertEqual(set(entries), {"sprites", "fly"})
        for name, entry in entries.items():
            with self.subTest(plugin=name):
                folder = ROOT / entry["source"]
                self.assertEqual(folder.resolve(), (ROOT / "plugins" / name).resolve())
                manifest = load_json(folder / ".claude-plugin/plugin.json")
                self.assertEqual(manifest["name"], name)
                self.assertNotIn("dependencies", manifest)
        self.assertEqual(load_json(PLUGIN / ".claude-plugin/plugin.json")["displayName"], "Fly.io")

    def test_connections_remain_independent(self) -> None:
        for name, url in [("fly", "https://mcp.fly.io"), ("sprites", "https://sprites.dev/mcp")]:
            with self.subTest(plugin=name):
                servers = load_json(ROOT / "plugins" / name / ".mcp.json")["mcpServers"]
                self.assertEqual(set(servers), {name})
                self.assertEqual(servers[name]["url"], url)
                self.assertEqual(servers[name]["type"], "http")
                self.assertEqual(servers[name]["headers"], {
                    "Fly-Client-Interactive": "false",
                    "Fly-Client-Agent": "claude-code",
                })

    def test_bundle_is_self_contained(self) -> None:
        for required in ["README.md", "LICENSE", ".claude-plugin/icon.png",
                         "skills/fly/SKILL.md", "skills/status/SKILL.md", "skills/smoke/SKILL.md"]:
            self.assertTrue((PLUGIN / required).is_file(), required)
        for path in PLUGIN.rglob("*"):
            self.assertFalse(path.is_symlink(), str(path))
            if path.suffix in {".md", ".json"}:
                self.assertNotIn("../../sprites", path.read_text())

    def test_ships_no_hooks_or_mods(self) -> None:
        # The directory accepts hooks and mods only from Verified organizations.
        manifest = load_json(PLUGIN / ".claude-plugin/plugin.json")
        for field in ["hooks", "types", "commands", "agents", "monitors"]:
            self.assertNotIn(field, manifest)
        for folder in ["hooks", "scripts", "types", "tests", "commands", "agents"]:
            self.assertFalse((PLUGIN / folder).exists(), folder)
        tracked = [path for path in PLUGIN.rglob("*")
                   if path.is_file() and ".claude-plugin/types" not in path.as_posix()
                   and path.name != "tsconfig.json"]
        # The directory accepts only Markdown, text, JSON, YAML, and PNG, JPEG, GIF,
        # WebP, or ICO images from organizations that are not Verified.
        allowed = {".md", ".txt", ".json", ".yaml", ".yml", ".png", ".jpg", ".jpeg", ".gif",
                   ".webp", ".ico"}
        for path in tracked:
            with self.subTest(path=str(path.relative_to(PLUGIN))):
                self.assertTrue(path.suffix.lower() in allowed or path.name == "LICENSE")
                self.assertFalse(path.read_bytes().startswith(b"#!"))

    def test_manifest_meets_directory_requirements(self) -> None:
        manifest = load_json(PLUGIN / ".claude-plugin/plugin.json")
        self.assertEqual(manifest["privacyPolicyUrl"], "https://fly.io/legal/privacy-policy/")
        self.assertEqual(manifest["termsOfServiceUrl"], "https://fly.io/legal/terms-of-service/")

    def test_no_docs_point_at_removed_features(self) -> None:
        for path in [*PLUGIN.rglob("*.md"), ROOT / "README.md"]:
            text = path.read_text()
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertNotIn("/fly-sprites-inspector", text)
                self.assertNotIn("fly_guard", text)


class FlyConfirmationGuidanceTests(unittest.TestCase):
    def test_documented_writes_need_confirmation_unless_reviewed(self) -> None:
        documented = set(re.findall(r"^\| `([a-z_]+)` \|", TOOLS.read_text(), re.MULTILINE))
        confirmed = confirmation_table()
        self.assertLessEqual(REVIEWED_WRITES, documented)
        # Every name in the Tools column is a real tool, apart from the argument it qualifies.
        self.assertLessEqual(confirmed - {"http_port"}, documented)
        for name in sorted(documented - REVIEWED_WRITES):
            with self.subTest(tool=name):
                if not READ_TOOL.search(name):
                    self.assertIn(name, confirmed)

    def test_former_hook_coverage_is_kept(self) -> None:
        confirmed = confirmation_table()
        for name in ["delete_app", "delete_machine", "delete_volume", "create_machine",
                     "create_volume", "extend_volume", "exec_machine_command", "set_app_secret",
                     "update_app_secrets", "delete_app_secret", "create_postgres_cluster",
                     "fork_postgres_cluster", "create_postgres_backup", "create_postgres_database",
                     "enable_postgres_extension", "list_postgres_active_queries",
                     "list_postgres_slow_queries", "destroy_sprite", "checkpoint_restore",
                     "policy_network_update", "file_delete", "file_rename", "file_copy",
                     "exec_kill", "service_stop", "service_create", "exec"]:
            with self.subTest(tool=name):
                self.assertIn(name, confirmed)

    def test_skills_point_at_the_confirmation_list(self) -> None:
        skill = (PLUGIN / "skills/fly/SKILL.md").read_text()
        self.assertIn("references/safety.md#confirm-before-these-calls", skill)


if __name__ == "__main__":
    unittest.main()
