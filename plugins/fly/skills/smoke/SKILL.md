---
name: smoke
description: Check authorized Fly MCP read paths; optionally test a disposable Sprite's file and exec operations when explicitly invoked with --create-sprite.
disable-model-invocation: true
argument-hint: "[--create-sprite] [--keep]"
---

# Fly smoke test

Keep every call on the Fly plugin connection. Read [authentication](../fly/references/auth.md) if tools or access are missing.

## Default: read-only

1. Call `get_fly_context` and inspect bindings and scopes.
2. List apps, Managed Postgres clusters, and/or Sprites only where the tools are available and the grant permits. Use exact organization slugs. Empty lists are valid; mark ungranted products as skipped.
3. For an authorized app, read its metadata and permitted Machine/volume summaries. Read secret names or networking metadata only if requested and granted; never fetch sensitive configuration as a smoke check.
4. For an authorized Managed Postgres organization, list clusters and inspect a selected cluster with `get_postgres_cluster`. Use the live schemas and exact discovered identifiers. Do not fetch query text, provision a cluster, create a backup/database, or enable extensions as a smoke check.
5. Report each attempted read's outcome and skipped checks. Do not create billable resources or change anything.

## Explicit disposable Sprite check

Only perform these steps if `$ARGUMENTS` includes the exact flag `--create-sprite`. This flag requests Sprite creation, file write/read, and a harmless exec; it does not authorize deletion, Fly app/Machine/volume changes, or Managed Postgres changes.

1. Verify the grant permits Sprite creation, file write/read, and exec. Read its prefix and creation cap with `get_fly_context`. If unavailable, stop the write check and report the missing permission.
2. Create a uniquely named disposable Sprite under the permitted prefix. Record the returned name and ID immediately. After an uncertain response, inspect before retrying creation.
3. Call `file_write` for `/tmp/fly-smoke.txt` with `workingDir: "/"`, `content: "fly-smoke-ok\n"`, and `encoding: "utf8"`. Include the created Sprite's name and ID. Read it back with `file_read`, supplying required fields from the live schema, and compare the contents.
4. Call `exec` with `cmd: ["uname", "-a"]` and record a short output line, plus the exit status if the result includes one (Sprite `exec` currently returns output only; say so rather than reporting a status).
5. If `--keep` is present, keep the Sprite. Otherwise ask before destruction unless the user already explicitly requested cleanup; honor the hook prompt. On any failure, report the resource that was created and whether it remains. Never delete a pre-existing Sprite or use deletion to make space under a cap.

Report authorization, each read/write/exec result, the exact created Sprite identity, and cleanup as kept, destroyed, or awaiting approval. A test that could not exercise a tool is skipped or failed, never passed. Do not install packages, start services, change network policy, or use a local shell/CLI as a fallback.
