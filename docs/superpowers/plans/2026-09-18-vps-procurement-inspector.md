# VPS deployment plan: Procurement Evidence Inspector

**Goal:** Serve the synthetic, read-only Procurement Evidence Inspector at
`https://procurement.ediacarian.dedyn.io` as an independently deployable showcase.

**Status:** Released on 2026-09-19. The completed HTTPS release is recorded in the
[deployment evidence note](../../project/procurement-vps-deployment-2026-09-19.md). This document
preserves the verified VPS conventions and release boundary.

## Verified deployment context

The current `ediacarian` VPS runs Docker and Traefik 2.10. Traefik owns public ports 80 and 443,
redirects HTTP to HTTPS, obtains certificates with its `desecresolver` DNS challenge, and discovers
opt-in containers on its `traefik_public` Docker network. The Docker Compose project names that
network `vps-srv_traefik_public`.

SciFact's checked-in application pattern is a containerized HTTP service with a loopback-only
host publication. Its current documented web service runs on the DGX rather than this VPS, so this
plan adopts the VPS's existing Traefik/Compose convention rather than assuming a shared SciFact
container or GPU/runtime dependency.

On 2026-09-18, `scifact.ediacarian.dedyn.io` resolves to the VPS address and
`procurement.ediacarian.dedyn.io` has no A record. The delivery work must add and verify the
procurement hostname without changing the existing SciFact/DGX service.

## Target architecture

```text
Browser
  │ HTTPS:443
  ▼
VPS Traefik (existing; deSEC TLS)
  │ Docker network vps-srv_traefik_public
  ▼
procurement-inspector container :8000
  │
  └── packaged synthetic XLSX fixtures and read-only inspector
```

The container exposes no host port. Traefik is the only public ingress. The application contains
no secrets, external model calls, customer data, write endpoints, or procurement-action authority.
It remains an employer-facing synthetic-data architecture demo.

## Delivery slices

### 1. Make the inspector deployable

Create a bounded GitHub Issue before implementation. Its acceptance criteria should cover the
container, `/healthz`, reverse-proxy contract, domain, rollback, and public-demo limitations.

Add a production server configuration to `interfaces/web.py` or a dedicated composition module:

- bind the container process to `0.0.0.0:8000` only inside the container;
- provide unauthenticated `GET /healthz` returning a small static JSON response;
- retain existing scope checks and all current application behavior;
- make the process configurable through explicit host/port arguments or environment variables,
  without reading ambient deployment state in the domain.

Add a focused HTTP integration test for `/healthz` and preserve the existing real-browser/API
scenario tests. The domain, fixtures, governing policy, and source-viewer rules must remain
unchanged.

### 2. Build a reproducible image

Add a repository-owned Dockerfile and a minimal production Compose file, for example under
`deploy/`. The image should install the built wheel rather than rely on a bind-mounted checkout.
It must include package resources, particularly the admitted synthetic XLSX fixtures and README
media dependencies used by the inspector.

The Compose service should:

- use a fixed service and container name such as `procurement-inspector`;
- restart with `unless-stopped`;
- declare a Docker health check against `http://127.0.0.1:8000/healthz`;
- join the externally managed `vps-srv_traefik_public` network;
- omit `ports:` entirely;
- set only non-secret runtime configuration explicitly; and
- use a read-only filesystem and dropped Linux capabilities if the stdlib server and temporary
  runtime behavior remain compatible.

The implementation must document the exact image tag or source revision used for deployment.
No mutable `latest` image tag becomes deployment evidence.

### 3. Attach to the existing Traefik convention

Add opt-in Traefik labels to the inspector service:

```text
traefik.enable=true
traefik.http.routers.procurement.rule=Host(`procurement.ediacarian.dedyn.io`)
traefik.http.routers.procurement.entrypoints=websecure
traefik.http.routers.procurement.tls.certresolver=desecresolver
traefik.http.services.procurement.loadbalancer.server.port=8000
```

Use a service-specific router and service name. Do not publish port 8000, modify Traefik's global
ports, expose its dashboard, or alter the existing `vps-srv` Compose project beyond the DNS record
required for the new hostname. HTTP-to-HTTPS redirection continues to be provided by the existing
Traefik entrypoint.

### 4. Provision and verify DNS and TLS

Add an A record for `procurement.ediacarian.dedyn.io` pointing to the current VPS public address.
Because the existing dynamic-DNS configuration enumerates host records, update it through the
owner's established deSEC/DDNS management path so future address updates include the new hostname.
Do not copy a token or DNS credential into this repository.

Before starting the inspector, verify:

1. `dig +short procurement.ediacarian.dedyn.io A` returns the intended VPS address.
2. The Traefik container can create or renew a certificate using `desecresolver` without changing
   another hostname's router.
3. The container is healthy on its Docker network and no host listener exists on port 8000.
4. `https://procurement.ediacarian.dedyn.io/healthz` returns the expected health response and
   `http://procurement.ediacarian.dedyn.io/` redirects to HTTPS.

### 5. Release and prove the public showcase

Deploy from a clean, tested revision after `make check`, `make integration`, `make package-smoke`,
and `make challenges` succeed. On the VPS, use an isolated checkout or image directory for this
service, separate from `/home/ubuntu/vps-srv` and all SciFact/DGX paths.

Record a deployment evidence note containing:

- Git commit and immutable image digest;
- deployed Compose configuration hash with secrets omitted;
- DNS, TLS, health, HTTP redirect, and public HTTPS results;
- the fixed browser walkthrough: conflict abstention, shared-value governed state, and original
  XLSX cell evidence; and
- known limits: synthetic read-only demo, no user accounts, no production procurement data, no
  action execution, and no availability claim.

Update `README.md` with the public URL only after the complete HTTPS walkthrough succeeds. Keep
the local launch instructions as the reproduction path.

## Rollback and operations

Keep the previous immutable image tag available. A rollback is limited to changing the
`procurement-inspector` image reference and recreating that one service after confirming the
previous image's health check. It must not restart Traefik, DDNS, Alloy, or any SciFact/DGX
process.

Inspect container logs and Traefik access/error logs for the single hostname during the initial
release. Treat a failing health check, missing certificate, DNS mismatch, or proxy `502/503` as a
failed deployment and restore the last healthy image before publishing the URL.

## Acceptance criteria

- The hostname resolves to the VPS and serves a valid HTTPS certificate.
- Only Traefik exposes public 80/443; the inspector has no direct host port.
- A fresh browser can complete the documented synthetic conflict and evidence walkthrough.
- Direct health, redirect, TLS, scope-denial, and unavailable-evidence cases are verified through
  the public proxy.
- The deployed image digest and Git revision are recorded, and a rollback to the prior image is
  tested or documented from a known healthy release.
- Documentation remains explicit that this is a synthetic, read-only showcase rather than a
  production procurement system.

## Non-goals

- Moving or exposing SciFact services on this VPS.
- Sharing a database, container network beyond Traefik ingress, credentials, or deployment
  lifecycle with SciFact.
- Authentication, customer uploads, write workflows, model hosting, retrieval infrastructure,
  purchasing actions, or operational procurement claims.
