# my-cookbook

MkDocs cookbook site for `https://gabbys-cookbook.perezdev.com`, with a
production container image and a Docker Compose deploy target for a Hetzner VM.

## Local development

Run the live-reload dev server in Docker:

```bash
docker compose -f compose.dev.yml up --build
```

Then open `http://localhost:8789`.

## Production container

Copy the environment template and add the token for a dedicated Cloudflare
Tunnel:

```bash
cp .env.example .env
```

In Cloudflare Zero Trust, add a public hostname to that tunnel:

- Hostname: `gabbys-cookbook.perezdev.com`
- Type: `HTTP`
- Service URL: `http://cookbook:8789`

Then build and start the site and its tunnel connector:

```bash
docker compose up --build -d
```

Open `https://gabbys-cookbook.perezdev.com` after the tunnel reports healthy.
The production service is intentionally not published on a host port.
`cookbook:8789` is only reachable by containers on `cookbook-network`.

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

3. Create the deployment environment file and set the dedicated tunnel token:

```bash
cp .env.example .env
nano .env
```

4. Start or update the site:

```bash
cd /opt/my-cookbook
docker compose up --build -d
```

5. Verify it is running:

```bash
docker compose ps
docker compose logs cloudflared
docker compose exec cookbook wget -qO- http://127.0.0.1:8789/
```

Both containers join the Compose-managed `cookbook-network`. The tunnel reaches
Nginx using the Compose service name `cookbook`, not a hostname that your host
computer or browser can resolve.

Use a tunnel dedicated to this stack. Reusing the tunnel from another isolated
Compose project can cause requests to reach a connector that has no route to
the `cookbook` container.

## Recommended VM hardening

- Keep inbound port `8789` closed at the firewall; the tunnel reaches the
  container over its private Docker network.
- Port `8789` is not one of Cloudflare's default HTTP proxy ports. Use the
  Tunnel service URL above rather than pointing a proxied DNS record directly
  to `:8789`.
