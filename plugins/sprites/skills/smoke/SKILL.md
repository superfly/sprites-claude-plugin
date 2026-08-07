---
name: smoke
description: Run an explicit end-to-end Sprites MCP smoke test covering list, create, and exec, with cleanup only after user approval.
disable-model-invocation: true
argument-hint: "[--keep]"
---

# Sprites smoke test

Prove the hosted MCP path end to end with a few calls:

1. Call `list_sprites`. Empty is valid.
2. Create a short-lived Sprite. If the session has no known prefix, prefer `mcp-smoke-<shortid>`. If the API requires another prefix, retry once with the exact required prefix and remember it.
3. Run `uname -a` or `echo smoke-ok` through `exec` and capture the exit status and a short output line.
4. If `$ARGUMENTS` contains `--keep`, keep the Sprite. Otherwise, destroy it only if the user explicitly requested cleanup before invoking this skill; if not, ask before calling `destroy_sprite`.

Report:

```text
Sprites smoke test
- list: OK (N visible) | empty (OK)
- create: NAME — STATUS — URL
- exec: exit CODE — OUTPUT
- destroy: kept | destroyed | awaiting approval
- prefix learned: PREFIX | full-access (none) | unknown
```

Do not install packages, create services, change policy, use the local shell as the Sprite, install the Sprites CLI, or call the REST API.
