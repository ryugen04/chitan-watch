# CSV Diff Viewer / Linked Context / Gemini Integration Roadmap

## Current Status

Status: draft for user review, not approved for implementation.
Target root: `/home/glaucus03/dev/projects/chitan-watch`
Created: 2026-08-10

## Original Request

CSVをエントリーポイントにするのであれば、CSVのdiff管理、Web上でのビュアー、版ごとの比較機能、CSV差分に紐づく情報のWeb表示、Gemini API keyを使った真面目なLLM機能組み込みを、先に全体像と具体計画として練り込む。

## Correction From Previous Direction

前の進め方は、自治体ページやRSS通知の小さな改善に寄りすぎていた。ここからは「CSV masterを中心にしたプロダクト」を主軸にする。

重要な考え方:

- CSVは単なる添付ファイルではなく、プロダクトの一次エントリーポイント。
- RSSは更新入口だが、ユーザーが本当に見るべきものは、版、差分、根拠、制度文脈、影響解釈。
- LLMは検知の代替ではなく、決定論的diffを読める形にする補助層。
- Gemini API keyはCI/ローカル生成側だけで使い、静的Webには絶対に出さない。


## Child Plans

This roadmap is intentionally broad. Implementation should proceed through reviewed child plans, not by editing product code directly from this parent.

| Child plan | Scope | Implementation approval |
|---|---|---|
| `.codex/plans/2026081008-csv-diff-data-contract-and-projection.md` | CSV version registry, diff registry, API/static JSON contracts, tests | Required before Phase 1/2 edits |
| `.codex/plans/2026081008-web-csv-diff-viewer-and-context.md` | Web UX, version viewer, comparison UI, linked context display | Required before Phase 3/4 edits |
| `.codex/plans/2026081008-gemini-llm-integration.md` | Gemini provider, secret handling, prompts, structured output, workflow wiring | Required before Phase 5 edits |

## Phase Dashboard

| Phase | Name | Status | Gate |
|---|---|---|---|
| 0 | Scope approval | In review | User accepts or edits this roadmap |
| 1 | Data contract design | Planned | Child plan approved |
| 2 | Master projection implementation | Planned | Static JSON tests pass |
| 3 | Web viewer | Planned | UI contract reviewed |
| 4 | Linked context display | Planned | Evidence/context labels reviewed |
| 5 | Gemini integration | Planned | Secret policy and invocation policy approved |
| 6 | Documentation/operator guide | Planned | Local and GitHub setup verified |
| 7 | Publish verification | Planned | Public Pages artifacts verified |

## Workflow Axes

| Axis | Direction |
|---|---|
| Product | CSV versioned diff viewer as the core experience |
| Data | Deterministic snapshots, normalized rows, field-level diffs, linked sources |
| Web | Static GitHub Pages compatible viewer and comparison UI |
| LLM | Optional Gemini enrichment after deterministic diff exists |
| Security | Secrets only in env / GitHub Actions secrets, never in static assets |
| Delivery | Additive static JSON payloads first, later backend/database possible |
| Review | Human review required for ambiguous row matching and LLM inference |

## Allowed Paths For Future Implementation

- `crawler/chitan_watch/**`
- `apps/web/**`
- `tests/**`
- `docs/**`
- `README.md`
- `prompts/**`
- `.github/workflows/**`
- `.codex/plans/**`
- `.careflow/cases/**` for workflow state only

## Forbidden Paths / Boundaries

- Do not commit `storage/**` payloads or downloaded official CSV/PDF/XLSX files.
- Do not commit `.env`, API keys, tokens, local cache, local generated secrets, or machine-specific paths.
- Do not expose `GEMINI_API_KEY` or Gemini request payloads containing secrets in `public/**`, RSS, browser JS, logs, or committed fixtures.
- Do not let Gemini create or mutate deterministic diff facts.
- Do not make Gemini mandatory for crawl, export, RSS, or Web display.
- Do not collapse municipality context into SSK CSV source authority.

## Target Product Shape

### 1. CSV Version Registry

The site should answer:

