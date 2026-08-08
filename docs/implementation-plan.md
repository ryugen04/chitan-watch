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


## ORD-006 completed increment

Implemented XLSX structure analysis and reconciliation evidence:

- reads workbook/sheet XML from XLSX ZIP payloads with the Python standard library
- reports sheet dimensions, first rows, tail cells, and workbook SHA-256
- confirmed the official Excel workbook has 47 sheets and 95 logical item candidates in header rows
- reconciled the CSV's 94-column shape by creating `csv_fields` that exclude new item `79`

Next increment should build a gated parser that can map the 94-column CSV rows using `csv_fields`, while refusing production mode until review clears the mapping status.


## ORD-007/ORD-008 completed increment

Implemented the gated parser and identity validation:

- positional parser maps 94 headerless CSV columns using `csv_fields`
- parser refuses candidate mappings unless explicitly allowed
- schema column mismatch raises `MasterSchemaBreak`
- identity validator compares multiple profiles and reports duplicate groups, blank identity parts, and full-row uniqueness

Next increment should implement row-level condition fingerprints and semantic diff matching that groups by business identity while refusing ambiguous row matches.


## ORD-009 completed increment

Implemented positional master snapshot diffing:

- normalizes positional master rows into deterministic row hashes and condition fingerprints
- treats the 4-part candidate identity as a business grouping key, not a unique row key
- matches exact row hashes before comparing unmatched rows
- emits singleton field-level modifications when one old and one new unmatched row remain in a business group
- emits `row_ambiguous` for many-to-many unmatched groups instead of guessing
- exposes `snapshot-master` and `diff-master` CLI commands

Next increment should connect discovery + snapshot metadata + positional diff into a run-level crawler state machine that can compare the latest official artifact against the previous stored snapshot.
