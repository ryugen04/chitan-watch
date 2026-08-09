const fallbackState = {
  runs: [
    {
      run_id: "fixture-run",
      status: "SUCCESS_CHANGED",
      evaluated_at: "2026-08-09T00:05:00+00:00",
      artifact_count: 2,
      changed_artifact_count: 1,
      failed_artifact_count: 0,
      change_event_count: 2,
    },
  ],
  changes: [
    {
      id: "chg_fixture_ssk_master_csv",
      run_id: "fixture-run",
      severity: "LOW",
      detected_at: "2026-08-09T00:05:00+00:00",
      effective_from: null,
      jurisdiction: { prefecture_code: "--", municipality_code: "" },
      program: { name: "地単公費マスター確定事業一覧", public_funding_number: "", classification: "master-latest-data" },
      change_categories: ["artifact-added", "source-layer:master-latest-data", "artifact-type:master_csv"],
      vendor_impacts: ["master-import", "validation-required"],
      summary: "支払基金の地単公費マスター確定事業一覧 CSV が更新候補として検知されました。基準日、ファイル名、サイズ、CSV 行差分を確認してください。",
      interpretation: {
        headline: "支払基金の確定事業一覧 CSV 更新候補",
        summary: "地単公費マスター最新データの CSV/Excel リンクまたはファイル内容に変化がある想定です。通知は公式更新の検知であり、本番反映の指示ではありません。",
        recommended_action: "支払基金 titansys の確定事業一覧を開き、基準日、CSV ファイル名、ファイルサイズ、行差分を確認してください。医事会計システムで使う場合は同値性テストが必要です。",
        confidence: "CONFIRMED",
        likely_impact: ["CSV 取込対象の確認", "患者負担金計算への影響確認", "同値性テストの要否判断"],
      },
      evidence: [
        { type: "official_artifact", evidence_level: "CONFIRMED", field: "source_layer", before: "", after: "master-latest-data", description: "支払基金 titansys の確定事業一覧 CSV/Excel を監視するサンプルです。" },
      ],
      review_required: true,
    },
    {
      id: "chg_fixture_mhlw_faq",
      run_id: "fixture-run",
      severity: "INFO",
      detected_at: "2026-08-09T00:05:00+00:00",
      effective_from: null,
      jurisdiction: { prefecture_code: "--", municipality_code: "" },
      program: { name: "厚労省 説明会・FAQ", public_funding_number: "", classification: "policy-faq" },
      change_categories: ["document-update", "source-layer:policy-faq"],
      vendor_impacts: ["policy-review", "admin-review"],
      summary: "厚労省の地単公費マスター関連説明会・FAQ 資料の更新候補です。対象範囲や登録運用の説明変更を確認してください。",
      interpretation: {
        headline: "厚労省の説明会・FAQ 更新候補",
        summary: "制度背景や自治体向け説明の資料更新を検知する想定です。CSV 本体の差分とは分けて読みます。",
        recommended_action: "厚労省ページで説明会資料、FAQ、対象範囲、登録運用の記述を確認し、支払基金データ本体への影響有無を切り分けてください。",
        confidence: "INFO",
        likely_impact: ["運用ルールの確認", "自治体向け説明の変更確認"],
      },
      evidence: [{ type: "official_document", evidence_level: "INFO", description: "厚労省 index_00030 配下の説明会・FAQ を監視するサンプルです。", source_url: "fixture" }],
      review_required: false,
    },
  ],
  sources: [
    { artifact_id: "art_master_csv", title: "Master CSV", type: "master_csv", state: "changed", sha256: "fixture", error: null, source_group: "master-latest-data", source_layer: "master-latest-data", source_owner: "ssk", source_role: "confirmed-master-list-download", jurisdiction_scope: "national", monitor_mode: "semantic_or_file_diff", notify_policy: "always", review_policy: "required" },
    { artifact_id: "art_mhlw_faq", title: "MHLW FAQ", type: "html", state: "unchanged", sha256: "fixture", error: null, source_group: "policy-faq", source_layer: "policy-faq", source_owner: "mhlw", source_role: "policy-background-and-faq-index", jurisdiction_scope: "national", monitor_mode: "source_health", notify_policy: "important_only", review_policy: "conditional" },
    { artifact_id: "art_municipality_seed", title: "札幌市 子ども医療費助成", type: "html", state: "unchanged", sha256: "fixture", error: null, source_group: "municipality-policy-context", source_layer: "municipality-policy-context", source_owner: "municipality", source_role: "local-benefit-rule-context-signal", jurisdiction_scope: "local", monitor_mode: "semantic_context_diff", notify_policy: "important_only", review_policy: "conditional" },
  ],
  masterVersions: {
    contract_version: 1,
    latest_run_id: "fixture-run",
    comparison_scope: "adjacent_observed_versions",
    arbitrary_comparison_supported: false,
    version_count: 2,
    versions: [
      {
        version_id: "fixture-new:art_master_csv",
        content_version_id: "sha256:fixture-new",
        run_id: "fixture-new",
        artifact_id: "art_master_csv",
        is_primary_candidate: true,
        title: "地単公費マスター確定事業一覧（令和8年8月3日時点）（CSV UTF-8）",
        basis_date_label: "令和8年8月3日時点",
        basis_date_iso: "2026-08-03",
        source_url: "https://www.ssk.or.jp/fixture/master-new.csv",
        retrieved_at: "2026-08-09T00:05:00+00:00",
        sha256: "fixture-new",
        content_length: 9725000,
        parser_status: "parsed",
        row_count: 3,
        mapping_status: "csv_mapping_candidate_requires_review",
        mapping_review_required: true,
        sample_limit: 25,
        sample_rows: [
          { row_number: 1, identity: { prefecture_code: "13", municipality_code: "131016", public_funding_number: "80130001", program_subdivision_code: "1" }, display_fields: { item_1: "こども医療費助成 改定", item_10: "20260401", item_11: "99991231" } },
        ],
      },
      { version_id: "fixture-old:art_master_csv", run_id: "fixture-old", artifact_id: "art_master_csv", title: "地単公費マスター確定事業一覧（令和8年7月21日時点）（CSV UTF-8）", basis_date_label: "令和8年7月21日時点", basis_date_iso: "2026-07-21", source_url: "https://www.ssk.or.jp/fixture/master-old.csv", retrieved_at: "2026-08-09T00:00:00+00:00", sha256: "fixture-old", parser_status: "parsed", row_count: 3, mapping_status: "csv_mapping_candidate_requires_review", mapping_review_required: true, sample_rows: [] },
    ],
  },
  masterDiffs: {
    contract_version: 1,
    comparison_scope: "adjacent_observed_versions",
    arbitrary_comparison_supported: false,
    diff_count: 1,
    diffs: [
      { diff_id: "fixture-diff", run_id: "fixture-new", old_run_id: "fixture-old", old_version_id: "fixture-old:art_master_csv", new_version_id: "fixture-new:art_master_csv", old_basis_date_label: "令和8年7月21日時点", new_basis_date_label: "令和8年8月3日時点", status: "ok", has_changes: true, review_required: false, summary: { old_record_count: 3, new_record_count: 3, unchanged_row_count: 1, added_row_count: 1, removed_row_count: 1, modified_row_count: 1, ambiguous_group_count: 0 }, top_changed_fields: [{ field: "item_1", label: "事業名 正式名称", count: 1 }], detail_url: "static/master-diffs/fixture-diff.json" },
    ],
  },
  masterDiffDetails: {
    "fixture-diff": {
      diff_id: "fixture-diff",
      old_version_id: "fixture-old:art_master_csv",
      new_version_id: "fixture-new:art_master_csv",
      field_labels: { item_1: "事業名 正式名称", item_10: "有効開始年月日", item_11: "有効終了年月日" },
      pagination: { total_change_count: 1, included_change_count: 1, limit: 500, truncated: false },
      changes: [
        { row_change_id: "rowchg-fixture", type: "row_modified", identity: { prefecture_code: "13", municipality_code: "131016", public_funding_number: "80130001", program_subdivision_code: "1" }, matching_status: "MATCHED", before_row_number: 1, after_row_number: 1, changed_field_count: 1, changed_fields: [{ field: "item_1", label: "事業名 正式名称", before: "こども医療費助成", after: "こども医療費助成 改定" }], related_change_event_ids: ["chg_fixture_ssk_master_csv"], review_required: false },
      ],
    },
  },
  llmStatus: { enabled: false, provider: "gemini", status: "disabled", reason: "GEMINI_API_KEY not set" },
  llmInterpretations: { interpretations: [] },
  latest_run_id: "fixture-run",
  apiOnline: false,
};

