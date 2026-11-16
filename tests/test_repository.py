from __future__ import annotations

import json
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

    def test_manifest_meets_directory_requirements(self) -> None:
        self.assertEqual(self.manifest["privacyPolicyUrl"], "https://fly.io/legal/privacy-policy/")
        self.assertEqual(self.manifest["termsOfServiceUrl"], "https://fly.io/legal/terms-of-service/")

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

    def test_ships_no_hooks_or_mods(self) -> None:
        # The directory accepts hooks and mods only from Verified organizations.
        for field in ["hooks", "types", "commands", "agents", "monitors"]:
            self.assertNotIn(field, self.manifest)
        for folder in ["hooks", "scripts", "types", "tests", "commands", "agents"]:
            self.assertFalse((PLUGIN / folder).exists(), folder)
        for path in PLUGIN.rglob("*"):
            if path.is_file():
                self.assertNotIn(path.suffix, {".py", ".js", ".mjs", ".ts", ".tsx", ".sh"}, str(path))

    def test_no_docs_point_at_removed_features(self) -> None:
        for path in [*PLUGIN.rglob("*.md"), ROOT / "README.md"]:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertNotIn("/sprites-inspector", text)
                self.assertNotIn("sprites_guard", text)
                self.assertNotIn("PreToolUse", text)


class SpritesConfirmationGuidanceTests(unittest.TestCase):
    def test_safety_reference_keeps_former_hook_coverage(self) -> None:
        safety = (PLUGIN / "skills/sprites/references/safety.md").read_text(encoding="utf-8")
        section = safety.split("## Confirm first", maxsplit=1)[1].split("\n## ", maxsplit=1)[0]
        for phrase in ["`destroy_sprite`", "`checkpoint_restore`", "`policy_network_update`",
                       "`service_create` with an `http_port`", "`exec`", "checkpoint",
                       "rm -rf", "npm", "pip", "migrations"]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, section)

    def test_skill_points_at_the_confirmation_list(self) -> None:
        skill = (PLUGIN / "skills/sprites/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("references/safety.md#confirm-first", skill)


if __name__ == "__main__":
    unittest.main()
