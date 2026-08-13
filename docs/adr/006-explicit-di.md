# ADR-0006: Explicit constructor DI and composition root

Status: accepted

Dependencies are passed through constructors and assembled in one visible composition root. No hidden service locator or import-time global wiring.