let state = fallbackState;

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
}

async function getJson(path) {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`${path} ${response.status}`);
  return response.json();
}

async function optionalJson(path, fallback) {
  try {
    return await getJson(path);
  } catch (_error) {
    return fallback;
  }
}

async function loadDataGroup(paths, optionalPaths = {}) {
  const [runsPayload, changesPayload, sourcePayload] = await Promise.all(paths.map(getJson));
  const [masterVersions, masterDiffs, llmStatus, llmInterpretations] = await Promise.all([
    optionalJson(optionalPaths.masterVersions, fallbackState.masterVersions),
    optionalJson(optionalPaths.masterDiffs, fallbackState.masterDiffs),
    optionalJson(optionalPaths.llmStatus, fallbackState.llmStatus),
    optionalJson(optionalPaths.llmInterpretations, fallbackState.llmInterpretations),
  ]);
  return {
    runs: runsPayload.runs ?? [],
    changes: changesPayload.changes ?? [],
    sources: sourcePayload.sources ?? [],
    masterVersions,
    masterDiffs,
    masterDiffDetails: {},
    llmStatus,
    llmInterpretations,
    latest_run_id: sourcePayload.latest_run_id ?? runsPayload.runs?.[0]?.run_id ?? null,
  };
}

async function loadState() {
  try {
    state = { ...(await loadDataGroup(["/api/runs", "/api/changes", "/api/source-health"], { masterVersions: "/api/master/versions", masterDiffs: "/api/master/diffs", llmStatus: "/api/llm/status", llmInterpretations: "/api/llm/interpretations" })), apiOnline: true };
    return;
  } catch (_apiError) {
    try {
      state = { ...(await loadDataGroup(["static/runs.json", "static/changes.json", "static/source-health.json"], { masterVersions: "static/master-versions.json", masterDiffs: "static/master-diffs.json", llmStatus: "static/llm-status.json", llmInterpretations: "static/llm-interpretations.json" })), apiOnline: false, staticExport: true };
      return;
    } catch (_staticError) {
      state = fallbackState;
    }
  }
}

function severityClass(value) {
  if (value === "CRITICAL" || value === "HIGH") return "high";
  if (value === "MEDIUM") return "medium";
  if (value === "LOW") return "low";
  return "info";
}

function statusClass(value) {
  if (value === "SUCCESS_CHANGED" || value === "SUCCESS_NO_CHANGE") return "ok";
  if (value === "PARTIAL_FAILURE") return "warn";
  return "bad";
}

