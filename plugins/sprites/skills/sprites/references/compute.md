# Remote compute

Use Sprites for isolated Linux compute: builds, tests, generated or untrusted code, preview environments, and long-running services.

## Choose local or remote

| Situation | Prefer |
| --- | --- |
| Local repository edits and quick reads | Claude Code local tools |
| User explicitly says remote, sandbox, or Sprite | Sprite |
| Untrusted/generated execution or heavy installs | Sprite |
| Persistent dev server or worker | Sprite service |
| Whole-environment rollback | Sprite checkpoint |

## Bootstrap a task environment

1. Call `list_sprites`; reuse a clear task match or call `create_sprite` with a descriptive name.
2. Probe only the required tools with short `exec` calls such as `node -v`, `python3 --version`, and `git --version`.
3. Create a clean baseline checkpoint before large installs or risky execution.
4. Bring code in with `git clone` when possible. For small generated files, use the base64 pattern in [files.md](files.md). Ask the user how to access private code rather than inventing credentials.
5. Use `exec` for finite commands and services for processes that should remain running.
6. Verify with tests, health checks, `service_get`, or `service_logs`.
7. Report the Sprite name, commands and exit status, checkpoint ids, services, and URLs.

Use non-interactive command flags so remote executions do not hang. Stop services that are no longer needed. Destroy a Sprite only after explicit user intent and the plugin's confirmation prompt.
