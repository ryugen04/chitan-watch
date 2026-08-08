# Implementation Plan

## Phase 1: official data investigation

Use the SSK hub as seed and discover latest master CSV, Excel, item list, input guide, FAQ, manuals, and MHLW references. Record headers and data properties before expanding parser logic.

## Phase 2: deterministic collector

Implement source registry, link discovery, artifact classification, HTTP metadata capture, SHA-256, snapshot metadata, and storage adapter.

## Phase 3: master parser

Implement versioned schema loading, normalization, validation, field grouping, and record model mapping.

## Phase 4: semantic diff

Implement added, removed, modified, validity rollover, and ambiguous matching. Route ambiguity to Admin Review.

## Phase 5: document diff

Canonicalize HTML main text and link inventories. For PDFs, compare SHA-256 first, extract changed pages/sections second.

## Phase 6: ChangeBundle and LLM

Finalize ChangeBundle schema, then add LLM provider adapters with structured output validation. Keep prompts in `prompts/`.

## Phase 7: persistence/API/Web

Persist snapshots, raw changes, events, evidence, subscriptions, source health, and delivery status. Build UI pages in priority order: Changes, Detail, Upcoming, Master Explorer, Source Health, Admin Review, Subscriptions.

## Phase 8: notifications

Implement RSS first, then Slack push, then email/digest scheduling.


## ORD-002 completed increment

Implemented deterministic source discovery:

- parse anchor tags with `html.parser`
- resolve relative URLs with `urljoin`
- filter by allowed domains
- classify artifacts with repository rules
- emit stable JSON through `chitan_watch.cli discover`
- avoid downloading official binaries during discovery

Next increment should add snapshot metadata and SHA-256 retrieval for selected artifacts, still without storing official binary payloads in Git.