function formatDate(value) {
  if (!value) return "未確定";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("ja-JP", { dateStyle: "medium", timeStyle: "short" });
}

function place(change) {
  const pref = change.jurisdiction?.prefecture_code || "--";
  const muni = change.jurisdiction?.municipality_code || "";
  return muni ? `${pref}-${muni}` : pref;
}

function latestRun() {
  return state.runs[0] ?? null;
}

function interpretation(change) {
  return change.interpretation ?? {};
}

function headline(change) {
  return interpretation(change).headline || change.summary || change.program?.name || "地単公費マスターの変更";
}

function interpSummary(change) {
  return interpretation(change).summary || change.summary || "検知内容を確認してください。";
}

function recommendedAction(change) {
  return interpretation(change).recommended_action || "詳細と公式ソースを確認してください。";
}

function confidence(change) {
  return interpretation(change).confidence || interpretation(change).evidence_level || "UNRESOLVED";
}

function impactList(change) {
  return interpretation(change).likely_impact ?? [];
}

function masterVersions() {
  return state.masterVersions?.versions ?? [];
}

function masterDiffs() {
  return state.masterDiffs?.diffs ?? [];
}

function latestMasterVersion() {
  return masterVersions()[0] ?? null;
}

function masterVersionById(id) {
  return masterVersions().find(version => version.version_id === id) ?? null;
}

function masterDiffById(id) {
  return masterDiffs().find(diff => diff.diff_id === id) ?? null;
}

function llmInterpretationFor(targetType, targetId) {
  return (state.llmInterpretations?.interpretations ?? []).find(item => item.target_type === targetType && item.target_id === targetId) ?? null;
}

function formatNumber(value) {
  if (value === null || value === undefined || value === "") return "-";
  return Number(value).toLocaleString("ja-JP");
}

function shortHash(value) {
  return value ? String(value).slice(0, 12) : "-";
}

function routeParts() {
  return (location.hash.replace("#", "") || "master").split("/").map(part => decodeURIComponent(part));
}

async function loadMasterDiffDetail(diff) {
  if (!diff) return null;
  if (state.masterDiffDetails?.[diff.diff_id]) return state.masterDiffDetails[diff.diff_id];
  const paths = state.apiOnline ? [`/api/master/diffs/${encodeURIComponent(diff.diff_id)}`] : [diff.detail_url || `static/master-diffs/${encodeURIComponent(diff.diff_id)}.json`];
  for (const path of paths) {
    try {
      const payload = await getJson(path);
      const detail = payload.diff ?? payload;
      state.masterDiffDetails = { ...(state.masterDiffDetails ?? {}), [diff.diff_id]: detail };
      return detail;
    } catch (_error) {}
  }
  return null;
}

function diffCounts(summary = {}) {
  return [
    ["追加", summary.added_row_count],
    ["削除", summary.removed_row_count],
    ["変更", summary.modified_row_count],
    ["曖昧", summary.ambiguous_group_count],
    ["不変", summary.unchanged_row_count],
  ];
}

function evidenceContextChips() {
  return `<div class="context-chips"><span class="chip evidence">根拠</span><span class="chip context">関連文脈</span><span class="chip inference">解釈</span><span class="chip review">要確認</span></div>`;
}

function evidenceRefs(ids = []) {
  const refs = ids.filter(Boolean).slice(0, 6);
  if (!refs.length) return "";
  return `<span class="evidence-refs">${refs.map(id => `<code>${escapeHtml(id)}</code>`).join(" ")}</span>`;
}

function evidencedText(item) {
  if (typeof item === "string") return { text: item, evidence_ids: [] };
  return { text: item?.text ?? "", evidence_ids: item?.evidence_ids ?? [] };
}

function renderEvidencedList(title, items = []) {
  const rows = items.map(evidencedText).filter(item => item.text).map(item => `<li><span>${escapeHtml(item.text)}</span>${evidenceRefs(item.evidence_ids)}</li>`).join("");
  return rows ? `<div class="llm-subsection"><h3>${escapeHtml(title)}</h3><ul>${rows}</ul></div>` : "";
}

function renderRecommendedReview(review) {
  const item = evidencedText(review);
  if (!item.text) return "";
  return `<p class="action-line"><strong>推奨レビュー:</strong> ${escapeHtml(item.text)} ${evidenceRefs(item.evidence_ids)}</p>`;
}

function renderLlmBlock(llm) {
  if (!llm) return `<p class="guide-note">Gemini解釈は未生成です。決定論的diffだけで確認できます。</p>`;
  const output = llm.output ?? {};
  const uncertainties = (output.uncertainties ?? []).map(item => `<li>${escapeHtml(item)}</li>`).join("");
  return `<section class="interpretation-block">
    <h2>LLM-assisted interpretation</h2>
    <p>${escapeHtml(output.summary_for_humans ?? "生成済み解釈があります。")}</p>
    ${renderEvidencedList("要点", output.key_points)}
    ${renderEvidencedList("事実根拠", output.fact_basis)}
    ${renderEvidencedList("推論", output.inferences)}
    ${renderRecommendedReview(output.recommended_review)}
    ${renderEvidencedList("併せて見る文脈", output.related_context_to_check)}
    ${uncertainties ? `<div class="llm-subsection"><h3>不確実性</h3><ul>${uncertainties}</ul></div>` : ""}
    <p class="meta">provider: ${escapeHtml(llm.provider)} / status: ${escapeHtml(llm.status)} / risk: ${escapeHtml(output.risk_label ?? "-")}</p>
  </section>`;
}

