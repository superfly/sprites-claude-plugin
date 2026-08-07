from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/sprites"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


class ClaudePluginRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.marketplace = load_json(ROOT / ".claude-plugin/marketplace.json")
        self.manifest = load_json(PLUGIN / ".claude-plugin/plugin.json")
        self.mcp = load_json(PLUGIN / ".mcp.json")

    def test_marketplace_points_to_plugin(self) -> None:
        entry = self.marketplace["plugins"][0]
        self.assertEqual(self.marketplace["name"], "sprites")
        self.assertEqual(entry["name"], "sprites")
        self.assertEqual((ROOT / entry["source"]).resolve(), PLUGIN.resolve())

    def test_manifest_identity(self) -> None:
        self.assertEqual(self.manifest["name"], "sprites")
        self.assertEqual(self.manifest["displayName"], "Sprites")
        self.assertEqual(
            self.manifest["repository"],
            "https://github.com/superfly/sprites-claude-plugin",
        )

    def test_expected_skills_are_packaged(self) -> None:
        expected = {"smoke", "sprites", "status"}
        actual = {path.parent.name for path in (PLUGIN / "skills").glob("*/SKILL.md")}
        self.assertEqual(actual, expected)

    def test_mcp_server_and_attribution(self) -> None:
        server = self.mcp["mcpServers"]["sprites"]
        parsed = urlparse(server["url"])
        self.assertEqual(server["type"], "http")
        self.assertEqual((parsed.scheme, parsed.netloc, parsed.path), ("https", "sprites.dev", "/mcp"))
        self.assertEqual(
            server["headers"],
            {
                "Fly-Client-Interactive": "false",
                "Fly-Client-Agent": "claude-code",
            },
        )

    def test_hook_targets_plugin_scoped_server(self) -> None:
        hooks = load_json(PLUGIN / "hooks/hooks.json")
        matcher = hooks["hooks"]["PreToolUse"][0]["matcher"]
        self.assertIn("plugin_sprites_sprites", matcher)


class SpritesGuardTests(unittest.TestCase):
    guard = PLUGIN / "scripts/sprites_guard.py"

    def run_guard(self, tool: str, tool_input: dict) -> dict | None:
        result = subprocess.run(
            [str(self.guard)],
            input=json.dumps({"tool_name": tool, "tool_input": tool_input}),
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(result.stdout) if result.stdout.strip() else None

    def assert_asks(self, result: dict | None) -> None:
        self.assertIsNotNone(result)
        output = result["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "PreToolUse")
        self.assertEqual(output["permissionDecision"], "ask")

    def test_read_only_call_is_unchanged(self) -> None:
        result = self.run_guard(
            "mcp__plugin_sprites_sprites__list_sprites",
            {},
        )
        self.assertIsNone(result)

    def test_destroy_requires_confirmation(self) -> None:
        result = self.run_guard(
            "mcp__plugin_sprites_sprites__destroy_sprite",
            {"sprite": "mcp-test"},
        )
        self.assert_asks(result)

    def test_package_install_requires_checkpoint_confirmation(self) -> None:
        result = self.run_guard(
            "mcp__plugin_sprites_sprites__exec",
            {"sprite": "mcp-test", "cmd": "npm install"},
        )
        self.assert_asks(result)

    def test_public_service_requires_confirmation(self) -> None:
        result = self.run_guard(
            "mcp__plugin_sprites_sprites__service_create",
            {"sprite": "mcp-test", "name": "web", "public_url": True},
        )
        self.assert_asks(result)


if __name__ == "__main__":
    unittest.main()
