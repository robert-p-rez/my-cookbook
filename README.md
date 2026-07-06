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

This Compose file follows the same deployment pattern as `compose (2).yml`:
the app does not run its own `cloudflared` container. Instead, it attaches to
the external Docker network named `perezdev_proxy`, where your existing
Cloudflare/proxy connector can reach it.

No Cloudflare token, Access AUD, or team-domain variables are required in this
app's `.env` file. Keep that configuration in your existing proxy stack and in
the Cloudflare dashboard.

If you still want a local `.env` placeholder, copy the template:

```bash
cp .env.example .env
```

Create the external Docker network once if your proxy stack has not already
created it:

```bash
docker network create perezdev_proxy
```

In the existing Cloudflare/proxy stack, route the public hostname to this app:

- Hostname: `gabbys-cookbook.perezdev.com`
- Type: `HTTP`
- Service URL: `http://my-cookbook:8789`

Then create a Cloudflare Access self-hosted application for the private upload
surface:

- Application domain: `gabbys-cookbook.perezdev.com`
- Protected paths:
  - `/submit*`
  - `/admin/*`
  - `/api/*`
- Policy: allow only the emails, groups, or identity provider rules that should
  submit and review uploads.

Then build and start the site:

```bash
docker compose up --build -d
```

Open `https://gabbys-cookbook.perezdev.com` after the proxy route is active.
The production service is intentionally not published on a host port.
`my-cookbook:8789` is only reachable by containers on `perezdev_proxy`.

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

3. Create the deployment environment file:

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
docker compose exec my-cookbook wget -qO- http://127.0.0.1:8789/
```

Both cookbook containers join the external `perezdev_proxy` network. The
existing proxy reaches Nginx using `my-cookbook:8789`, not a hostname that your
host computer or browser can resolve.

## Recommended VM hardening

- Keep inbound port `8789` closed at the firewall; the proxy reaches the
  container over the external Docker network.
- Port `8789` is not one of Cloudflare's default HTTP proxy ports. Use the
  proxy service URL above rather than pointing a proxied DNS record directly to
  `:8789`.

## Recipe image submissions

- Users submit batches at `https://gabbys-cookbook.perezdev.com/submit/`.
- Review and delete submissions at
  `https://gabbys-cookbook.perezdev.com/admin/uploads/`.
- The submit, review, and upload API routes should be protected by Cloudflare
  Access in the Cloudflare dashboard/proxy layer. The upload API trusts that
  anything reaching `/api/*` came through that protected route.
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
