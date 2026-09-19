# ADR-025: Public showcase deployment stays outside procurement semantics

Status: accepted

## Context

The synthetic Procurement Evidence Inspector is useful to prospective employers only if it can be
visited without reproducing a local development environment. The existing VPS already uses Traefik
as its sole public ingress, Docker service discovery, and deSEC DNS challenges for TLS. Introducing
that runtime must not turn the Inspector into a production procurement authority or place Docker,
DNS, certificate, and host concerns in the domain layer.

## Decision

The Inspector remains a read-only HTTP adapter to the deterministic application services described
by ADR-011. It gains an unauthenticated static `/healthz` endpoint and explicit host/port command
arguments. Its local default remains loopback-only; the production container supplies `0.0.0.0:8000`
inside its private Docker network.

The public deployment is a separate, non-root container that installs the built wheel and admits
only packaged synthetic fixtures. It joins the existing externally managed Traefik network and has
no host `ports:` mapping. Traefik owns ports 80 and 443, HTTP-to-HTTPS redirection, TLS, and routing
for `procurement.ediacarian.dedyn.io`; the service opts in with a hostname-specific router label.
DNS credentials and public-record maintenance remain on the VPS's existing DDNS path and are never
repository configuration.

Each release records the merged Git revision, image digest, secret-free rendered Compose hash, and
public health/walkthrough results. Rollback recreates only the Inspector from a prior recorded
revision; it does not restart Traefik, DDNS, SciFact, or DGX services.

## Consequences

The public URL demonstrates an isolated synthetic architecture lab. It provides no accounts,
customer data, uploads, procurement actions, availability guarantee, or shared deployment lifecycle
with SciFact. Request scope and evidence failures remain enforced by the existing application path;
the health endpoint carries no domain data or authority.

Container, proxy, DNS, and certificate mechanics can evolve without changing procurement-domain
objects or policies. A future authenticated or production-data service requires a separate public
scope and authority decision.
