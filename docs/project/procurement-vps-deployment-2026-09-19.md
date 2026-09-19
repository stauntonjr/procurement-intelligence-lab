# Public release evidence: Procurement Evidence Inspector

**Released:** 2026-09-19  
**Public URL:** <https://procurement.ediacarian.dedyn.io/>  
**Issue:** [#163](https://github.com/stauntonjr/procurement-intelligence-lab/issues/163)

## Released artifact

- Git revision: `f9346a5c15807ccea73661734e272c730936ad51`
- Image ID: `sha256:883fa6433aa1e7f87ddf1c914f3ba81b79366b52a89791ddbfa330afee4ba3ac`
- Rendered Compose SHA-256: `6782f12c44e32ef7d2dfaeb61f9e17ff5bbef6d8f3730453c8c7b5ccce35f570`
- Runtime: a non-root, read-only `procurement-inspector` container on
  `vps-srv_traefik_public`; it has no direct host port.

## Public verification

- `procurement.ediacarian.dedyn.io` resolves to the VPS address `193.122.204.110`.
- HTTP `/` returns a `301` redirect to HTTPS.
- HTTPS presents a valid Let’s Encrypt certificate for
  `procurement.ediacarian.dedyn.io`.
- `GET /healthz` returns `{"status": "ok"}` through Traefik.
- The public homepage renders the Evidence Inspector.
- The conflict walkthrough returns an unresolved required quantity with no value.
- The shared-value walkthrough returns a governed required quantity of `4` and expected state of
  `4`; its admitted source row retains `GPU-A`, `GPU accelerator`, `4`, `100`, and `each`.
- An unknown evidence identifier returns `404`; a cross-tenant request returns `403`.

Traefik is the only public listener on ports 80 and 443. During this release, the running Traefik
container was attached to its already declared `vps-srv_traefik_public` network without a restart,
restoring the existing Compose topology so it could reach the Inspector.

## Rollback

No previous public Inspector release exists. For a future rollback, check out the prior recorded
revision in `/home/ubuntu/procurement-intelligence-lab`, set
`PROCUREMENT_INSPECTOR_REVISION` to that revision, rebuild or reuse its image, and recreate only
the `inspector` service. Do not restart Traefik, DDNS, Alloy, SciFact, or DGX services.

## Public limits

This is an employer-facing architecture demo using only admitted synthetic fixtures. It has no
accounts, customer or operational procurement data, uploads, write workflows, purchasing actions,
external model calls, or availability commitment.
