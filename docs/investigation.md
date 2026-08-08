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


## Live SSK discovery inventory

`ORD-002` added deterministic seed-page discovery and ran it against the SSK hub on 2026-08-08. With monitoring-oriented artifact-type filters, the current inventory contains:

| Type | Title | URL |
| --- | --- | --- |
| master_excel | 地単公費マスター確定事業一覧（令和8年8月3日時点）（Excel） | https://www.ssk.or.jp/seikyushiharai/titansys/index.files/20260803_kakutei_chitan.xlsx |
| master_csv | 地単公費マスター確定事業一覧（令和8年8月3日時点）（CSV UTF-8） | https://www.ssk.or.jp/seikyushiharai/titansys/index.files/m_regional_publicly_funded_all_20260803.csv |
| other | 地単公費マスターの整備について | https://www.ssk.or.jp/seikyushiharai/titansys/index.files/siryo0_20250603.pdf |
| manual | 基本操作マニュアル | https://www.ssk.or.jp/seikyushiharai/titansys/index.files/siryo1_20260330.pdf |
| schema | 地単公費マスター項目一覧 | https://www.ssk.or.jp/seikyushiharai/titansys/index.files/siryo2_20260330.pdf |
| input_guide | 地単公費マスター項目入力要領 | https://www.ssk.or.jp/seikyushiharai/titansys/index.files/siryo3_20260330.pdf |
| examples | 地単公費マスター入力例 | https://www.ssk.or.jp/seikyushiharai/titansys/index.files/siryo4_20250704.pdf |
| faq | FAQ | https://www.ssk.or.jp/seikyushiharai/titansys/index.files/siryo5_FAQ_20250530.pdf |
| other | 地単公費の請求事務の各自治体の委託状況 | https://www.ssk.or.jp/seikyushiharai/titansys/index.files/itakujoukyou_202606.pdf |
| mhlw_document | 令和8年1月28日全国説明会 | https://www.mhlw.go.jp/stf/newpage_67679.html |
| mhlw_document | 国公費・地単公費マスター関連ページ | https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/iryouhoken/index_00030.html |

The crawler still needs an explicit relevance policy for broad HTML navigation links. `--artifact-type` filtering is currently the safe operational path for seed-page inventory.
