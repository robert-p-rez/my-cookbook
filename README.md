# my-cookbook

MkDocs cookbook site with a production container image and a simple Docker Compose deploy target for a Hetzner VM.

## Local development

Run the live-reload dev server in Docker:

```bash
docker compose -f compose.dev.yml up --build
```

Then open `http://localhost:8789`.

## Production container

Build and run the production image locally:

```bash
docker compose up --build -d
```

Then open `http://localhost:8789`.

The production image:

- builds the MkDocs site during `docker build`
- fails the build on MkDocs warnings via `--strict`
- serves the generated static files through unprivileged Nginx

## Deploy to a Hetzner VM

These steps assume an Ubuntu VM with Docker Engine and the Docker Compose plugin installed.

1. Copy the project to the server:

```bash
rsync -av --delete ./ your-user@your-vm-ip:/opt/my-cookbook/
```

2. SSH into the VM:

```bash
ssh your-user@your-vm-ip
```

3. Ensure the external Docker network shared with `cloudflared` exists:

```bash
docker network inspect cloudflare >/dev/null 2>&1 || docker network create cloudflare
```

If your network has a different name, set `CLOUDFLARE_NETWORK` when running
Compose.

4. Start or update the site:

```bash
cd /opt/my-cookbook
docker compose up --build -d
```

5. Verify it is running:

```bash
docker compose ps
curl http://localhost:8789
```

For a Cloudflare Tunnel running on the same Docker network, set the tunnel's
service URL to `http://cookbook:8789`.

## Recommended VM hardening

- With Cloudflare Tunnel, keep inbound port `8789` closed at the firewall; the
  tunnel reaches the container over the shared Docker network.
- Port `8789` is not one of Cloudflare's default HTTP proxy ports. Use the
  Tunnel service URL above rather than pointing a proxied DNS record directly
  to `:8789`.
