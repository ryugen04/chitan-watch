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

Primary candidate:

```text
prefecture_code + municipality_code + public_funding_number + program_subdivision_code
```

If this is duplicated in either old or new snapshot, the diff result is `AMBIGUOUS` and must route to Admin Review. LLM must not choose the matching row.

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
