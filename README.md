# Chitan Watch

Chitan Watch is a repository for building a制度変更 intelligence service around the official SSK 地単公費マスター and related official materials.

The first rule of this project is simple: deterministic software detects changes; LLMs explain changes after they have been detected.

## Current Scope

This bootstrap contains:

- documentation requested by the product specification
- deterministic domain models for artifacts, snapshots, raw changes, change bundles, and evidence
- CSV master schema validation and semantic diff primitives
- a small fixture-backed web prototype for core screens
- tests for parser and diff behavior

It is not production complete yet. Live official-data crawling, persistent storage, authentication, notifications, and real LLM providers are later phases.

## Repository Layout

```text
apps/web/           Static UI prototype for Changes, Upcoming, Master, Source Health
crawler/            Python deterministic collection/parsing/diff foundation
packages/domain/    Shared JSON schemas and domain notes
schemas/master/     Versioned master schema and field groups
prompts/            LLM prompt templates, kept out of source code
tests/              Parser/diff fixtures and tests
docs/               Investigation, architecture, domain model, master analysis, plan
```

## Run Checks

```bash
PYTHONPATH=crawler python3 -m unittest discover -s tests
PYTHONPATH=crawler python3 -m chitan_watch.cli diff tests/fixtures/master_old.csv tests/fixtures/master_new.csv
```

For local UI preview:

```bash
cd apps/web
python3 -m http.server 4173
```

Then open `http://localhost:4173`.

## Official Starting Points

- SSK 地単公費マスター: https://www.ssk.or.jp/seikyushiharai/titansys/index.html
- MHLW 国公費・地単公費マスター page: https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/iryouhoken/index_00030.html

Do not treat discovered file URLs as permanent. Discover links from seed pages on each crawl.


## Source Discovery

Discover current official artifacts from the SSK seed page without hard-coding the latest file URLs:

```bash
PYTHONPATH=crawler python3 -m chitan_watch.cli discover   https://www.ssk.or.jp/seikyushiharai/titansys/index.html   --allowed-domain www.ssk.or.jp   --allowed-domain www.mhlw.go.jp   --artifact-type master_csv   --artifact-type master_excel   --artifact-type schema   --artifact-type input_guide   --artifact-type manual   --artifact-type examples   --artifact-type faq   --artifact-type mhlw_document   --artifact-type other
```

The command fetches only seed HTML and emits JSON inventory. It does not download or commit official binary artifacts.


## Snapshot Probe

Fetch one selected artifact and emit deterministic Snapshot metadata without writing the payload to Git:

```bash
PYTHONPATH=crawler python3 -m chitan_watch.cli snapshot   https://www.ssk.or.jp/seikyushiharai/titansys/index.files/m_regional_publicly_funded_all_20260803.csv   --artifact-id art_3f9a30bc52854e52
```

HTTP errors must be treated as failed snapshots, not as no-change results.


## CSV Structural Analysis

Analyze a selected CSV artifact without storing the payload:

```bash
PYTHONPATH=crawler python3 -m chitan_watch.cli analyze-csv   https://www.ssk.or.jp/seikyushiharai/titansys/index.files/m_regional_publicly_funded_all_20260803.csv
```

The current live CSV is headerless, so production parsing must map columns from the official item-list document before semantic diffing.


## Item List PDF Extraction

Extract item candidates from the official item-list PDF without committing the PDF payload:

```bash
PYTHONPATH=crawler python3 -m chitan_watch.cli extract-pdf-items /tmp/chitan-siryo2_20260330.pdf
```

The current extraction produces 95 item candidates, while the live CSV has 94 columns. The positional schema is therefore marked `manual_review_required` until the mismatch is reconciled.


## XLSX Structure Analysis

Analyze the official Excel master workbook without committing the payload:

```bash
PYTHONPATH=crawler python3 -m chitan_watch.cli analyze-xlsx /tmp/chitan-20260803_kakutei_chitan.xlsx
```

The current workbook has 47 prefecture sheets. Header rows expose 95 logical item candidates, while CSV has 94 columns; evidence indicates CSV likely excludes new item `79` (`その他制度に係る参考情報`).


## Gated Master Parser

Parse the live 94-column headerless CSV only with explicit candidate-mapping acknowledgement:

```bash
PYTHONPATH=crawler python3 -m chitan_watch.cli parse-master   https://www.ssk.or.jp/seikyushiharai/titansys/index.files/m_regional_publicly_funded_all_20260803.csv   --allow-candidate-mapping
```

Validate candidate identity profiles:

```bash
PYTHONPATH=crawler python3 -m chitan_watch.cli validate-identity   https://www.ssk.or.jp/seikyushiharai/titansys/index.files/m_regional_publicly_funded_all_20260803.csv   --allow-candidate-mapping
```

Without `--allow-candidate-mapping`, parsing is intentionally blocked while the mapping status is `csv_mapping_candidate_requires_review`.


## Positional Master Snapshot Diff

Build deterministic row fingerprints for the gated 94-column master CSV:

```bash
PYTHONPATH=crawler python3 -m chitan_watch.cli snapshot-master \
  tests/fixtures/master_positional_diff_old.csv \
  --allow-candidate-mapping
```

Diff two positional master CSV snapshots with business-identity grouping and row-hash safeguards:

```bash
PYTHONPATH=crawler python3 -m chitan_watch.cli diff-master \
  tests/fixtures/master_positional_diff_old.csv \
  tests/fixtures/master_positional_diff_new.csv \
  --allow-candidate-mapping
```