- What CSV versions have been observed?
- Which one is latest?
- What was the official source URL, title, basis date, retrieved time, SHA-256, file size, and run id?
- Was the CSV parse successful, blocked by candidate schema mapping, or failed?
- Which previous CSV version was compared?

Suggested static payload:

```text
/static/master-versions.json
```

Candidate shape:

```json
{
  "latest_run_id": "run-...",
  "versions": [
    {
      "version_id": "run-...:art_...",
      "run_id": "run-...",
      "artifact_id": "art_...",
      "title": "地単公費マスター確定事業一覧（令和8年8月3日時点）...",
      "basis_date_label": "令和8年8月3日時点",
      "basis_date_iso": "2026-08-03",
      "source_url": "https://www.ssk.or.jp/...csv",
      "retrieved_at": "...",
      "sha256": "...",
      "content_length": 9958400,
      "row_count": 12345,
      "schema_id": "2026-03-30.positional",
      "parser_status": "parsed"
    }
  ]
}
```

### 2. CSV Diff Registry

The site should answer:

- Which CSV versions were compared?
- How many rows were added, removed, modified, unchanged, or ambiguous?
- Which fields changed most?
- Which prefectures/municipalities changed most?
- Which changes require review?
- Which ChangeEvents came from the diff?

Suggested static payload:

```text
/static/master-diffs.json
/static/master-diffs/<diff_id>.json
```

Candidate summary shape:

```json
{
  "diffs": [
    {
      "diff_id": "run-new:master-csv:run-old",
      "old_version_id": "run-old:art_...",
      "new_version_id": "run-new:art_...",
      "old_basis_date_label": "令和8年7月21日時点",
      "new_basis_date_label": "令和8年8月3日時点",
      "summary": {
        "old_record_count": 0,
        "new_record_count": 0,
        "added_row_count": 0,
        "removed_row_count": 0,
        "modified_row_count": 0,
        "ambiguous_group_count": 0
      },
      "top_changed_fields": [
        { "field": "item_10", "label": "開始日", "count": 12 }
      ],
      "review_required": false
    }
  ]
}
```

Detailed diff shape should include row changes, field changes, stable ids, source run ids, official source URLs, and links to generated ChangeEvents.

### 3. Web: Master CSV Viewer

Primary screens:

- `#master`: latest CSV version overview and recent versions.
- `#master-version/<version_id>`: metadata for one CSV version, row count, parse status, source URL, file identity.
- `#master-compare/<diff_id>`: version-to-version comparison summary and row/field diff table.
- `#change-detail/<change_id>`: existing change detail, enhanced with CSV diff linkage.

Core UI controls:

- Version selector: old version / new version.
- Diff type filters: added / removed / modified / ambiguous.
- Severity/review filters.
- Field filters for important columns.
- Search by public funding number, prefecture code, municipality code, program name.
- Compact table with stable dimensions so long Japanese field values do not break layout.

The Web should not try to render the entire CSV by default if it is large. It should render summaries, searchable diff rows, and paginated/detail subsets.

### 4. Linked Context Display

Each CSV diff row should be able to show:

- Deterministic row identity: public funding number, prefecture, municipality, program subdivision.
- Changed fields with before/after values.
- Relevant official source: SSK CSV URL and run artifact metadata.
- Related document/source layer if known: registration docs, FAQ, policy page, municipality context page.
- Related ChangeEvent id and RSS item link.
- Review status: deterministic, inferred, unresolved, LLM-assisted.

Important boundary:

- A municipality page can be linked as context, not as proof that the SSK CSV changed.
- Gemini can propose a link/explanation, but deterministic source and evidence remain separate.

### 5. Gemini Integration

Use Gemini after deterministic diff generation. Gemini should not call from browser JavaScript. It should run in local CLI / GitHub Actions / future backend only.

Environment setting:

```text
GEMINI_API_KEY=<user-provided key>
```

GitHub Actions setting location:

```text
GitHub repository -> Settings -> Secrets and variables -> Actions -> New repository secret -> GEMINI_API_KEY
```

Optional local setting:

```bash
export GEMINI_API_KEY='...'
```

Do not commit `.env` with this value.

Provider behavior:

