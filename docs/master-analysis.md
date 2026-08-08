# Master Analysis

## Bootstrap schema stance

The current repository has a deliberately small draft schema in `schemas/master/2026-03-30.yaml`. It is only enough to exercise parser and diff behavior. It must be reconciled with the official item list before production use.

## Required official-data checks

Before broad parser implementation, inspect the latest official CSV and item list for:

- encoding
- delimiter
- header presence
- column count
- official field names
- record count
- nullable public funding number patterns
- subdivision usage
- date representation
- duplicate identity candidates
- field groups for eligibility, copayment, benefit, validity, and metadata

## Identity policy

Primary business grouping candidate:

```text
prefecture_code + municipality_code + public_funding_number + program_subdivision_code
```

Live validation showed this is not unique at row level. The positional diff therefore treats it as a business identity group, then uses deterministic full-row hashes to match unchanged rows inside the group. If exactly one unmatched old row and one unmatched new row remain, the diff emits a field-level modification. If multiple old and new unmatched rows remain, the diff emits `row_ambiguous` and routes the group to Admin Review. LLM must not choose among ambiguous row matches.

## Schema break policy

Missing required columns stop semantic diff and produce `SCHEMA_BREAK`. Additional columns are allowed during bootstrap but should be reviewed before production.


## Live CSV snapshot metadata

`ORD-003` probed the current SSK CSV artifact discovered from the seed page:

- URL: https://www.ssk.or.jp/seikyushiharai/titansys/index.files/m_regional_publicly_funded_all_20260803.csv
- HTTP status: 200
- Content-Type: text/csv
- Content-Length: 9,958,587 bytes
- Last-Modified: Mon, 03 Aug 2026 01:35:44 GMT
- SHA-256: 4f768cfe38af951701aba24f79723333961ee2ed9db0a914c14dedec902399bf

The CSV bytes were not committed. Next parser work must inspect header/encoding/column semantics from an approved runtime artifact or object-storage snapshot.


## Live CSV structural analysis

`ORD-004` analyzed the current SSK CSV structurally without committing its payload:

- Encoding: `utf-8-sig`
- Delimiter: comma
- Header row: not present
- Column count: 94
- Record count: 22,975
- Inconsistent row count: 0
- SHA-256: `4f768cfe38af951701aba24f79723333961ee2ed9db0a914c14dedec902399bf`

Implications:

- The parser cannot rely on CSV headers.
- `schemas/master/2026-03-30.yaml` must be generated from or reconciled with the official item-list PDF before semantic parsing.
- Record identity fields are still unresolved because column positions and official item names must be mapped first.


## Item-list PDF extraction

`ORD-005` extracted the official item-list PDF text with Poppler `pdftotext`:

- Source PDF: https://www.ssk.or.jp/seikyushiharai/titansys/index.files/siryo2_20260330.pdf
- PDF SHA-256: `5cff5c0020ff089019108d15f73370efefc329bbc37b2cd4961f622becdee98c`
- PDF metadata: Excel-origin PDF, A3, 6 pages
- Extracted item candidates: 95
- Live CSV columns: 94

The repository now contains `schemas/master/2026-03-30.positional.json` as a candidate mapping artifact. It is intentionally marked `manual_review_required` because direct use would risk a one-column semantic shift.

Likely reconciliation work:

- confirm whether `その他制度に係る参考情報` is present in the CSV payload or only in the registration system item list
- inspect sample rows by position, especially the tail columns around new item numbers 78-91
- verify whether PDF text extraction split or merged any visually grouped item row
- cross-check with the Excel master file if allowed, because PDF layout may obscure true column positions


## Excel reconciliation

`ORD-006` inspected the official Excel master workbook structure without committing the workbook payload:

- Source Excel: https://www.ssk.or.jp/seikyushiharai/titansys/index.files/20260803_kakutei_chitan.xlsx
- Excel SHA-256: `26529eed5f088cccf206b4e3b53f5345cc1c790f70fcf6c9d63564cd8327bf99`
- Workbook sheets: 47, apparently one sheet per prefecture code
- Example sheet dimension: `A1:DV6176`
- Header row logical item candidates: 95
- Last logical item candidate: column `CQ`, new item `79`, `その他制度に係る参考情報`
- Live CSV columns: 94

Reconciliation finding:

The Excel/PDF item list includes 95 logical item candidates, but the CSV export contains 94 columns. The strongest current explanation is that CSV positions 1-94 correspond to Excel/PDF candidates through new item `78` (`公費適用優先順位`), and new item `79` (`その他制度に係る参考情報`) is workbook-only / excluded from CSV export.

The positional schema now records:

- `fields`: all 95 PDF/Excel candidates
- `csv_fields`: 94-column CSV mapping candidate
- `excluded_from_csv_candidates`: new item `79`
- `mapping_status`: `csv_mapping_candidate_requires_review`

This is now strong enough to start a gated parser prototype, but still requires manual review before production use.


## Gated parser and identity validation

`ORD-007` implemented a positional 94-column parser using `csv_fields`. The parser refuses to read source bytes unless either:

- the schema mapping status is production-approved, or
- the caller explicitly passes `--allow-candidate-mapping`

This keeps the current mapping useful for investigation while preventing accidental production use.

`ORD-008` validated the candidate identity fields from the live CSV:

| Profile | Unique keys | Duplicate keys | Rows in duplicate groups |
| --- | ---: | ---: | ---: |
| 3+4+8+9 | 20,836 | 1,306 | 3,445 |
| 3+4+8+9+10+11 | 21,619 | 911 | 2,267 |
| 3+4+8+9+1 | 22,414 | 528 | 1,089 |
| 3+4+8+9+1+10+11 | 22,845 | 113 | 243 |
| full row | 22,975 | 0 | 0 |

Findings:

- `都道府県番号 + 市区町村コード + 公費負担者番号 + 事業内区分コード` is not unique at row level.
- Adding validity dates or program name reduces but does not eliminate duplicates.
- Full rows are unique, so duplicate groups represent multiple distinct rule/condition rows under the same business grouping, not duplicate records.
- Record matching must model a business identity group plus row-level condition identity/fingerprint. Ambiguous matching must remain review-gated.


## Row fingerprint diff policy

The current row fingerprint algorithm is `chitan-watch-positional-row-v1`:

- `row_hash` hashes all 94 mapped CSV item values with the positional schema version.
- `condition_fingerprint` hashes non-identity item values and records that identity items `3`, `4`, `8`, and `9` were excluded.
- `snapshot-master` emits row fingerprints, business identity counts, and duplicate business identity summaries.
- `diff-master` compares two positional snapshots using exact row hashes first, then conservative singleton modification matching.

This makes row-level comparison useful before production mapping approval while preserving the explicit `--allow-candidate-mapping` gate.
