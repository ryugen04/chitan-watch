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
      id: "chg_fixture_tokyo_age",
      run_id: "fixture-run",
      severity: "HIGH",
      detected_at: "2026-08-09T00:05:00+00:00",
      effective_from: "2026-04-01",
      jurisdiction: { prefecture_code: "13", municipality_code: "131016" },
      program: { name: "こども医療費助成", public_funding_number: "80130001", classification: "1" },
      change_categories: ["master-row-modified", "validity-period"],
      vendor_impacts: ["master-import", "eligibility-determination", "patient-registration"],
      summary: "こども医療費助成 の地単公費マスター差分: row_modified",
      evidence: [
        { type: "master_field_diff", evidence_level: "CONFIRMED", field: "item_1", before: "こども医療費助成", after: "こども医療費助成 改定", source_url: "fixture" },
      ],
      review_required: false,
    },
    {
      id: "chg_fixture_review",
      run_id: "fixture-run",
      severity: "HIGH",
      detected_at: "2026-08-09T00:05:00+00:00",
      effective_from: null,
      jurisdiction: { prefecture_code: "13", municipality_code: "131050" },
      program: { name: "重複制度", public_funding_number: "80130005", classification: "1" },
      change_categories: ["admin-review", "ambiguous-master-row-match"],
      vendor_impacts: ["master-import", "admin-review"],
      summary: "重複制度 の地単公費マスター差分: row_ambiguous",
      evidence: [{ type: "ambiguous_master_match", evidence_level: "UNRESOLVED", description: "Business identity requires Admin Review", source_url: "fixture" }],
      review_required: true,
    },
  ],
  sources: [
    { artifact_id: "art_master_csv", title: "Master CSV", type: "master_csv", state: "changed", sha256: "fixture", error: null },
    { artifact_id: "art_schema", title: "Schema PDF", type: "schema", state: "unchanged", sha256: "fixture", error: null },
  ],
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

async function loadDataGroup(paths) {
  const [runsPayload, changesPayload, sourcePayload] = await Promise.all(paths.map(getJson));
  return {
    runs: runsPayload.runs ?? [],
    changes: changesPayload.changes ?? [],
    sources: sourcePayload.sources ?? [],
    latest_run_id: sourcePayload.latest_run_id ?? runsPayload.runs?.[0]?.run_id ?? null,
  };
}

