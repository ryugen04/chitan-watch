# Architecture

## Boundary

```text
Official Sources
  -> Source Collector
  -> Artifact Snapshot
  -> Change Detector
  -> RawChange / ChangeBundle
  -> LLM Layer
  -> ChangeEvent / Evidence / Report
  -> Web UI / RSS / Notifications
```

Deterministic code owns collection, link discovery, SHA-256 comparison, CSV parsing, schema validation, record matching, semantic diff, PDF/HTML canonicalization, and ChangeBundle generation.

The LLM layer starts after ChangeBundle exists. It may summarize, group, research official evidence, and propose vendor impact candidates. It must not mutate RawChange.

## Initial deployment shape

Use one web application, one worker, PostgreSQL, object storage, and an LLM provider adapter. Avoid premature microservices.

## Storage model

- Official binary/text content: object storage
- Snapshot metadata: database
- RawChange and ChangeBundle: database/jsonb
- ChangeEvent, Evidence, reports, review queue: database
- Prompt templates and domain taxonomies: version-controlled repository files

## Failure semantics

CrawlerRun states must distinguish:

- `SUCCESS_NO_CHANGE`
- `SUCCESS_CHANGED`
- `FAILED`
- `PARTIAL_FAILURE`
- `SCHEMA_BREAK`

Silent monitoring failure is a product bug.