function guideLink(label = "通知の見方") {
  return `<a class="guide-link" href="#guide">${escapeHtml(label)}</a>`;
}

function kpis() {
  const run = latestRun();
  const reviewCount = state.changes.filter(change => change.review_required).length;
  return `<div class="kpis">
    <div class="kpi"><span class="meta">Open changes</span><strong>${state.changes.length}</strong></div>
    <div class="kpi"><span class="meta">Review queue</span><strong>${reviewCount}</strong></div>
    <div class="kpi"><span class="meta">Latest run</span><strong>${escapeHtml(run?.status ?? "NO_RUN")}</strong></div>
    <div class="kpi"><span class="meta">Changed artifacts</span><strong>${escapeHtml(run?.changed_artifact_count ?? 0)}</strong></div>
  </div>`;
}

function renderChanges() {
  const rows = state.changes.map(change => `<article class="card change-card">
    <div class="card-top"><span class="severity ${severityClass(change.severity)}">${escapeHtml(change.severity)}</span>${change.review_required ? '<span class="review-badge">Review</span>' : ""}</div>
    <h2><a href="#change-detail/${encodeURIComponent(change.id)}">${escapeHtml(headline(change))}</a></h2>
    <p>${escapeHtml(interpSummary(change))}</p>
    <p class="action-line"><strong>対応:</strong> ${escapeHtml(recommendedAction(change))}</p>
    <p class="meta">確度: ${escapeHtml(confidence(change))} / 施行: ${escapeHtml(change.effective_from ?? "未確定")} / 検知: ${escapeHtml(formatDate(change.detected_at))}</p>
    <div class="tags">${(change.change_categories ?? []).map(item => `<span>${escapeHtml(item)}</span>`).join("")}</div>
  </article>`).join("");
  return `${kpis()}<p class="page-note">公費制度、データ構造、通知の読み方は ${guideLink("公費制度ガイド")} にまとめています。</p><div class="grid">${rows || '<section class="empty">変更はまだありません。</section>'}</div>`;
}

function selectedChange() {
  const parts = location.hash.split("/");
  const id = parts[1] ? decodeURIComponent(parts[1]) : state.changes[0]?.id;
  return state.changes.find(change => change.id === id) ?? state.changes[0] ?? null;
}

function relatedDiffForChange(change) {
  return masterDiffs().find(diff => diff.run_id === change?.run_id || diff.new_run_id === change?.run_id) ?? null;
}

function renderDetail() {
  const change = selectedChange();
  if (!change) return '<section class="empty">変更詳細はまだありません。</section>';
  const evidenceRows = (change.evidence ?? []).map(item => `<tr><td>${escapeHtml(item.evidence_level)}</td><td>${escapeHtml(item.field ?? item.type)}</td><td>${escapeHtml(item.before ?? "")}</td><td>${escapeHtml(item.after ?? "")}</td><td>${escapeHtml(item.description ?? "")}</td></tr>`).join("");
  const impacts = impactList(change).map(item => `<li>${escapeHtml(item)}</li>`).join("");
  const relatedDiff = relatedDiffForChange(change);
  const diffLink = relatedDiff ? `<p class="action-line"><strong>CSV diff:</strong> <a href="#master-compare/${encodeURIComponent(relatedDiff.diff_id)}">${escapeHtml(relatedDiff.old_basis_date_label ?? relatedDiff.old_version_id ?? "old")} → ${escapeHtml(relatedDiff.new_basis_date_label ?? relatedDiff.new_version_id ?? "new")}</a></p>` : "";
  return `<section class="detail-panel">
    <div class="card-top"><span class="severity ${severityClass(change.severity)}">${escapeHtml(change.severity)}</span>${change.review_required ? '<span class="review-badge">Review</span>' : ""}</div>
    <h2>${escapeHtml(headline(change))}</h2>
    <p class="lead">${escapeHtml(interpSummary(change))}</p>
    <div class="interpretation-block">
      <h2>解釈</h2>
      <ul>${impacts || '<li>想定影響はまだ整理されていません。</li>'}</ul>
      <p class="action-line"><strong>推奨対応:</strong> ${escapeHtml(recommendedAction(change))}</p>
      <p class="guide-note">公費制度の背景、確度、再通知の読み方は ${guideLink("公費制度ガイド")} で確認できます。</p>
    </div>
    ${diffLink}
    <dl class="facts"><div><dt>Run</dt><dd>${escapeHtml(change.run_id)}</dd></div><div><dt>確度</dt><dd>${escapeHtml(confidence(change))}</dd></div><div><dt>公費負担者番号</dt><dd>${escapeHtml(change.program?.public_funding_number ?? "")}</dd></div><div><dt>施行</dt><dd>${escapeHtml(change.effective_from ?? "未確定")}</dd></div></dl>
    <h2>根拠</h2>
    <table class="table"><tr><th>Level</th><th>Field</th><th>Before</th><th>After</th><th>Description</th></tr>${evidenceRows}</table>
  </section>`;
}

function renderUpcoming() {
  const upcoming = state.changes.filter(change => change.effective_from).sort((a, b) => String(a.effective_from).localeCompare(String(b.effective_from)));
  return `<section class="table-panel"><table class="table"><tr><th>施行日</th><th>自治体</th><th>制度</th><th>Severity</th><th>Review</th></tr>${upcoming.map(change => `<tr><td>${escapeHtml(change.effective_from)}</td><td>${escapeHtml(place(change))}</td><td>${escapeHtml(change.program?.name ?? "")}</td><td>${escapeHtml(change.severity)}</td><td>${change.review_required ? "必要" : "-"}</td></tr>`).join("")}</table></section>`;
}

