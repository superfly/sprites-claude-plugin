# Files inside a Sprite

Use `file_list` / `file_read` / `file_write` / `file_copy` / `file_rename` / `file_delete` for filesystem work (`workingDir` + path flags per live schema). Prefer `git clone` for repos; use `file_write` (utf8/base64) for small generated files; fall back to `exec` only when no file tool fits.

## Preferred transfer methods

1. `git clone` or fetch for repositories and multi-file projects.
2. `file_write` with `encoding: "utf8"` for literal text or `"base64"` for encoded bytes (no data URL prefix); `mkdir` can create parents. Writes support up to 16 MiB subject to transport limits.
3. `file_list` / `file_read` for directory and content inspection (prefer bounded reads over dumping large files).
4. Ask the user for a private-code transfer approach when credentials are unavailable.

## When to use `exec` instead

Fall back to `exec` only when no file tool fits (for example archive unpack after a `file_write`, or commands that are not filesystem CRUD). The MCP `exec` command is represented as one string and may not preserve complex shell quoting the way a local interactive shell does. Avoid heredocs, deeply nested quotes, and relying on an stdin body that the tool schema does not expose.

## Reliable small-file write via file tools

Use `file_write` with `sprite`, `path`, `workingDir`, and `content`. Include `sprite_id` when known. Verify with `file_read`, `file_list`, or a short `exec` (`wc -c`, checksum).

For many files, prefer a cloned repository or a base64-encoded archive written with `file_write` then unpacked via a simple `tar`/`unzip` `exec`. Never put credentials into HTTP-served paths or world-readable files.

`file_delete` takes explicit `recursive` and `asRoot` flags — confirm path and scope before deletion. `file_rename` and `file_copy` take `source` and `dest`; inspect the destination before overwriting.