- If `GEMINI_API_KEY` is missing: deterministic-only export, clear `llm_status: disabled` in metadata.
- If present: enrich selected diff/change summaries with bounded structured JSON.
- Network/API failure: export still succeeds with deterministic data and `llm_status: failed`.
- LLM output stored as generated interpretation metadata, not as source truth.

Suggested static payloads:

```text
/static/llm-status.json
/static/llm-interpretations.json
```

Suggested event enrichment fields:

```json
{
  "llm_interpretation": {
    "provider": "gemini",
    "model": "...",
    "generated_at": "...",
    "status": "success",
    "summary_for_humans": "...",
    "fact_basis": ["deterministic CSV diff", "official SSK source URL"],
    "inferences": ["..."],
    "uncertainties": ["..."],
    "recommended_review": "..."
  }
}
```

Prompt/schema principles:

- Input contains only bounded diff rows and official metadata, not secrets.
- Output JSON schema is strict.
- Require fact/inference separation.
- Require uncertainty statements.
- Require no medical/legal advice phrasing beyond operational review guidance.
- Require citations to existing evidence ids/source URLs only; no invented URLs.

### 6. RSS / Notification Relationship

RSS should remain a trigger, not the full analysis surface.

RSS item should include:

- Version pair if CSV diff exists.
- Summary counts.
- Link to `#master-compare/<diff_id>`.
- Link to `#guide` for interpretation guidance.
- LLM summary only if generated and explicitly labeled as LLM-assisted.

RSS should not include huge diff tables.

## Proposed Phases

### Phase 0: Scope Approval

Goal: agree this plan before implementation.

Outputs:

- This plan file reviewed and edited.
- Explicit approval phrase from user before coding.

Checkpoint questions:

- Is GitHub Pages static-only still the intended delivery target for this milestone?
- Should Gemini run on every scheduled crawl, only when diff count is non-zero, or only manual workflow dispatch?
- Should Web initially show all row diffs or cap/paginate them?
- Which CSV fields are “business critical” for severity and UI emphasis?

### Phase 1: Data Contract Design

Goal: define additive static JSON contracts before UI work.

Outputs:

- `docs/csv-diff-product-contract.md`
- Tests describing `master-versions.json` and `master-diffs.json` payloads.

Acceptance:

- Existing `/api/runs`, `/api/changes`, `/api/source-health`, and RSS remain backward compatible.
- New payloads can be generated from current `LocalRunStore` without database migration.

### Phase 2: Master Version / Diff Projection

Goal: turn existing stored runs and `master-diff.json` into product-ready JSON.

Implementation candidates:

- `crawler/chitan_watch/master_projection.py`
- Add API endpoints:
  - `/api/master/versions`
  - `/api/master/diffs`
  - `/api/master/diffs/<diff_id>`
- Add static exports:
  - `static/master-versions.json`
  - `static/master-diffs.json`
  - `static/master-diffs/<diff_id>.json`

Acceptance:

- Fixture runs produce version records.
- Runs with previous CSV produce diff records.
- Runs without diff produce version records but no fake diff.
- Ambiguous row groups remain explicit review items.

### Phase 3: Web Viewer and Comparison UI

Goal: make CSV versions and diffs inspectable in the browser.

Implementation candidates:

- Extend `apps/web/app.js` state loader for master payloads.
- Replace the current shallow `#master` table with:
  - version list
  - latest version panel
  - diff summary cards
  - comparison table
  - row/field detail drilldown
- Update `apps/web/styles.css` for dense operational tables.

Acceptance:

- User can identify latest CSV version.
- User can open a version-to-version diff.
- User can filter row changes and inspect field before/after values.
- Change detail links back to relevant CSV diff/version.

### Phase 4: Linked Context Layer

Goal: show related official/context info next to diff rows without overstating certainty.

Implementation candidates:

- Add linking helpers that attach source layer metadata and related ChangeEvents to diff rows.
- Expose context cards in Web detail views.

Acceptance:

- CSV row diff has official SSK source evidence.
- Related MHLW/registration/municipality context can be displayed as context.
- UI labels distinguish evidence vs context vs inference.

### Phase 5: Gemini Provider

Goal: integrate Gemini in a controlled, optional way.

Implementation candidates:

