# Investigation

## Official seed pages checked on 2026-08-08

- SSK: https://www.ssk.or.jp/seikyushiharai/titansys/index.html
- MHLW: https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/iryouhoken/index_00030.html
- MHLW 2026-01-28 briefing: https://www.mhlw.go.jp/stf/newpage_67679.html

## Current SSK hub observations

The SSK hub publishes the latest 地単公費マスター as Excel and CSV UTF-8 files. As observed on 2026-08-08, the latest label on the hub is `令和8年8月3日時点`.

The same hub links to:

- 地単公費マスターの整備について
- 基本操作マニュアル
- 地単公費マスター項目一覧
- 地単公費マスター項目入力要領
- 地単公費マスター入力例
- FAQ
- MHLW explanation materials

## Product implications

- The crawler must begin from seed pages and classify discovered links each run.
- The latest CSV URL must not be hard-coded as a permanent source of truth.
- File update date and effective date are separate concepts.
- `NO_CHANGE` and `CRAWL_FAILED` must stay separate run states.

## Still required before production parser work

- Download the latest CSV under an approved storage policy.
- Confirm encoding, delimiter, header presence, column count, date format, nullable fields, and duplicate identity patterns.
- Compare the CSV headers against the official item list PDF.
- Decide whether official files may be retained as test fixtures or whether anonymized fixtures are required.