function renderMaster() {
  const latest = latestMasterVersion();
  const versions = masterVersions();
  const diffs = masterDiffs();
  const latestDiff = diffs[0] ?? null;
  const versionRows = versions.map(version => `<tr><td><a href="#master-version/${encodeURIComponent(version.version_id)}">${escapeHtml(version.basis_date_label ?? version.version_id)}</a></td><td>${escapeHtml(version.run_id)}</td><td>${escapeHtml(formatDate(version.retrieved_at))}</td><td>${escapeHtml(formatNumber(version.row_count))}</td><td>${escapeHtml(version.parser_status)}</td><td>${version.mapping_review_required ? '<span class="review-badge">mapping review</span>' : '<span class="source-state">ok</span>'}</td><td>${escapeHtml(shortHash(version.sha256))}</td><td><a href="${escapeHtml(version.source_url)}" target="_blank" rel="noopener">公式CSV</a></td></tr>`).join("");
  const diffRows = diffs.map(diff => `<tr><td><a href="#master-compare/${encodeURIComponent(diff.diff_id)}">${escapeHtml(diff.new_basis_date_label ?? diff.diff_id)}</a></td><td>${escapeHtml(diff.old_basis_date_label ?? "-")}</td><td>${escapeHtml(diff.status)}</td><td>${diffCounts(diff.summary).map(([label, count]) => `${label} ${formatNumber(count)}`).join(" / ")}</td><td>${diff.review_required ? '<span class="review-badge">Review</span>' : '<span class="source-state">deterministic</span>'}</td></tr>`).join("");
  const samples = (latest?.sample_rows ?? []).map(row => `<tr><td>${escapeHtml(row.row_number)}</td><td>${escapeHtml(row.identity?.prefecture_code ?? "")}-${escapeHtml(row.identity?.municipality_code ?? "")}</td><td>${escapeHtml(row.identity?.public_funding_number ?? "")}</td><td>${escapeHtml(row.display_fields?.item_1 ?? "")}</td><td>${escapeHtml(row.display_fields?.item_10 ?? "")}</td><td>${escapeHtml(row.display_fields?.item_11 ?? "")}</td></tr>`).join("");
  return `<section class="master-dashboard">
    <section class="master-hero">
      <div>
        <p class="eyebrow">Master CSV</p>
        <h2>${escapeHtml(latest?.title ?? "CSV版はまだありません")}</h2>
        <p class="lead">${latest ? `${escapeHtml(latest.basis_date_label ?? "基準日未抽出")} / ${formatNumber(latest.row_count)} rows / SHA ${escapeHtml(shortHash(latest.sha256))}` : "確定事業一覧CSVの取得後に表示します。"}</p>
      </div>
      <div class="master-actions">${latestDiff ? `<a class="button" href="#master-compare/${encodeURIComponent(latestDiff.diff_id)}">最新diffを見る</a>` : ""}<a class="button secondary" href="#guide">見方</a></div>
    </section>
    <section class="kpis">
      <div class="kpi"><span class="meta">CSV versions</span><strong>${formatNumber(versions.length)}</strong></div>
      <div class="kpi"><span class="meta">Diff pairs</span><strong>${formatNumber(diffs.length)}</strong></div>
      <div class="kpi"><span class="meta">Comparison</span><strong>${escapeHtml(state.masterDiffs?.comparison_scope ?? "-")}</strong></div>
      <div class="kpi"><span class="meta">LLM</span><strong>${escapeHtml(state.llmStatus?.status ?? "unknown")}</strong></div>
    </section>
    <p class="page-note">CSVを入口に、版・差分・根拠・関連文脈を分けて確認します。任意2版比較は未対応で、現在は隣接する観測版のdiffを表示します。</p>
    ${evidenceContextChips()}
    <section class="table-panel"><h2>Version history</h2><table class="table dense"><tr><th>基準日</th><th>Run</th><th>取得</th><th>Rows</th><th>Parse</th><th>Review</th><th>SHA</th><th>Source</th></tr>${versionRows || '<tr><td colspan="8">CSV版はまだありません。</td></tr>'}</table></section>
    <section class="table-panel"><h2>Diff index</h2><table class="table dense"><tr><th>New</th><th>Old</th><th>Status</th><th>Counts</th><th>Review</th></tr>${diffRows || '<tr><td colspan="5">比較可能なdiffはまだありません。</td></tr>'}</table></section>
    <section class="table-panel"><h2>Current version sample</h2><table class="table dense"><tr><th>Row</th><th>自治体</th><th>公費負担者番号</th><th>制度</th><th>開始</th><th>終了</th></tr>${samples || '<tr><td colspan="6">サンプル行はありません。</td></tr>'}</table></section>
  </section>`;
}

