# Gemini LLM Integration Plan

Parent plan: `.codex/plans/2026081008-csv-diff-viewer-gemini-roadmap.md`
Status: draft for review, not approved for implementation.
Target root: `/home/glaucus03/dev/projects/chitan-watch`

## Original Request

Gemini API keyを使って、CSV差分や関連情報の解釈を真面目に組み込む。キーはユーザーが設定できる場所を提示する。

## Goal

Add a real Gemini-backed enrichment path that explains deterministic CSV diffs and linked context, without making LLM output authoritative and without exposing secrets.

## Official References

- Gemini API key documentation: `https://ai.google.dev/gemini-api/docs/api-key`
- Gemini structured output documentation: `https://ai.google.dev/gemini-api/docs/structured-output`

Implementation should verify the current REST endpoint and model names from official docs at implementation time.

## Secret Setting

GitHub Actions repository secret:

```text
Settings -> Secrets and variables -> Actions -> New repository secret -> GEMINI_API_KEY
```

Local manual runs should keep the key out of shell history. Put it in an ignored local env file such as `.env.local`, then source that file without printing the value.

Optional compatibility:

```text
GOOGLE_API_KEY
```

`GEMINI_API_KEY` wins if both are set.

## Security Rules

- Never put the key in browser JavaScript.
- Never put the key in static JSON, RSS, logs, fixtures, snapshots, prompts, or error details.
- Do not commit `.env`.
- Redact request headers in errors.
- Store only generated output and non-secret metadata.
- If secret exposure occurs, stop and rotate the key.

## Provider Boundary

Candidate module updates:

```text
crawler/chitan_watch/llm.py
```

Candidate classes/functions:

```python
class DisabledLLMProvider: ...
class GeminiLLMProvider: ...
def load_llm_provider_from_env(env: Mapping[str, str] = os.environ) -> LLMProvider: ...
def build_csv_diff_interpretation_input(diff: dict, max_rows: int) -> dict: ...
def validate_llm_interpretation(raw: dict) -> dict: ...
```

Provider outcomes:

| Status | Meaning | Export behavior |
|---|---|---|
| `disabled` | No key or `--enable-llm` false | deterministic export continues |
| `success` | Gemini returned valid structured JSON | write interpretation payload |
| `invalid_output` | Response did not match schema | deterministic export continues, review flag |
| `failed` | Network/API/runtime failure | deterministic export continues, error category only |


## Production Controls

The first Gemini implementation must be operationally bounded, not just mocked.

| Control | Initial value |
|---|---|
| Timeout | 20 seconds per request |
| Retries | 1 retry for transient network/server errors |
| Batch size | One diff summary plus capped row samples per request |
| Row cap | 30 row changes per Gemini request unless manually raised |
| Daily/run cap | Max 5 Gemini requests per export by default |
| Token budget | Prompt builder truncates long field values and records truncation |
| Cache | Reuse interpretation when target id and deterministic input hash match |
| Failure behavior | Deterministic export succeeds with `llm_status=failed` |
| Cost visibility | Export summary includes request count, not token secrets or key data |

## Prompt Injection And Output Safety

Official pages and CSV values are still untrusted text for prompt purposes.

Rules:

- Wrap source/context text as data, never as instructions.
- Tell Gemini to ignore instructions embedded in source text.
- Validate output against schema before publishing.
- Escape all published text in Web rendering.
- Do not allow Gemini to introduce new URLs or facts outside provided evidence.
- Keep raw Gemini response out of public output unless validated and sanitized.

## Invocation Policy

Recommended first policy:

- Gemini is invoked only when `--enable-llm` is passed and a key exists.
- Scheduled GitHub Actions can pass `--enable-llm` later after key setup.
- First implementation caps rows per request.
- Only changed diffs/events are sent, not unchanged full CSV contents.

Open policy choice for user:

| Option | Behavior | Risk |
|---|---|---|
| Manual only | Use only workflow dispatch input | Lowest cost and surprise |
| Diff only | Scheduled crawl uses Gemini only when deterministic diff exists | Good default |
| Always when key exists | Every run asks Gemini for summaries | Higher cost and noise |

Recommended initial: Diff only, with manual override.

## Prompt Contract

Prompt file candidate:

```text
prompts/analyze-csv-diff-with-context.md
```

Prompt must require:

- Japanese output for users.
- Separation of facts, inferences, and uncertainties.
- Citations only to provided evidence ids or official URLs.
- Every fact, key point, inference, recommendation, and related context item carries `evidence_ids`; uncited material belongs in `uncertainties`.
- No invented制度 changes.
- No medical/legal advice.
- Clear review recommendation.
- Compact output suitable for Web cards and RSS snippets.

Structured output candidate:

```json
{
  "summary_for_humans": "string",
  "key_points": [{"text": "string", "evidence_ids": ["diff_id|row_change_id|source_url"]}],
  "fact_basis": [{"text": "string", "evidence_ids": ["diff_id|row_change_id|source_url"]}],
  "inferences": [{"text": "string", "evidence_ids": ["diff_id|row_change_id|source_url"]}],
  "uncertainties": ["string"],
  "recommended_review": {"text": "string", "evidence_ids": ["diff_id|row_change_id|source_url"]},
  "related_context_to_check": [{"text": "string", "evidence_ids": ["diff_id|row_change_id|source_url"]}],
  "risk_label": "low|medium|high|needs_review"
}
```

## Static Outputs

```text
/static/llm-status.json
/static/llm-interpretations.json
```

Status example:

```json
{
  "enabled": false,
  "provider": "gemini",
  "status": "disabled",
  "reason": "GEMINI_API_KEY not set",
  "generated_at": "..."
}
```

Interpretation entry example:

```json
{
  "target_type": "master_diff",
  "target_id": "diff_...",
  "provider": "gemini",
  "model": "...",
  "status": "success",
  "generated_at": "...",
  "output": { }
}
```

## Workflow Wiring

Potential `publish-static.yml` changes after approval:

- Add workflow dispatch input `enable_llm`.
- Add env in export step:

```yaml
GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

- Pass `--enable-llm` only when policy allows.

Do not print whether a key value exists. It is acceptable to print `llm_status=disabled|success|failed`.

## Acceptance Criteria

- Without key, static export succeeds and writes disabled status.
- With mocked provider, structured interpretation is written and linked to diff id.
- Invalid Gemini output is rejected.
- Network failure does not fail deterministic export.
- Public static assets contain no key.
- Timeout, retry, request cap, row cap, input hash cache, and failure fallback are implemented or explicitly deferred with a blocking note.
- Prompt-injection treatment and output sanitization are tested or reviewed.
- Docs tell user exactly where to set `GEMINI_API_KEY`.

## Tests

- `tests/test_llm.py` for disabled provider, env selection, mocked Gemini client, invalid output, and redaction.
- Static export test for `llm-status.json`.
- Optional workflow text test for secret env name without value.

## Approval Gate

Do not implement until the user chooses Gemini invocation policy and accepts `GEMINI_API_KEY` as the setting name.

## Rollback

Remove `--enable-llm` from workflows or remove the repository secret. Deterministic static export remains usable. If implementation code itself is faulty, revert the Gemini integration commit while keeping CSV diff viewer work.
