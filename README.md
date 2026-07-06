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

Set these values in `.env`:

```dotenv
CLOUDFLARE_TUNNEL_TOKEN=your-dedicated-tunnel-token
CLOUDFLARE_ACCESS_TEAM_DOMAIN=https://your-team.cloudflareaccess.com
CLOUDFLARE_ACCESS_AUD=your-access-application-aud-tag
ACCESS_ALLOWED_EMAILS=
```

`ACCESS_ALLOWED_EMAILS` is optional. Leave it blank to rely on the Cloudflare
Access policy, or set a comma-separated email allowlist for defense in depth.

In Cloudflare Zero Trust, add a public hostname to that tunnel:

- Hostname: `gabbys-cookbook.perezdev.com`
- Type: `HTTP`
- Service URL: `http://cookbook:8789`

Then create a Cloudflare Access self-hosted application for the private upload
surface:

- Application domain: `gabbys-cookbook.perezdev.com`
- Protected paths:
  - `/submit*`
  - `/admin/*`
  - `/api/*`
- Policy: allow only the emails, groups, or identity provider rules that should
  submit and review uploads.

Copy the application's Audience (AUD) tag into `CLOUDFLARE_ACCESS_AUD`. Use
your Zero Trust team domain for `CLOUDFLARE_ACCESS_TEAM_DOMAIN`, for example
`https://your-team.cloudflareaccess.com`.

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

All three containers join the Compose-managed `cookbook-network`. The tunnel
reaches Nginx using the Compose service name `cookbook`, not a hostname that
your host computer or browser can resolve.

Use a tunnel dedicated to this stack. Reusing the tunnel from another isolated
Compose project can cause requests to reach a connector that has no route to
the `cookbook` container.

## Recommended VM hardening

- Keep inbound port `8789` closed at the firewall; the tunnel reaches the
  container over its private Docker network.
- Port `8789` is not one of Cloudflare's default HTTP proxy ports. Use the
  Tunnel service URL above rather than pointing a proxied DNS record directly
  to `:8789`.

## Recipe image submissions

- Users submit batches at `https://gabbys-cookbook.perezdev.com/submit/`.
- Review and delete submissions at
  `https://gabbys-cookbook.perezdev.com/admin/uploads/`.
- The submit, review, and upload API routes are protected by Cloudflare Access.
  The upload API validates the `Cf-Access-Jwt-Assertion` token against
  Cloudflare's signing keys and this application's AUD tag.
- Images and manifests are stored in the private Docker volume
  `my-cookbook_cookbook-uploads` and are never served directly by Nginx.
- The upload API accepts validated JPEG, PNG, and WebP files, with a maximum of
  20 images per submission, 15 MB per image, and 90 MB per batch. The batch
  limit stays below Cloudflare's 100 MB request limit on Free and Pro plans.
- Delete each submission from the review page after its recipe has been added
  to the cookbook.

## Recipe source files

Maintain recipes as Markdown files under `docs/recipes/`. You do not need to
hand-maintain matching HTML files.

MkDocs reads the Markdown source, applies the theme/templates/plugins, and
generates static HTML into `site/` during `mkdocs build`. The `site/` directory
is build output and is ignored by Git; Docker regenerates it during image builds.