function renderMasterVersion() {
  const id = routeParts()[1];
  const version = masterVersionById(id) ?? latestMasterVersion();
  if (!version) return '<section class="empty">CSV版はまだありません。</section>';
  const sampleRows = (version.sample_rows ?? []).map(row => `<tr><td>${escapeHtml(row.row_number)}</td><td>${escapeHtml(row.identity?.prefecture_code ?? "")}-${escapeHtml(row.identity?.municipality_code ?? "")}</td><td>${escapeHtml(row.identity?.public_funding_number ?? "")}</td><td>${escapeHtml(row.display_fields?.item_1 ?? "")}</td><td>${escapeHtml(row.display_fields?.item_10 ?? "")}</td><td>${escapeHtml(row.display_fields?.item_11 ?? "")}</td></tr>`).join("");
  return `<section class="detail-panel"><p class="eyebrow">CSV version</p><h2>${escapeHtml(version.title)}</h2><dl class="facts"><div><dt>Version</dt><dd>${escapeHtml(version.version_id)}</dd></div><div><dt>Basis</dt><dd>${escapeHtml(version.basis_date_label ?? "-")}</dd></div><div><dt>Rows</dt><dd>${formatNumber(version.row_count)}</dd></div><div><dt>Parser</dt><dd>${escapeHtml(version.parser_status)}</dd></div><div><dt>Mapping</dt><dd>${escapeHtml(version.mapping_status ?? "-")}</dd></div><div><dt>SHA</dt><dd>${escapeHtml(shortHash(version.sha256))}</dd></div></dl><p class="page-note">${escapeHtml(version.mapping_blocker ?? "")}</p><p><a class="button secondary" href="${escapeHtml(version.source_url)}" target="_blank" rel="noopener">公式CSVを開く</a></p><h2>Sample rows</h2><table class="table dense"><tr><th>Row</th><th>自治体</th><th>公費負担者番号</th><th>制度</th><th>開始</th><th>終了</th></tr>${sampleRows || '<tr><td colspan="6">サンプル行はありません。</td></tr>'}</table></section>`;
}

function renderCompare(detail) {
  if (!detail) return '<section class="empty">CSV diff detailを読み込めませんでした。</section>';
  const llm = llmInterpretationFor("master_diff", detail.diff_id);
  const rows = (detail.changes ?? []).map(row => `<tr><td><a href="#master-row/${encodeURIComponent(detail.diff_id)}/${encodeURIComponent(row.row_change_id)}">${escapeHtml(row.type)}</a></td><td>${escapeHtml(row.identity?.prefecture_code ?? "")}-${escapeHtml(row.identity?.municipality_code ?? "")}</td><td>${escapeHtml(row.identity?.public_funding_number ?? "")}</td><td>${escapeHtml(row.changed_fields?.map(field => field.label || field.field).slice(0, 4).join(" / ") ?? "")}</td><td>${row.review_required ? '<span class="review-badge">Review</span>' : '<span class="source-state">deterministic</span>'}</td><td>${escapeHtml((row.related_change_event_ids ?? []).join(", "))}</td></tr>`).join("");
  const topFields = (detail.top_changed_fields ?? []).map(item => `<span>${escapeHtml(item.label ?? item.field)} ${formatNumber(item.count)}</span>`).join("");
  const llmBlock = renderLlmBlock(llm);
  return `<section class="detail-panel"><p class="eyebrow">CSV compare</p><h2>${escapeHtml(detail.old_basis_date_label ?? detail.old_version_id ?? "old")} → ${escapeHtml(detail.new_basis_date_label ?? detail.new_version_id ?? "new")}</h2><div class="kpis">${diffCounts(detail.summary).map(([label, count]) => `<div class="kpi"><span class="meta">${escapeHtml(label)}</span><strong>${formatNumber(count)}</strong></div>`).join("")}</div><p class="page-note">比較スコープ: ${escapeHtml(detail.comparison_scope)} / 任意2版比較: ${detail.arbitrary_comparison_supported ? "対応" : "未対応"}</p>${evidenceContextChips()}<div class="tags">${topFields}</div>${llmBlock}<table class="table dense"><tr><th>Type</th><th>自治体</th><th>公費負担者番号</th><th>Changed fields</th><th>Review</th><th>ChangeEvent</th></tr>${rows || '<tr><td colspan="6">行差分はありません。</td></tr>'}</table></section>`;
}

function renderMasterRow(detail) {
  const rowId = routeParts()[2];
  const row = (detail?.changes ?? []).find(item => item.row_change_id === rowId);
  if (!detail || !row) return '<section class="empty">行差分が見つかりません。</section>';
  const fields = (row.changed_fields ?? []).map(field => `<tr><td>${escapeHtml(field.label ?? field.field)}</td><td>${escapeHtml(field.field)}</td><td>${escapeHtml(field.before ?? "")}</td><td>${escapeHtml(field.after ?? "")}</td></tr>`).join("");
  const links = (row.related_change_event_ids ?? []).map(id => `<a href="#change-detail/${encodeURIComponent(id)}">${escapeHtml(id)}</a>`).join(" / ");
  return `<section class="detail-panel"><p class="eyebrow">CSV row diff</p><h2>${escapeHtml(row.identity?.public_funding_number ?? row.row_change_id)}</h2><dl class="facts"><div><dt>自治体</dt><dd>${escapeHtml(row.identity?.prefecture_code ?? "")}-${escapeHtml(row.identity?.municipality_code ?? "")}</dd></div><div><dt>区分</dt><dd>${escapeHtml(row.identity?.program_subdivision_code ?? "")}</dd></div><div><dt>Before row</dt><dd>${escapeHtml(row.before_row_number ?? "-")}</dd></div><div><dt>After row</dt><dd>${escapeHtml(row.after_row_number ?? "-")}</dd></div><div><dt>Evidence</dt><dd>deterministic CSV diff</dd></div><div><dt>ChangeEvent</dt><dd>${links || "-"}</dd></div></dl>${evidenceContextChips()}<table class="table dense"><tr><th>Field</th><th>Key</th><th>Before</th><th>After</th></tr>${fields}</table></section>`;
}

