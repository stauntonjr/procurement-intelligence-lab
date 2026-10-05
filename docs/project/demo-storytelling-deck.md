# Demo storytelling deck

The editable presentation is the native Google Slides deck
[Procurement Intelligence Lab — Evidence-to-Action Architecture](https://docs.google.com/presentation/d/17LFjSGQs1q3rIvuqdRKdNqvBFXXYjKWctcDvqlLjxoQ/edit).
The repository retains the exact rendered slide images used by the automated
rehearsal recorder in `docs/assets/rehearsal-v2/slides/`.

## Slide order

1. Procurement Intelligence Lab — from conflicting documents to a reviewable,
   evidence-backed decision.
2. Who, what, why, and how.
3. Architecture — the full evidence-to-action pipeline, with gold data at
   every boundary and human governance at controlled checkpoints.
4. Hypothetical conflict — two approved requirements disagree.
5. Processing flow — input, parse, assert, reconcile state, detect, review.
6. Procurement scenarios made reviewable.
7. Potential applications beyond procurement.
8. Live-demonstration transition.

## Source and claim boundaries

The content is grounded in `AGENTS.md`, `docs/architecture.md`,
`docs/architecture/platform-semantics.md`,
`docs/architecture/universal-stage-semantics.md`,
`docs/architecture/domain-verticals.md`, and the product contracts named in
each slide footer. The conflicting-requirement example is explicitly
hypothetical. Procurement is the implemented vertical; every other domain is
presented only as a potential application of the architecture.

The architecture vision runs from source artifacts through structured and
schema-mapped documents, observations, assertions, entity resolution,
reconciliation, operational state, derived facts, anomalies, predictions,
policy decisions, authorized actions, and human governance. Gold data and
evaluation apply at every boundary. The deck visually distinguishes current
procurement behavior (through anomaly assessment and review) from prediction,
decision, and action stages that remain architectural vision.

The deck does not claim deployment, purchasing authority, or support for those
other verticals. It states that model interpretation routes a request,
deterministic services compute governed state, and an authenticated human owns
the saved review disposition.

## Verification

- Visual QA was performed against the eight-slide contact sheet after a
  consolidated layout repair pass; no content is cropped.
- Google Drive conversion returned a native presentation with eight ordered
  slides, a 16:9 page size, and editable text and shapes.
- Structural readback confirmed the expected slide titles, all 15 pipeline
  stages, both cross-cutting governance rails, source footers, the
  hypothetical/non-implemented qualifiers, and the live-demo transition.
- The recorder must consume the rendered PNGs in numeric order so the captured
  deck is revision-stable even if the native deck is edited later.
