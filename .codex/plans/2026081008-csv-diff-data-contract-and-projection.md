# CSV Diff Data Contract And Projection Plan

Parent plan: `.codex/plans/2026081008-csv-diff-viewer-gemini-roadmap.md`
Status: draft for review, not approved for implementation.
Target root: `/home/glaucus03/dev/projects/chitan-watch`

## Original Request

CSVをエントリーポイントにするため、版管理、版ごとの差分管理、Web/APIで扱える静的JSON契約を先に固める。

## Goal

Existing runs already store manifests, payload references, evaluations, change events, and optional `master-diff.json`. This phase turns that internal storage into stable product payloads for GitHub Pages and the local API.

## Current Code To Build On

- `crawler/chitan_watch/local_store.py` stores `manifest.json`, `evaluation.json`, `master-diff.json`, and `change-events.json`.
- `crawler/chitan_watch/master_diff.py` already emits `MasterDiffSummary` with row-level changes.
- `crawler/chitan_watch/change_events.py` already creates ChangeEvents from master row changes.
- `crawler/chitan_watch/static_export.py` currently writes `runs.json`, `changes.json`, `source-health.json`, and RSS.
- `crawler/chitan_watch/api.py` currently exposes runs, changes, source-health, and run details.


## Version Selection And Ordering Rules

The version registry must not assume there is exactly one clean CSV per run forever.

Rules:

- Select `master_csv` artifacts with `source_layer=master-latest-data` and `source_role=confirmed-master-list-download` as primary CSV versions.
- If multiple CSV artifacts exist in a run, choose all primary candidates and mark `is_primary_candidate`. The UI may choose the latest by basis date and retrieval time, but the payload keeps every candidate.
- Version ordering uses `basis_date_iso` when parseable, then `retrieved_at`, then `run_id`, then `artifact_id`.
- Duplicate SHA across runs means a repeated observation, not a new content version. Keep an observation record and link it to a canonical `content_version_id`.
- Same basis date with different SHA is a high-review condition.
- Title or URL drift without SHA drift is source metadata drift and should not be treated as row diff.
- Failed parse keeps the version metadata and sets `parser_status`, instead of removing the version from the registry.

## Version Viewer Data

A CSV-first product also needs current-version inspection when no diff exists. Add a lightweight version detail payload or section that can show a bounded sample/search index.

Candidate fields:

```json
{
  "version_id": "...",
  "sample_rows": [
    { "row_number": 1, "identity": {}, "display_fields": {} }
  ],
  "sample_limit": 100,
  "search_hints": ["public_funding_number", "municipality_code", "program_name"],
  "full_row_export_available": false
}
```

Initial scope may use bounded samples and identity summaries, not full CSV rendering. The UI must label this clearly.

## Comparison Semantics

Initial static implementation persists adjacent observed-version diffs only. Arbitrary two-version comparison is out of the first implementation unless explicitly approved.

UI requirement:

- If the user selects a pair without a persisted diff, show `この版組み合わせの比較はまだ生成されていません` and point to the nearest available adjacent diffs.

Future extension:

- A backend or precompute job can generate arbitrary comparisons later.

## Data Products

### Master Versions

Endpoint and static file:

```text
/api/master/versions
/static/master-versions.json
```

Contract fields:

| Field | Meaning | Source |
|---|---|---|
| `version_id` | Stable UI id, likely `<run_id>:<artifact_id>` | run id and artifact id |
| `run_id` | Crawler run id | store path |
| `artifact_id` | CSV artifact id | manifest artifact |
| `title` | Official link/file title | manifest artifact |
| `basis_date_label` | Japanese basis date from title | parsed from title |
| `basis_date_iso` | ISO date when parseable | derived from Japanese era date |
| `source_url` | Official CSV URL | manifest artifact |
| `retrieved_at` | Snapshot retrieved time | snapshot |
| `sha256` | Snapshot hash | snapshot |
| `content_length` | Payload/content length | snapshot |
| `storage_key_present` | Whether payload is available locally | snapshot |
| `parser_status` | parsed / not_parsed / schema_break / candidate_mapping_required | projection helper |
| `row_count` | Parsed row count when available | master snapshot parse |
| `schema_path` | Positional schema path used | config |
| `mapping_status` | Official/candidate mapping warning | schema metadata |

Rules:

- Do not expose storage filesystem paths in public JSON.
- Do expose official URLs and content hashes.
- If row count cannot be computed without payload, return metadata and `parser_status`.
- Keep candidate mapping warning visible until the schema is promoted from review.

### Master Diff Index

Endpoint and static file:

```text
/api/master/diffs
/static/master-diffs.json
```

Contract fields:

| Field | Meaning |
|---|---|
| `diff_id` | Stable id for version pair |
| `run_id` | New run id |
| `old_run_id` | Previous run id when known |
| `old_version_id` | Previous CSV version id |
| `new_version_id` | Current CSV version id |
| `old_source_url` | Old official CSV URL or local source label |
| `new_source_url` | Current official CSV URL |
| `summary` | counts from `MasterDiffSummary` |
| `has_changes` | Boolean |
| `review_required` | True when ambiguous groups or schema issue exist |
| `top_changed_fields` | Counted changed field ids/labels |
| `top_jurisdictions` | Counted prefecture/municipality groups |
| `detail_url` | Static detail JSON path |

### Master Diff Detail

Endpoint and static file pattern:

```text
/api/master/diffs/<diff_id>
/static/master-diffs/<diff_id>.json
```

Contract fields:

- All index fields.
- `changes` array with row-level changes.
- Each change has `row_change_id`, `type`, `identity`, `matching_status`, row numbers, row hashes, field diffs, related ChangeEvent ids, source URLs, review reason.
- `field_labels` map for all fields used in the payload.
- `pagination` metadata if payload is capped.

## Projection Implementation Sketch

Candidate module:

```text
crawler/chitan_watch/master_projection.py
```

Candidate functions:

```python
def build_master_versions_payload(store: LocalRunStore) -> dict: ...
def build_master_diffs_payload(store: LocalRunStore, max_changes_per_detail: int = 500) -> tuple[dict, dict[str, dict]]: ...
def master_version_from_manifest(run_id: str, manifest: SnapshotManifest) -> dict | None: ...
def master_diff_projection(run_id: str, run: dict, bundle: dict) -> dict: ...
```

API additions:

- `build_api_payload('/api/master/versions', store)`
- `build_api_payload('/api/master/diffs', store)`
- `build_api_payload('/api/master/diffs/<diff_id>', store)`

Static export additions:

- Write `static/master-versions.json`.
- Write `static/master-diffs.json`.
- Write `static/master-diffs/<diff_id>.json` for each detail.

## Acceptance Criteria

- Existing API/static/RSS contracts remain compatible.
- Fixture runs with a master CSV expose at least one version.
- Fixture runs with previous/current master CSV expose a diff summary and detail.
- Diff detail row changes link back to ChangeEvent ids when available.
- Public JSON does not contain local payload filesystem paths.
- Version records handle duplicate SHA, multiple CSV artifacts, same-date/different-SHA review flags, and title/URL drift.
- Adjacent comparison limitation is explicit in payload and UI data.
- Candidate schema mapping warning is represented in version metadata.

## Tests

- Add `tests/test_master_projection.py`.
- Extend `tests/test_static_export.py` for new files.
- Extend product slice tests for API routes.
- Run full suite with `PYTHONPATH=crawler python3 -m unittest discover tests`.

## Approval Gate

Do not implement until the user accepts the static JSON names and minimum fields.

## Rollback

Remove new static/API endpoints and Web references. Old runs, RSS, changes, and source-health remain valid.