function renderGuide() {
  return `<section class="guide">
    <section class="guide-section guide-wide">
      <p class="eyebrow">公費制度ガイド</p>
      <p class="lead">Chitan Watch は、支払基金・厚労省側で公開される地単公費マスターと関連説明資料を追い、更新確認の入口を RSS と静的ページで届けるための監視サイトです。</p>
      <p>今回の対象は「自治体の医療費助成制度を全部集めたカタログ」ではありません。現物給付の患者負担金計算に使う地単公費マスターを、どこで見て、何を対象とし、どう更新を追うかに絞っています。Source Registry は、その公式ページと資料を役割ごとに管理するための地図です。</p>
    </section>
    <section class="guide-section guide-wide">
      <h2>まず見るページ</h2>
      <ol class="flow-list">
        <li><strong>支払基金</strong><span>地単公費マスター情報の登録に関するお知らせ。実ファイルの取得元であり、確定事業一覧の Excel / CSV が置かれるデータ本体の本命ページです。</span></li>
        <li><strong>厚労省</strong><span>国公費・地単公費マスターの変更・更新、現物給付化の取組。制度背景、説明会資料、FAQ、自治体向け説明を見るページで、実データ取得元とは分けます。</span></li>
        <li><strong>診療報酬情報提供サービス</strong><span>公費負担医療制度マスターの入口。国公費マスター・地単公費マスターの位置づけと、支払基金ページへの導線を確認します。</span></li>
      </ol>
    </section>
    <div class="guide-grid">
      <article class="guide-section">
        <h2>地単公費マスターの対象</h2>
        <p>地方公共団体の医療費等助成事業のうち、併用レセプトまたは連記式医療費明細書による現物給付の制度が中心です。受給者証の券面記載事項の要件を使い、患者負担金を計算できるように作成されています。</p>
      </article>
      <article class="guide-section">
        <h2>対象外</h2>
        <p>償還払い制度はこのマスターには含まれません。地単公費マスターに載っていないことは、自治体制度が存在しないことを意味しません。現物給付・併用レセプト・連記式医療費明細書の枠に入るかを分けて見ます。</p>
      </article>
      <article class="guide-section">
        <h2>最新データの見方</h2>
        <p>リンク文言やファイル名に含まれる「令和X年X月X日時点」を最初に見ます。人が確認するなら Excel、差分検知や自動処理には CSV を使います。CSV ファイル名の日付、ファイルサイズ、ハッシュ、行差分を確認します。</p>
      </article>
      <article class="guide-section">
        <h2>確定事業一覧</h2>
        <p>見るべき本体は「地単公費マスター確定事業一覧」です。暫定的な入力フォームや説明資料と混ぜません。ただし医事会計システムやレセコンで利用する場合は、同値性テストなど必要な検証を実施した上で使います。</p>
      </article>
      <article class="guide-section">
        <h2>更新のリードタイム</h2>
        <p>自治体の新規制度登録、登録内容変更、廃止は Web フォームで行われます。新規開始や既存制度変更は、原則として変更6か月前の月末までに更新対応する前提です。通知日、ファイル基準日、制度施行日は別の概念なので、公開が施行前に見える場合も、既存資料の更新として見える場合もあります。</p>
      </article>
      <article class="guide-section">
        <h2>説明会・FAQ</h2>
        <p>厚労省ページでは、全国説明会、自治体向け説明会、実態調査、よくあるご質問を見ます。データ本体の差分ではなく、対象範囲、登録運用、自治体への依頼内容が変わっていないかを確認する層です。</p>
      </article>
      <article class="guide-section">
        <h2>現在の監視範囲</h2>
        <p>現在の主な監視対象は、支払基金の titansys ページ、確定事業一覧 CSV/Excel、登録・運用資料、厚労省の変更・更新ページ、診療報酬情報提供サービスの制度マスター入口です。自治体制度ページは、支払基金マスターとは別の「自治体制度文脈」として現在の監視範囲に含めます。支払基金トップ更新情報は Source Health の取得状態確認として扱います。</p>
      </article>
      <article class="guide-section">
        <h2>自治体制度文脈</h2>
        <p>自治体個別ページは、受給者証、自己負担、現物給付、償還払い、申請、更新日などの実制度文脈を見る現在スコープの情報源です。支払基金マスター更新そのものとは分け、「自治体制度文脈更新」として RSS に出します。PMH は今回の監視範囲には入れません。</p>
      </article>
      <article class="guide-section">
        <h2>情報層の分け方</h2>
        <dl class="term-list">
          <div><dt>master-latest-data</dt><dd>確定事業一覧の Excel / CSV と基準日を追う本命レイヤーです。</dd></div>
          <div><dt>master-registration-operation</dt><dd>項目一覧、入力要領、入力例、FAQ、登録・変更・廃止の運用資料です。</dd></div>
          <div><dt>policy-faq</dt><dd>厚労省の説明会、制度背景、FAQ、自治体向け説明です。</dd></div>
          <div><dt>reference-portal</dt><dd>診療報酬情報提供サービス側の公費負担医療制度マスター入口です。</dd></div>
          <div><dt>site-news-health</dt><dd>支払基金トップ更新情報の補助確認です。本命は titansys ページです。</dd></div>
          <div><dt>municipality-policy-context</dt><dd>自治体の医療費助成制度ページを、マスターとは別の制度文脈更新として見るレイヤーです。</dd></div>
        </dl>
      </article>
      <article class="guide-section">
        <h2>通知で見る順番</h2>
        <p>RSS は公式ページやファイルの変化を知らせる入口です。制度変更の確定判断、本番マスター反映、ベンダー作業指示を自動で意味するものではありません。Severity は確認優先度、Review は人の確認要否、確度は根拠の強さ、Source Health 用の項目は取得状態の補助確認として読みます。自治体制度文脈は「自治体制度文脈更新」として、支払基金マスター更新とは別の見出しで読みます。</p>
        <ol>
          <li>ソース層が master-latest-data、policy-faq、municipality-policy-context のどれかを確認します。</li>
          <li>基準日、CSV/Excel ファイル名、ファイルサイズ、検知日時を見ます。</li>
          <li>CSV 行差分があれば、公費負担者番号、自治体、制度名、適用期間を見ます。</li>
          <li>説明会・FAQ 更新なら、運用ルールや対象範囲の変更かを確認します。</li>
        </ol>
      </article>
      <article class="guide-section">
        <h2>解釈の境界</h2>
        <p>現在の公開版では、外部 LLM に判断を任せていません。見出し、想定影響、推奨対応、確度はルールベースです。公開 CSV をそのまま本番反映するのではなく、差分確認、計算影響確認、同値性テストを前提に扱います。</p>
      </article>
      <article class="guide-section">
        <h2>よくある読み違い</h2>
        <p>地単公費マスターは、自治体医療費助成制度を全部網羅する制度カタログではありません。償還払い制度や、現物給付・併用レセプト・連記式医療費明細書の枠に入らない制度は対象外になり得ます。自治体制度文脈の通知は、この違いを実例で確認するための補助線です。</p>
      </article>
    </div>
    <section class="guide-section guide-wide">
      <h2>情報源</h2>
      <ul class="source-list">
        <li><a href="https://www.ssk.or.jp/seikyushiharai/titansys/index.html" target="_blank" rel="noopener">社会保険診療報酬支払基金 地単公費マスター情報の登録に関するお知らせ</a></li>
        <li><a href="https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/iryouhoken/index_00030.html" target="_blank" rel="noopener">厚生労働省 国公費・地単公費マスターの変更・更新、現物給付化の取組</a></li>
        <li><a href="https://shinryohoshu.mhlw.go.jp/shinryohoshu/html/seido_master.jsp" target="_blank" rel="noopener">診療報酬情報提供サービス 公費負担医療制度マスター</a></li>
        <li><a href="https://www.ssk.or.jp/" target="_blank" rel="noopener">社会保険診療報酬支払基金 トップ更新情報</a></li>
      </ul>
    </section>
  </section>`;
}

