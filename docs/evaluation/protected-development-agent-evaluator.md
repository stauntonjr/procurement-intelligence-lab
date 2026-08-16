# Protected development-agent evaluator

Status: protected evaluator established; baseline execution pending an explicitly authorized
model/configuration run.

The blind evaluator lives outside this public repository at
[`stauntonjr/procurement-intelligence-lab-evaluator`](https://github.com/stauntonjr/procurement-intelligence-lab-evaluator),
which is private. It is the only place allowed to contain held-out challenge oracles, model
credentials, private instruction variants, or agent transcripts. The public repository contains
the C001-C008 regression oracles and challenge metadata, but never the blind answer key.

## Run boundary

Each baseline run pins:

- public repository revision and evaluator revision;
- instruction variant: `pre-hardening` or `hardened`;
- model identifier, configuration/prompt version, and seed when applicable;
- challenge set version and opaque held-out challenge IDs; and
- start/end timestamps and duration.

The evaluator reports only structured outcomes. For every challenge it records separate
`prevention`, `pre_merge_detection`, and `repair` values from the closed set `success`, `failure`,
`not_evaluated`, or `not_applicable`. It must not persist chain-of-thought, raw prompts, private
oracle text, credentials, or unredacted agent transcripts.

The public result contract is defined in
[`evals/development_agents/baseline.schema.json`](../../evals/development_agents/baseline.schema.json).
The private runner validates the same shape before publishing an aggregate baseline report.

## Baseline protocol

1. Build the evaluator from its pinned private revision and verify its access policy.
2. Run all C001-C008 equivalents twice: once with the pre-hardening instruction bundle and once
   with the hardened bundle from the target public revision.
3. Score prevention, pre-merge detection, and repair independently; do not collapse them into a
   single success rate.
4. Publish only aggregate JSON containing the pinned revisions, configuration identifiers,
   durations, and outcome counts. Keep held-out challenge-level evidence private.
5. Record the run URL and aggregate report in the Issue/PR without copying hidden oracle details.

No baseline score is claimed by this public-repository slice until an authorized model run has
completed. A missing score is evidence of an unexecuted experiment, not a green result.

## Access and CI controls

The companion repository is private, uses manual dispatch for baseline runs, least-privilege
workflow permissions, environment-protected secrets, and artifact retention limits. Public PRs in
this repository cannot invoke it with trusted credentials. The evaluator may read a public commit
or release artifact, but public code never receives the held-out oracle or secret-bearing token.
