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
