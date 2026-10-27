from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/fly"
PREFIX = "mcp__plugin_fly_fly__"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


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
        self.assertEqual(load_json(PLUGIN / ".claude-plugin/plugin.json")["displayName"], "Fly")

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

    def test_hook_dispatch_is_isolated(self) -> None:
        hooks = load_json(PLUGIN / "hooks/hooks.json")
        hook = hooks["hooks"]["PreToolUse"][0]
        matcher = re.compile(hook["matcher"])
        self.assertIsNotNone(matcher.search(PREFIX + "delete_app"))
        for other in ["mcp__plugin_sprites_sprites__destroy_sprite", "mcp__fly__delete_app",
                      "mcp__plugin_other_fly__delete_app", "mcp__plugin_fly_fly_extra__delete_app"]:
            self.assertIsNone(matcher.search(other))
        self.assertEqual(hook["hooks"][0]["command"], '"${CLAUDE_PLUGIN_ROOT}"/scripts/fly_guard.py')

    def test_bundle_is_self_contained(self) -> None:
        manifest = load_json(PLUGIN / ".claude-plugin/plugin.json")
        self.assertTrue((PLUGIN / manifest["types"]).is_file())
        for required in ["README.md", "LICENSE", "assets/fly-icon.svg", "hooks/register.tsx",
                         "scripts/fly_guard.py", "skills/fly/SKILL.md", "skills/status/SKILL.md",
                         "skills/smoke/SKILL.md"]:
            self.assertTrue((PLUGIN / required).is_file(), required)
        self.assertTrue((PLUGIN / "scripts/fly_guard.py").stat().st_mode & 0o111)
        for path in PLUGIN.rglob("*"):
            self.assertFalse(path.is_symlink(), str(path))
            if path.suffix in {".ts", ".tsx", ".py", ".json"}:
                self.assertNotIn("../../sprites", path.read_text())

    def test_inspector_names_do_not_collide(self) -> None:
        register = (PLUGIN / "hooks/register.tsx").read_text()
        contract = (PLUGIN / "types/index.d.ts").read_text()
        self.assertIn("const COMMAND = 'fly-sprites-inspector'", register)
        self.assertIn("const PANE = 'fly-sprites-inspector'", register)
        self.assertIn("const SERVER = 'fly'", register)
        self.assertIn("plugin: 'fly'", register)
        self.assertIn("fly: { inspector: InspectorState }", contract)
        self.assertNotIn("plugin: 'sprites'", register)