function renderSources() {
  const run = latestRun();
  const groups = state.sources.reduce((acc, source) => {
    const key = source.source_layer || source.source_group || "uncategorized";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
  const groupText = Object.entries(groups).map(([name, count]) => `${escapeHtml(name)} ${count}`).join(" / ");
  const rows = state.sources.map(source => `<tr><td>${escapeHtml(source.title)}</td><td><span class="source-state">${escapeHtml(source.state)}</span></td><td>${escapeHtml(source.type)}</td><td>${escapeHtml(source.source_layer ?? "")}</td><td>${escapeHtml(source.source_owner ?? "")}</td><td>${escapeHtml(source.source_role ?? "")}</td><td>${escapeHtml(source.jurisdiction_scope ?? "")}</td><td>${escapeHtml(source.monitor_mode ?? "")}</td><td>${escapeHtml(source.notify_policy ?? "")}</td><td>${escapeHtml(source.review_policy ?? "")}</td><td>${escapeHtml(source.sha256 ? source.sha256.slice(0, 12) : "")}</td><td>${escapeHtml(source.error ?? "")}</td></tr>`).join("");
  return `<section class="table-panel"><div class="run-strip"><span class="status-dot ${statusClass(run?.status)}"></span><strong>${escapeHtml(run?.status ?? "NO_RUN")}</strong><span class="meta">Latest: ${escapeHtml(state.latest_run_id ?? "-")}</span></div><p class="page-note">監視対象レイヤー: ${groupText || "未設定"}</p><table class="table"><tr><th>Source</th><th>State</th><th>Type</th><th>Layer</th><th>Owner</th><th>Role</th><th>Scope</th><th>Monitor</th><th>Notify</th><th>Review</th><th>SHA-256</th><th>Error</th></tr>${rows}</table></section>`;
}

function titleFor(route) {
  return ({ "changes": "Changes", "change-detail": "Change Detail", "guide": "公費制度ガイド", "upcoming": "Upcoming", "master": "Master CSV", "master-version": "CSV Version", "master-compare": "CSV Compare", "master-row": "CSV Row", "sources": "Source Health" })[route] ?? "Master CSV";
}

async function contentForRoute(route) {
  if (route === "master-compare") {
    const diff = masterDiffById(routeParts()[1]) ?? masterDiffs()[0];
    return renderCompare(await loadMasterDiffDetail(diff));
  }
  if (route === "master-row") {
    const diff = masterDiffById(routeParts()[1]) ?? masterDiffs()[0];
    return renderMasterRow(await loadMasterDiffDetail(diff));
  }
  return ({
    changes: renderChanges,
    "change-detail": renderDetail,
    guide: renderGuide,
    upcoming: renderUpcoming,
    master: renderMaster,
    "master-version": renderMasterVersion,
    sources: renderSources,
  })[route]?.() ?? renderMaster();
}

async function render() {
  const route = routeParts()[0] || "master";
  const app = document.querySelector("#app");
  document.querySelector("h1").textContent = titleFor(route);
  document.querySelector(".status-pill").textContent = state.apiOnline ? "API connected" : state.staticExport ? "Static export" : "Fixture fallback";
  app.innerHTML = await contentForRoute(route);
}

addEventListener("hashchange", () => { render(); });
await loadState();
await render();
