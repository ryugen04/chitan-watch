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
