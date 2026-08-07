# Services

Use Sprites services for web servers, workers, databases, daemons, and preview applications. Do not leave a forever-blocking `exec` as the primary lifecycle mechanism.

1. Inspect existing services with `service_list`.
2. Choose a stable role name such as `web`, `api`, `worker`, or `db`.
3. Create the service with `service_create`, setting `service_name`, `cmd`, and any `args` deliberately. Set `http_port` only when the service should answer on the Sprite's URL; without it the URL proxy keeps routing to port 8080.
4. Start it with `service_start`.
5. Confirm status with `service_get` and inspect `service_logs`.
6. Report the service name, port, URL, and expected authentication/exposure.

Read logs before restarting or modifying a failing service. Setting `http_port` is what makes a service reachable over HTTP, so the plugin asks for confirmation on that call; explain what the service serves before issuing it. Never expose environment dumps, admin/debug endpoints, arbitrary file browsers, secrets, or unfiltered logs.
