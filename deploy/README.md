# VPS release: Procurement Evidence Inspector

This directory describes the public showcase release only. It packages admitted synthetic fixtures
and the read-only Inspector; it contains no production procurement data, credentials, user
accounts, uploads, write actions, or availability commitment.

## Runtime boundary

The Inspector runs as one non-root container on the existing VPS Docker network
`vps-srv_traefik_public`. Its Compose file intentionally contains no `ports:` mapping. The existing
Traefik instance owns public ports 80 and 443, redirects HTTP to HTTPS, provisions the certificate
through its existing `desecresolver`, and forwards this hostname to the container's internal port
8000.

The only hostname is `procurement.ediacarian.dedyn.io`. Its A record belongs in the existing VPS
deSEC/DDNS configuration; credentials stay on that host and must never be copied into this
repository. Add the `procurement` record alongside the existing managed records, recreate only the
DDNS updater, then verify DNS before releasing this service.

## Release procedure

On the VPS, use an isolated checkout outside `/home/ubuntu/vps-srv` and all SciFact paths:

```sh
git clone git@github.com:stauntonjr/procurement-intelligence-lab.git /home/ubuntu/procurement-intelligence-lab
cd /home/ubuntu/procurement-intelligence-lab
git checkout <merged-git-revision>
export PROCUREMENT_INSPECTOR_REVISION="$(git rev-parse HEAD)"
docker compose -f deploy/compose.yml build
docker compose -f deploy/compose.yml up -d --no-deps inspector
```

Record the checkout revision, `docker image inspect` digest, and a SHA-256 hash of the rendered
Compose configuration with environment values but no credentials. The image tag is the complete
Git revision; `latest` is not deployment evidence.

## Verification and rollback

Verify the container's health state and that the host has no listener on port 8000. Then verify
these public paths through Traefik:

```sh
curl -I http://procurement.ediacarian.dedyn.io/
curl --fail --show-error https://procurement.ediacarian.dedyn.io/healthz
curl --fail --show-error https://procurement.ediacarian.dedyn.io/
```

Complete the fixed browser walkthrough: inspect the conflicting required-GPU scenario, the
equal-value competing-revision state, and the highlighted original XLSX source cells. Confirm a
wrong scope produces the existing 403 response and an unavailable evidence identifier produces
the existing 404 response.

To roll back, check out the prior recorded revision, set `PROCUREMENT_INSPECTOR_REVISION` to that
revision, rebuild or reuse its image, and recreate **only** `inspector`. Do not restart Traefik,
DDNS, Alloy, SciFact, or DGX services.