async function loadState() {
  try {
    state = { ...(await loadDataGroup(["/api/runs", "/api/changes", "/api/source-health"])), apiOnline: true };
    return;
  } catch (_apiError) {
    try {
      state = { ...(await loadDataGroup(["static/runs.json", "static/changes.json", "static/source-health.json"])), apiOnline: false, staticExport: true };
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
  return `${kpis()}<p class="page-note">通知の読み方や確認順は ${guideLink("Guide")} にまとめています。</p><div class="grid">${rows || '<section class="empty">変更はまだありません。</section>'}</div>`;
}

function selectedChange() {
  const parts = location.hash.split("/");
  const id = parts[1] ? decodeURIComponent(parts[1]) : state.changes[0]?.id;
  return state.changes.find(change => change.id === id) ?? state.changes[0] ?? null;
}

function renderDetail() {
  const change = selectedChange();
  if (!change) return '<section class="empty">変更詳細はまだありません。</section>';
  const evidenceRows = (change.evidence ?? []).map(item => `<tr><td>${escapeHtml(item.evidence_level)}</td><td>${escapeHtml(item.field ?? item.type)}</td><td>${escapeHtml(item.before ?? "")}</td><td>${escapeHtml(item.after ?? "")}</td><td>${escapeHtml(item.description ?? "")}</td></tr>`).join("");
  const impacts = impactList(change).map(item => `<li>${escapeHtml(item)}</li>`).join("");
  return `<section class="detail-panel">
    <div class="card-top"><span class="severity ${severityClass(change.severity)}">${escapeHtml(change.severity)}</span>${change.review_required ? '<span class="review-badge">Review</span>' : ""}</div>
    <h2>${escapeHtml(headline(change))}</h2>
    <p class="lead">${escapeHtml(interpSummary(change))}</p>
    <div class="interpretation-block">
      <h2>解釈</h2>
      <ul>${impacts || '<li>想定影響はまだ整理されていません。</li>'}</ul>
      <p class="action-line"><strong>推奨対応:</strong> ${escapeHtml(recommendedAction(change))}</p>
      <p class="guide-note">確度や再通知の読み方は ${guideLink("Guide")} で確認できます。</p>
    </div>
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
  const rows = state.changes.flatMap(change => (change.evidence ?? []).filter(item => item.type === "master_field_diff").map(item => ({ change, item })));
  return `<section class="table-panel"><table class="table"><tr><th>自治体</th><th>制度</th><th>Field</th><th>Before</th><th>After</th><th>Level</th></tr>${rows.map(({ change, item }) => `<tr><td>${escapeHtml(place(change))}</td><td>${escapeHtml(change.program?.name ?? "")}</td><td>${escapeHtml(item.field)}</td><td>${escapeHtml(item.before ?? "")}</td><td>${escapeHtml(item.after ?? "")}</td><td>${escapeHtml(item.evidence_level)}</td></tr>`).join("")}</table></section>`;
}

function renderGuide() {
  return `<section class="guide-panel">
    <section class="guide-intro">
      <p class="lead">Chitan Watch は、社会保険診療報酬支払基金が公開する地単公費マスター関連資料を確認し、変更候補を通知するための監視ページです。</p>
      <p>通知は業務判断の入口です。確度、想定影響、推奨対応を読み、担当範囲に関係するものを公式ソースで確認します。</p>
    </section>
    <section class="guide-section guide-wide">
      <h2>全体像</h2>
      <ol class="flow-list">
        <li><strong>公式ソース</strong><span>社会保険診療報酬支払基金の公開ページから、CSV や PDF などの地単公費マスター関連ファイルを見つけます。</span></li>
        <li><strong>取得と保存</strong><span>GitHub Actions が定期実行し、取得したファイルのハッシュ、取得時刻、実行結果を run として保存します。</span></li>
        <li><strong>差分検知</strong><span>前回の run と今回の run を比べ、公開ファイルの追加、更新、削除、マスター行の追加や変更を change として整理します。</span></li>
        <li><strong>解釈</strong><span>ルールベースの判定で見出し、想定影響、推奨対応、確度を付けます。現在の公開版では外部 LLM に判断を任せていません。</span></li>
        <li><strong>配信</strong><span>GitHub Pages に Web ページ、JSON、RSS を静的ファイルとして公開し、Slack などの RSS リーダーから購読できる形にします。</span></li>
      </ol>
    </section>
    <div class="guide-grid">
      <article class="guide-section">
        <h2>何を見ているか</h2>
        <p>公開元は社会保険診療報酬支払基金の公式ページです。ページ内のリンク、ファイル種別、ファイル本文のハッシュ、地単公費マスターの行内容を確認します。</p>
      </article>
      <article class="guide-section">
        <h2>通知で見る順番</h2>
        <ol>
          <li>対象の自治体、制度名、ファイル名を確認します。</li>
          <li>確度が CONFIRMED か、確認が必要な状態かを見ます。</li>
          <li>想定影響と推奨対応を読み、社内の更新手順に進むか判断します。</li>
        </ol>
      </article>
      <article class="guide-section">
        <h2>画面の構造</h2>
        <dl class="term-list">
          <div><dt>Changes</dt><dd>検知された change の一覧です。通知から来たときの入口になります。</dd></div>
          <div><dt>Detail</dt><dd>選んだ change の根拠、推奨対応、確度、差分項目を確認します。</dd></div>
          <div><dt>Source Health</dt><dd>公式ソースを取得できたか、ファイル状態が変わったかを確認します。</dd></div>
        </dl>
      </article>
      <article class="guide-section">
        <h2>確度の意味</h2>
        <dl class="term-list">
          <div><dt>CONFIRMED</dt><dd>公式ソースや差分から変更候補を確認できた状態です。</dd></div>
          <div><dt>UNRESOLVED</dt><dd>候補はありますが、人の確認が必要な状態です。</dd></div>
          <div><dt>INFO</dt><dd>参考情報として扱う通知です。すぐに更新作業へ進むとは限りません。</dd></div>
        </dl>
      </article>
      <article class="guide-section">
        <h2>想定影響</h2>
        <p>請求、資格確認、患者登録、マスター取込に関係する可能性を示します。影響は施設やシステム構成で変わるため、通知だけで作業完了とは判断しません。</p>
      </article>
      <article class="guide-section">
        <h2>推奨対応</h2>
        <p>CONFIRMED の通知は、公式ページと対象ファイルを確認し、必要に応じて社内マスターや運用メモを更新します。UNRESOLVED の通知は、差分候補の対応関係を人が確認します。</p>
      </article>
      <article class="guide-section">
        <h2>再通知と実変更</h2>
        <p>再通知は、同じ変更候補を改めて知らせるものです。実変更は、公開元の内容やファイルが前回確認時から変わったものです。再通知だけであれば、すぐにマスター更新が必要とは限りません。</p>
      </article>
      <article class="guide-section">
        <h2>更新の価値観</h2>
        <p>このページは、変更を見逃さないための早期検知を重視します。通知は作業命令ではなく、確認すべき入口です。公式ソースで根拠を確認し、施設の運用手順に合わせて反映可否を決めます。</p>
      </article>
      <article class="guide-section">
        <h2>具体例</h2>
        <p>公開ファイル追加の通知なら、まず対象ファイルが利用中の取込対象かを見ます。マスター行変更の通知なら、制度名、公費負担者番号、施行日、差分項目を確認します。</p>
      </article>
    </div>
  </section>`;
}

function renderSources() {
  const run = latestRun();
  const rows = state.sources.map(source => `<tr><td>${escapeHtml(source.title)}</td><td><span class="source-state">${escapeHtml(source.state)}</span></td><td>${escapeHtml(source.type)}</td><td>${escapeHtml(source.sha256 ? source.sha256.slice(0, 12) : "")}</td><td>${escapeHtml(source.error ?? "")}</td></tr>`).join("");
  return `<section class="table-panel"><div class="run-strip"><span class="status-dot ${statusClass(run?.status)}"></span><strong>${escapeHtml(run?.status ?? "NO_RUN")}</strong><span class="meta">Latest: ${escapeHtml(state.latest_run_id ?? "-")}</span></div><table class="table"><tr><th>Source</th><th>State</th><th>Type</th><th>SHA-256</th><th>Error</th></tr>${rows}</table></section>`;
}

function titleFor(route) {
  return ({ "changes": "Changes", "change-detail": "Change Detail", "guide": "Guide", "upcoming": "Upcoming", "master": "Master", "sources": "Source Health" })[route] ?? "Changes";
}

function render() {
  const route = (location.hash.replace("#", "") || "changes").split("/")[0];
  const app = document.querySelector("#app");
  document.querySelector("h1").textContent = titleFor(route);
  document.querySelector(".status-pill").textContent = state.apiOnline ? "API connected" : state.staticExport ? "Static export" : "Fixture fallback";
  app.innerHTML = ({
    changes: renderChanges,
    "change-detail": renderDetail,
    guide: renderGuide,
    upcoming: renderUpcoming,
    master: renderMaster,
    sources: renderSources,
  })[route]?.() ?? renderChanges();
}

addEventListener("hashchange", render);
await loadState();
render();