- Replace/extend `crawler/chitan_watch/llm.py` with:
  - `DisabledLLMProvider`
  - `GeminiLLMProvider`
  - `load_llm_provider_from_env()`
  - structured output validation
- Add prompts under `prompts/` for CSV diff interpretation.
- Add CLI/export option:
  - `--enable-llm`
  - maybe `--llm-max-events`
- Add workflow env:
  - `GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}`

Acceptance:

- No key: tests/static export pass with disabled status.
- Fake/mocked key/client: request plumbing and schema parsing tested.
- API failure: deterministic export still succeeds.
- Static assets never contain the key.

### Phase 6: Documentation and Operator Guide

Goal: make the system operable by someone other than the implementer.

Outputs:

- README section: Gemini key setup.
- Docs section: CSV diff viewer semantics.
- Docs section: fact/evidence/inference boundaries.
- Security note: no browser-side LLM calls.

Acceptance:

- User can set `GEMINI_API_KEY` in GitHub Actions secrets.
- User can run locally with `export GEMINI_API_KEY=...`.
- User understands LLM output is explanatory, not authoritative.

### Phase 7: Publish and Verify

Goal: deploy to GitHub Pages and verify public artifacts.

Verification:

- Unit tests.
- Static export smoke with fixture diff.
- Optional disabled-LLM smoke.
- Public checks for:
  - `static/master-versions.json`
  - `static/master-diffs.json`
  - `static/llm-status.json`
  - `rss.xml`
  - `app.js`

## Test Plan

Minimum tests before implementation completion:

- `tests/test_master_projection.py`
  - version extraction
  - diff summary extraction
  - detailed diff payload shape
  - no fake diff when previous CSV missing
- `tests/test_static_export.py`
  - new static JSON files exist
  - old static files remain
- `tests/test_api.py` or existing product slice tests
  - `/api/master/versions`
  - `/api/master/diffs`
- `tests/test_llm.py`
  - disabled provider
  - env provider selection
  - mocked Gemini response parsing
  - failure fallback
- `tests/test_product_slice.py`
  - Web app references master payloads and Gemini status
- Existing full suite:
  - `PYTHONPATH=crawler python3 -m unittest discover tests`
  - `node --check apps/web/app.js`
  - `git diff --check`

## Approval Gates

Implementation must not start until the user explicitly approves this plan or a revised version.

Separate approval recommended for:

1. Data contract names and shapes.
2. Web UI scope for first release.
3. Gemini invocation policy.
4. GitHub Actions secret wiring.
5. Public deployment.



## Anti-Shrink Product Gates

These gates are added specifically to prevent the product from shrinking back into RSS/source-health or a narrow one-file notification tool.

| Gate | Pass condition |
|---|---|
| CSV-first public entry | The public root page loads the Master CSV experience by default, or presents it as the unmistakable first action above changes/RSS. |
| Version registry completeness | Version records handle duplicate SHA, repeated basis date, title/URL drift, multiple CSV artifacts, parse failures, and explicit ordering. |
| Comparison semantics | The plan states whether arbitrary observed-version comparison is supported. Initial default: adjacent observed-version diffs are persisted; arbitrary comparison may be computed locally later and must be visibly unavailable until implemented. |
| CSV viewer, not only diff viewer | A user can inspect the latest/current CSV version even when there is no diff, through searchable or paginated row samples plus metadata. |
| Context contract | Related context has ids, source layer, freshness, relation reason, confidence, and missing-context behavior. |
| Gemini production behavior | Timeouts, retries, batching, token/row caps, cache policy, cost guardrails, and failure fallback are specified before implementation. |
| Public safety | Static output is scanned for secrets, HTML escaping/XSS is preserved, prompt-injection from official/context text is treated as untrusted input. |
| Published behavior | Public verification opens real routes and RSS links, not just static files. |

## Recommended Defaults For Approval

If the user says to proceed without choosing every option, use these defaults.

