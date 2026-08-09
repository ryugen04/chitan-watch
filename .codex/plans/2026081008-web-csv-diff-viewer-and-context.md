# Web CSV Diff Viewer And Context Plan

Parent plan: `.codex/plans/2026081008-csv-diff-viewer-gemini-roadmap.md`
Status: draft for review, not approved for implementation.
Target root: `/home/glaucus03/dev/projects/chitan-watch`

## Original Request

CSV diffをWebで見られるようにし、版ごとの比較、差分に紐づく情報、通知から理解画面へ進む導線を作る。

## Goal

Make the first screen useful for someone who wants to understand what changed in the official CSV, not only that something changed.

## UX Principle

The Web app should behave like an operational viewer, not a landing page. It should prioritize scan, compare, filter, and drilldown.


## CSV-First Public Entry Requirement

The public URL must not make users start from generic change cards. The root experience should load `#master` by default, or the first viewport must make Master CSV the primary action.

Implementation default:

- Change the default route from `changes` to `master` after the data contract exists.
- Navigation order starts with `Master CSV`, then `Changes`, `Upcoming`, `Source Health`, `Guide`.
- RSS links for CSV diff events point to `#master-compare/<diff_id>` when a diff id exists.

Acceptance check:

- Opening the public site without a hash shows latest CSV version and available diff summaries in the first viewport.

## Routes

| Route | Purpose | Data |
|---|---|---|
| `#master` | Latest CSV, version history, diff index | `master-versions`, `master-diffs` |
| `#master-version/<version_id>` | One CSV version metadata plus bounded row/sample inspection | `master-versions`, optional version detail |
| `#master-compare/<diff_id>` | Version pair comparison | `master-diffs/<diff_id>` |
| `#master-row/<diff_id>/<row_change_id>` | Row-level detail | diff detail |
| `#change-detail/<change_id>` | Existing event detail with CSV links | `changes`, diff details |
| `#guide` | Reading guide | static app text |

## Master Page Layout

Top band:

- Latest CSV title.
- Basis date.
- Source URL.
- SHA prefix.
- Row count.
- Parser/mapping status.
- Compare-to previous version button when diff exists.

Version history:

- Table with basis date, run id, retrieved time, row count, hash, source URL.
- Compact controls for selecting two versions.

Diff index:

- Cards or table rows for version pairs.
- Counts for added, removed, modified, ambiguous.
- Review-required marker.

## Compare Page Layout

Summary strip:

- Old version and new version.
- Count summary.
- Field hot spots.
- Jurisdiction hot spots.
- Links to source CSVs.

Controls:

- Search input for public funding number, municipality code, program name.
- Type filter for added, removed, modified, ambiguous.
- Field filter.
- Review filter.

Diff table columns:

| Column | Meaning |
|---|---|
| Type | added/removed/modified/ambiguous |
| Jurisdiction | prefecture and municipality code |
| Public funding number | identity field |
| Program | item_1 or known name field |
| Changed fields | short labels |
| Effective period | start/end fields when known |
| Review | required/none |
| Links | row detail, ChangeEvent |

Row detail panel:

- Identity and row hashes.
- Before/after table for changed fields.
- Evidence source card for SSK CSV.
- Related ChangeEvent card.
- Related context cards.
- LLM interpretation card when present, labeled as generated explanation.

## Linked Context Display

Context categories:

| Label | Meaning | UI wording |
|---|---|---|
| Evidence | Deterministic CSV diff and official source metadata | `根拠` |
| Context | MHLW docs, registration docs, municipality pages | `関連文脈` |
| Inference | Gemini or rule-based interpretation | `解釈` |
| Review | Ambiguous matching or uncertain impact | `要確認` |

Hard boundary:

- Municipality context may help users understand a local制度, but it does not prove the SSK CSV row changed.
- Gemini text is never shown above deterministic diff facts.

## Data Loading

Extend `loadState()` to fetch:

```text
/api/master/versions or static/master-versions.json
/api/master/diffs or static/master-diffs.json
/static/llm-status.json when available
```

Fetch detail JSON lazily when opening a compare route:

```text
/api/master/diffs/<diff_id> or static/master-diffs/<diff_id>.json
```

Fallback state should include a small fixture diff so the UI remains inspectable without API/static files.

## Styling

- Dense operational tables.
- No oversized hero layout.
- Stable column widths and wrapped long Japanese text.
- Clear badges for deterministic, context, LLM-assisted, and review-required.
- No nested cards.

## Acceptance Criteria

- `#master` is useful as the default CSV entry point.
- User can open a diff and inspect row-level before/after values.
- User can move from a ChangeEvent to the relevant CSV diff when linked.
- Evidence/context/inference labels are visually distinct.
- Missing master payloads degrade gracefully.
- If arbitrary selected-version comparison is unavailable, the UI says so plainly and links to persisted adjacent diffs.
- RSS links to compare pages resolve correctly under the GitHub Pages base path.
- `node --check apps/web/app.js` passes.

## Tests

- Extend static export tests to assert Web references new payloads.
- Add JS string/route tests if the repo stays framework-free.
- Use local static export smoke for payload loading.

## Approval Gate

Do not implement until data contract child plan is approved and first payload shape is stable.

## Rollback

Keep old `#changes`, `#sources`, and RSS intact. If the viewer breaks, route `#master` can temporarily show the old evidence table while static JSON is fixed.