class FlyGuardTests(unittest.TestCase):
    def run_guard(self, name: str, args: dict, prefix: str = PREFIX) -> dict | None:
        result = subprocess.run(
            [str(PLUGIN / "scripts/fly_guard.py")],
            input=json.dumps({"tool_name": prefix + name, "tool_input": args}),
            text=True, capture_output=True, check=True,
        )
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout) if result.stdout.strip() else None

    def assert_asks(self, name: str, args: dict) -> dict:
        result = self.run_guard(name, args)
        self.assertIsNotNone(result)
        output = result["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "PreToolUse")
        self.assertEqual(output["permissionDecision"], "ask")
        self.assertTrue(output["permissionDecisionReason"])
        return output

    def test_read_paths_keep_normal_permissions(self) -> None:
        for name in ["get_fly_context", "list_apps", "list_machines", "get_machine",
                     "list_volumes", "list_app_secrets", "list_app_ips", "get_app_certificate",
                     "list_sprites", "get_sprite_info", "service_list", "checkpoint_list",
                     "file_read", "file_list"]:
            with self.subTest(tool=name):
                self.assertIsNone(self.run_guard(name, {}))

    def test_destructive_targets_require_confirmation(self) -> None:
        for name, args in [
            ("delete_app", {"app_name": "production"}),
            ("delete_machine", {"app_name": "production", "machine_id": "a" * 14, "force": True}),
            ("delete_volume", {"app_name": "production", "volume_id": "vol_123"}),
            ("destroy_sprite", {"name": "mcp-test"}),
            ("checkpoint_restore", {"sprite": "mcp-test", "checkpoint_id": "v2"}),
            ("policy_network_update", {"sprite": "mcp-test", "rules": []}),
            ("file_delete", {"sprite": "mcp-test", "path": "/data", "workingDir": "/",
                             "recursive": True, "asRoot": True}),
        ]:
            with self.subTest(tool=name):
                self.assert_asks(name, args)

    def test_billable_and_disruptive_changes_require_confirmation(self) -> None:
        for name in ["create_machine", "create_volume", "extend_volume", "start_machine",
                     "stop_machine", "restart_machine", "suspend_machine", "signal_machine",
                     "cordon_machine", "uncordon_machine", "set_machine_memory_limit",
                     "reclaim_machine_memory", "update_volume", "update_machine_metadata",
                     "set_machine_metadata_key", "delete_machine_metadata_key",
                     "create_machine_lease", "release_machine_lease", "exec_kill", "service_stop",
                     "file_copy", "file_rename"]:
            with self.subTest(tool=name):
                self.assert_asks(name, {})

    def test_secret_changes_never_echo_values(self) -> None:
        secret = "private-test-value-never-echo"
        for name, args in [
            ("set_app_secret", {"app_name": "example", "secret_name": "KEY", "body": {"value": secret}}),
            ("update_app_secrets", {"app_name": "example", "body": {"values": {"KEY": secret, "OLD": None}}}),
            ("delete_app_secret", {"app_name": "example", "secret_name": "KEY"}),
        ]:
            with self.subTest(tool=name):
                output = self.assert_asks(name, args)
                self.assertNotIn(secret, json.dumps(output))

    def test_machine_exec_is_guarded_even_for_unrecognized_commands(self) -> None:
        output = self.assert_asks("exec_machine_command", {
            "app_name": "production", "machine_id": "a" * 14,
            "body": {"command": ["custom-admin", "private-argument"]},
        })
        self.assertNotIn("private-argument", json.dumps(output))
        self.assertIn("Sprite checkpoints do not protect", output["permissionDecisionReason"])

    def test_risky_sprite_exec_supports_argv_and_legacy_strings(self) -> None:
        for command in ["npm install", ["npm", "install"], ["sh", "-c", "rm -rf /data"],
                        ["python3", "-m", "pip", "install", "example"]]:
            with self.subTest(command=command):
                output = self.assert_asks("exec", {"sprite": "mcp-test", "cmd": command})
                self.assertIn("checkpoint", output["permissionDecisionReason"])

    def test_simple_sprite_exec_keeps_normal_permissions(self) -> None:
        for command in ["uname -a", ["uname", "-a"]]:
            self.assertIsNone(self.run_guard("exec", {"sprite": "mcp-test", "cmd": command}))

    def test_http_service_requires_confirmation(self) -> None:
        self.assert_asks("service_create", {"sprite": "mcp-test", "service_name": "web", "http_port": 3000})
        self.assertIsNone(self.run_guard("service_create", {"sprite": "mcp-test", "service_name": "worker"}))

    def test_other_connections_are_untouched_even_if_called_directly(self) -> None:
        for prefix in ["mcp__plugin_sprites_sprites__", "mcp__fly__", "mcp__plugin_other_fly__"]:
            with self.subTest(prefix=prefix):
                self.assertIsNone(self.run_guard("destroy_sprite", {"name": "mcp-test"}, prefix))

    def test_invalid_payload_does_not_crash(self) -> None:
        for payload in ["", "invalid-json", "[]", '{"tool_name": "mcp__plugin_fly_fly__delete_app", "tool_input": null}']:
            result = subprocess.run([str(PLUGIN / "scripts/fly_guard.py")], input=payload,
                                    text=True, capture_output=True, check=True)
            self.assertEqual(result.stderr, "")
            if "delete_app" in payload:
                self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"], "ask")
            else:
                self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
