# Services

Use Sprites services for web servers, workers, databases, daemons, and preview applications. Do not leave a forever-blocking `exec` as the primary lifecycle mechanism.

1. Inspect existing services with `service_list`.
2. Choose a stable role name such as `web`, `api`, `worker`, or `db`.
3. Create the service with its command and HTTP port set intentionally.
4. Start it with `service_start`.
5. Confirm status with `service_get` and inspect `service_logs`.
6. Report the service name, port, URL, and expected authentication/exposure.

Read logs before restarting or modifying a failing service. Confirm before making a service public. Never expose environment dumps, admin/debug endpoints, arbitrary file browsers, secrets, or unfiltered logs.
