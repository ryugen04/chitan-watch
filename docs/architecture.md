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


## Implemented deterministic run layer

The current crawler foundation has a JSON manifest boundary:

```text
ArtifactSourceSpec
  -> SnapshotManifest
  -> CrawlerRunEvaluation
  -> optional MasterDiffAttachment
```

`SnapshotManifest` is intentionally storage-neutral. It can be produced from local fixture sources today and later from object storage/database records without changing the artifact comparison rules. `CrawlerRunEvaluation` compares previous/current manifests, classifies artifact states as `added`, `removed`, `changed`, `unchanged`, or `failed`, then derives the visible CrawlerRun status.

Master CSV semantic diff is attached separately through `MasterDiffAttachment`, so a raw artifact SHA change is not confused with a confirmed row-level制度 change.


## Local storage adapter

The local operational adapter writes this ignored layout by default:

```text
storage/chitan-watch/
  runs/<run_id>/
    source-spec.json
    payloads/<artifact_id>.<ext>
    manifest.json
    evaluation.json
    master-diff.json
  sources/<source_id>/latest.txt
```

This is a development and small-ops boundary, not the long-term production database. It deliberately mirrors the future object-storage/database split: payload bytes live under `payloads/`, deterministic metadata lives in JSON, and `latest.txt` is only a pointer for local previous-run lookup.


## Product slice API/UI boundary

The local product slice now runs as one Python process for development:

```text
run-official-local
  -> LocalRunStore
  -> change-events.json
  -> chitan_watch.api
  -> apps/web
```

The API is deliberately read-only and file-backed in this phase. It exposes `/api/runs`, `/api/runs/<id>`, `/api/changes`, `/api/changes/<id>`, `/api/source-health`, and static Web assets. This keeps the UI contract close to the future hosted API while avoiding database and auth work until the deterministic pipeline is proven.


## RSS delivery boundary

RSS v1 is generated directly from stored `change-events.json` files:

```text
LocalRunStore -> ChangeEvent JSON -> RSS 2.0 XML -> /rss.xml
```

This is the first notification surface because it is pull-based, stateless, and easy for external apps to subscribe to. Slack and email can reuse the same ChangeEvent feed ordering and item summaries later.
