# Files inside a Sprite

Sprites MCP does not expose dedicated upload, read-file, or write-file tools. Filesystem work goes through `exec`.

## Preferred transfer methods

1. `git clone` or fetch for repositories and multi-file projects.
2. Base64 plus a space-free `python3 -c` expression for small generated files.
3. Simple `cat`, `head`, `tail`, `wc`, and `ls` commands for reads.
4. Ask the user for a private-code transfer approach when credentials are unavailable.

The MCP `exec` command is represented as one string and may not preserve complex shell quoting the way a local interactive shell does. Avoid heredocs, deeply nested quotes, and relying on an stdin body that the tool schema does not expose.

## Reliable small-file write

Create the parent directory, then decode base64 with a payload that contains no spaces after `-c`:

```text
mkdir -p /home/sprite/app
python3 -c __import__('pathlib').Path('/home/sprite/app/index.html').write_bytes(__import__('base64').b64decode('BASE64_HERE'))
wc -c /home/sprite/app/index.html
```

For many files, prefer a cloned repository or a base64-encoded archive followed by a simple `tar -xzf` or `unzip` command. Never put credentials into HTTP-served paths or world-readable files.