The diff first matches exact row hashes inside each business identity group. If one old and one new unmatched row remain, it emits a field-level `row_modified` change. If multiple old and new unmatched rows remain, it emits `row_ambiguous` for Admin Review instead of guessing.


## Crawler Run Evaluation

Build a deterministic artifact snapshot manifest from a local spec JSON:

```bash
PYTHONPATH=crawler python3 -m chitan_watch.cli build-manifest \
  tests/fixtures/manifest_spec_old.json \
  --generated-at 2026-08-09T00:00:00+00:00
```

Evaluate a current manifest against a previous manifest, optionally attaching positional master semantic diff output:

```bash
PYTHONPATH=crawler python3 -m chitan_watch.cli evaluate-run current.json \
  --previous-manifest previous.json \
  --master-old-source tests/fixtures/master_positional_diff_old.csv \
  --master-new-source tests/fixtures/master_positional_diff_new.csv \
  --allow-candidate-mapping
```

Run evaluation distinguishes artifact metadata changes from parsed master row changes, and reports `SUCCESS_NO_CHANGE`, `SUCCESS_CHANGED`, `PARTIAL_FAILURE`, `FAILED`, or `SCHEMA_BREAK`.


## Local Crawler Run

Execute a complete local run into an ignored run directory:

```bash
PYTHONPATH=crawler python3 -m chitan_watch.cli run-local \
  tests/fixtures/local_run_spec_old.json \
  --store-dir storage/chitan-watch \
  --run-id run-20260809T000000Z \
  --previous latest \
  --master-artifact-id art_master_csv \
  --allow-candidate-mapping
```

`run-local` copies source payloads into `runs/<run_id>/payloads/`, writes `source-spec.json`, `manifest.json`, `evaluation.json`, optional `master-diff.json`, and updates `sources/<source_id>/latest.txt`. The default store path is under `storage/`, which is ignored by Git.


## Product Slice: Live Local Crawl, API, Web

Run a fixture-backed official crawl into local storage:

```bash
PYTHONPATH=crawler python3 -m chitan_watch.cli run-official-local \
  https://www.ssk.or.jp/seikyushiharai/titansys/index.html \
  --store-dir storage/chitan-watch \
  --artifact-type master_csv \
  --previous latest \
  --allow-candidate-mapping
```

For live official use, omit `--seed-html-file` and `--source-map-file`; fetched payloads are copied under ignored `storage/chitan-watch/runs/<run_id>/payloads/`.

Serve the local API and Web UI together:

```bash
PYTHONPATH=crawler python3 -m chitan_watch.cli serve \
  --store-dir storage/chitan-watch \
  --web-dir apps/web \
  --port 8765
```

Then open `http://127.0.0.1:8765`. The Web UI reads `/api/runs`, `/api/changes`, and `/api/source-health`; if the API is unavailable, it falls back to fixture data.


## Master CSV Version and Diff Payloads

Static export now publishes CSV-first data products for the Web viewer:

```text
static/master-versions.json
static/master-diffs.json
static/master-diffs/<diff_id>.json
```

The first comparison scope is adjacent observed versions. Arbitrary two-version comparison is intentionally deferred. Public payloads expose official URLs, hashes, parser status, row counts, bounded sample rows, and field-level diff details, but not local `storage/**` paths.

## Gemini Interpretation Setup

Gemini is optional and runs only during server-side/local/static export, never in browser JavaScript. Without a key, export still succeeds and writes `static/llm-status.json` with disabled status.

For local manual export, keep the key out of shell history. Put it in an ignored local env file such as `.env.local`:

```text
GEMINI_API_KEY=your-key-here
```

Then load it without printing the value and run export:

```bash
set -a
. ./.env.local
set +a
PYTHONPATH=crawler python3 -m chitan_watch.cli export-static \
  --store-dir storage/chitan-watch \
  --output-dir public \
  --web-dir apps/web \
  --site-url https://example.test/chitan-watch \
  --enable-llm
```

Do not commit `.env.local`, paste the key into scripts, or expose it in browser/static assets.

For GitHub Actions, set the repository secret:

```text
Settings -> Secrets and variables -> Actions -> New repository secret -> GEMINI_API_KEY
```

Then run the `Publish static Chitan Watch feed` workflow with `enable_llm` checked. Gemini output is stored as generated interpretation metadata in `static/llm-interpretations.json`; deterministic CSV diff evidence remains the source of truth. Each key point, factual basis, inference, review recommendation, and related context entry must carry provided evidence ids such as a diff id, row change id, or official source URL.

## RSS Subscription

When the local server is running, RSS readers can subscribe to:

```text
http://127.0.0.1:8765/rss.xml
```

The same feed is also available at `/feeds/changes.xml`. To emit the feed XML from the CLI:

```bash
PYTHONPATH=crawler python3 -m chitan_watch.cli rss \
  --store-dir storage/chitan-watch \
  --site-url http://127.0.0.1:8765
```

The Web UI advertises the feed with an RSS auto-discovery link, so normal feed readers can detect it from the site URL.


## Static Publishing

Export serverless Web/RSS assets from local run storage:

```bash
PYTHONPATH=crawler python3 -m chitan_watch.cli export-static \
  --store-dir storage/chitan-watch \
  --output-dir public \
  --web-dir apps/web \
  --site-url https://<owner>.github.io/<repo>
```

The exported directory contains `index.html`, `app.js`, `styles.css`, `rss.xml`, `feeds/changes.xml`, and `static/*.json`. `public/` is ignored by Git because it is generated output.

GitHub Actions workflow `.github/workflows/publish-static.yml` can run this on a schedule and deploy to GitHub Pages without custom secrets. See `docs/publication.md` before making the repository public.
