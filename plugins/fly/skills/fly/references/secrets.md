# App secrets and networking metadata

## Secrets

Use `list_app_secrets` or `get_app_secret` to inspect names, digests, and timestamps. These tools never return the secret value. Do not claim to have retrieved or compared plaintext values from their metadata. Their schemas list `show_secrets`, but the server refuses it with an error that reads like a missing grant; omit the parameter, and do not take that refusal as evidence the grant lacks secret access.

- `set_app_secret` takes the app, secret name, and `body.value`.
- `update_app_secrets` takes `body.values`, a mapping of names to strings or null. Null deletes a secret and requires delete permission as well as write permission. A deletion's result still lists the name, without a digest; confirm with `list_app_secrets`. The upstream bulk API also needs create/write/delete action bits even for sets; do not work around a rejected grant.
- `delete_app_secret` deletes a name. It can succeed and advance the secrets version even when that name is already absent.

Confirm the target app and the names being added, changed, or removed. Use an approved source for values; do not ask users to paste credentials into chat, print values in logs, or echo them in confirmation reasons or summaries. If a value cannot be supplied securely through the available workflow, direct the user to their existing secret-management interface. Verify the resulting metadata and requested application behavior without exposing the values.

## IP addresses and certificates

`list_app_ips`, `list_app_certificates`, and `get_app_certificate` are read-only. They help diagnose existing assignments and certificate state. The current MCP does not allocate or release IPs, create certificates, or modify DNS. Explain that boundary if a requested fix needs those operations.
