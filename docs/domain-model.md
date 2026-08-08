# Domain Model

## Source of Truth chain

```text
Snapshot -> RawChange -> ChangeBundle -> ChangeEvent -> Publication -> Delivery
```

## Core entities

- Source: seed page and allowed domains
- Artifact: discovered official resource
- Snapshot: one retrieval of one artifact, including HTTP metadata and SHA-256
- RawChange: deterministic delta, never edited by LLM
- ChangeBundle: deterministic run output passed to LLM
- ChangeEvent: product-level制度変更 unit, with evidence and severity
- Evidence: first-class proof object with evidence level
- CrawlerRun: monitoring state and failure visibility
- Subscription: user matching criteria
- Delivery: Slack/Email/RSS delivery state

## Fact and inference levels

- CONFIRMED: directly visible in master diff or official document
- CORROBORATED: confirmed by multiple official sources
- INFERRED: reasonable but not explicit
- UNRESOLVED: not safely decidable

The UI must label these levels instead of blending them into one narrative.