| Decision | Default | Reason |
|---|---|---|
| Delivery shape | GitHub Pages static-only for this milestone, with root page CSV-first | Keeps RSS/Slack subscription simple and avoids server operations |
| First implementation slice | Data contract and projection, then Web viewer, then Gemini | Prevents UI and LLM from inventing a data model |
| Master payload size | Split diff detail per `diff_id`, cap first detail page at 500 row changes with metadata, and expose current-version row search/sample separately | Works on static hosting and avoids huge first-load JSON |
| Gemini invocation | Disabled unless `--enable-llm` is passed; once wired, scheduled runs use it only when deterministic diff count is non-zero | Avoids silent cost/noise and keeps deterministic export primary |
| Gemini key name | `GEMINI_API_KEY`, with `GOOGLE_API_KEY` as fallback | Clear user-facing setup, compatible with Google examples |
| LLM placement | Separate `llm-interpretations.json` linked by target id | Keeps deterministic event/diff facts clean |
| CSV schema warning | Keep candidate mapping warning visible until schema mapping is formally accepted | Prevents false confidence in parsed row semantics |
| Municipality context | Show as related context, never as proof of SSK CSV changes | Preserves source authority boundaries |
| RSS content | Summary counts and link to compare page, no large tables | RSS remains trigger, Web remains analysis surface |

## Implementation Start Rule

After this roadmap is accepted, implementation still starts with the child plan `.codex/plans/2026081008-csv-diff-data-contract-and-projection.md`. The first code changes should be limited to additive projection/API/static export work and tests. Web and Gemini code changes wait until that data contract is passing locally.

## Open Decisions

1. Gemini invocation timing:
   - Option A: only manual workflow dispatch.
   - Option B: scheduled crawl only when deterministic diff count > 0.
   - Option C: always on scheduled crawl when key exists.
   - Recommended initial: Option B, with manual override later.

2. Diff payload size:
   - Option A: export all row diffs.
   - Option B: export summaries plus capped rows, keep full details for later backend.
   - Option C: split detailed diff JSON per run/diff with pagination metadata.
   - Recommended initial: Option C for GitHub Pages compatibility.

3. LLM output placement:
   - Option A: attach to each ChangeEvent.
   - Option B: separate `llm-interpretations.json` linked by event/diff id.
   - Recommended initial: Option B to keep deterministic event schema clean.

4. CSV row identity confidence:
   - Current candidate mapping requires explicit `--allow-candidate-mapping`.
   - Need decide whether public UI should show a persistent warning until schema mapping is fully accepted.
   - Recommended: show persistent warning.

5. Official field labels:
   - Current field labels are partial.
   - Need decide whether Phase 1 must complete full 94-field label map before rich UI.
   - Recommended: at least label high-impact fields first, then expand.

## Rollback / Recovery

- New JSON endpoints are additive; if broken, remove them from static export and Web loader while keeping old RSS/changes/source-health working.
- Gemini can be disabled by removing `GEMINI_API_KEY` or not passing `--enable-llm`.
- If Gemini returns invalid JSON, store disabled/failed status and continue deterministic export.
- If public Pages verification fails, do not publish follow-up changes until `static/*` contracts are fixed locally.
- If a secret is ever printed or committed, treat as security incident: revoke key immediately, purge logs if possible, and rotate secret.


## Approval Checklist For Next Implementation Slice

The user can approve the first implementation slice by saying the defaults are acceptable. Approval means only Phase 1 and Phase 2 start, not the whole product.

Required checklist for Phase 1/2 start:

- Accept `static/master-versions.json` as the version registry file.
- Accept `static/master-diffs.json` and `static/master-diffs/<diff_id>.json` as the diff registry/detail files.
- Accept adjacent observed-version diffs as the first comparison scope.
- Accept root page becoming CSV-first after Web phase, while data phase only prepares payloads.
- Accept that full CSV rendering is deferred; first viewer uses metadata, row samples, search/filter-ready diff details, and explicit limits.
- Accept that Gemini implementation waits until data contract and Web contract are stable.

If any item is not accepted, revise the relevant child plan before implementation.

## Immediate Next Step After Approval

Create a child implementation plan for Phase 1 and Phase 2 only:

```text
.codex/plans/2026081008-csv-diff-data-contract-and-projection.md
```

That child plan should contain concrete file edits and tests for static `master-versions` / `master-diffs` payloads. Web and Gemini implementation should not begin until the data contract is reviewed.
