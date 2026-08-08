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


## ORD-003 completed increment

Implemented deterministic snapshot metadata probing:

- fetch one artifact URL with explicit HTTP success handling
- compute SHA-256 over retrieved bytes
- populate Snapshot metadata without writing official payloads into Git
- expose `chitan_watch.cli snapshot`
- test SHA-256, content metadata, and HTTP failure handling

Next increment should connect discovery output to snapshot probes for a full crawler run state, including `SUCCESS_NO_CHANGE`, `SUCCESS_CHANGED`, `FAILED`, and `PARTIAL_FAILURE` outcomes.


## ORD-004 completed increment

Implemented CSV structural analysis:

- supports URL and file input
- detects encoding from `utf-8-sig`, `utf-8`, then `cp932`
- detects delimiter and header presence
- reports SHA-256, byte length, column count, record count, headers, and inconsistent rows
- records live SSK CSV facts without committing the CSV payload

Next increment should extract the official item-list PDF text/table and build the 94-column positional schema mapping.


## ORD-005 completed increment

Implemented item-list PDF extraction:

- uses Poppler `pdftotext -layout`
- parses line-level item candidates with old/new item numbers and data type
- stores a candidate positional schema in `schemas/master/2026-03-30.positional.json`
- marks the mapping as `manual_review_required` because PDF candidates (95) and CSV columns (94) do not match

Next increment should reconcile this mismatch by inspecting CSV tail positions and, if practical, the official Excel master structure.
