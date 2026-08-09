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
    { artifact_id: "art_master_csv", title: "Master CSV", type: "master_csv", state: "changed", sha256: "fixture", error: null, source_group: "official-materials", monitor_mode: "semantic_diff", notify_policy: "always", review_policy: "conditional" },
    { artifact_id: "art_schema", title: "Schema PDF", type: "schema", state: "unchanged", sha256: "fixture", error: null, source_group: "official-materials", monitor_mode: "file_hash", notify_policy: "always", review_policy: "conditional" },
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
  return `${kpis()}<p class="page-note">公費制度、データ構造、通知の読み方は ${guideLink("公費制度ガイド")} にまとめています。</p><div class="grid">${rows || '<section class="empty">変更はまだありません。</section>'}</div>`;
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
      <p class="guide-note">公費制度の背景、確度、再通知の読み方は ${guideLink("公費制度ガイド")} で確認できます。</p>
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
      <p class="eyebrow">公費制度ガイド</p>
      <p class="lead">Chitan Watch は、地方自治体の医療費助成制度に関わる地単公費マスターの公開資料を追い、変更候補を理解しやすい形で届けるための静的監視サイトです。</p>
      <p>初めて見る人が迷いやすいのは、通知そのものよりも「公費とは何か」「マスターのどの列が業務に効くのか」「公式ファイルの更新をどこまで信じてよいのか」です。このページでは、その前提から順に整理します。</p>
    </section>
    <section class="guide-section guide-wide">
      <h2>公費制度の入口</h2>
      <p>医療機関の窓口では、健康保険だけでなく、国や自治体の助成制度によって患者負担が軽くなることがあります。地単公費は、地方自治体が独自に実施する医療費助成事業を扱う領域です。こども医療、ひとり親家庭、重度心身障害者など、自治体ごとに名称、対象者、負担方法、開始日が異なります。</p>
      <p>支払基金の地単公費関連ページでは、地方単独医療費助成事業を扱うマスター、事業一覧、登録や変更のための資料が公開されています。Chitan Watch は、この公開資料を起点にしています。</p>
    </section>
    <section class="guide-section guide-wide">
      <h2>全体像</h2>
      <ol class="flow-list">
        <li><strong>制度</strong><span>自治体が医療費助成事業を設計します。対象者、自己負担、所得制限、現物給付か償還払いかといった運用条件が制度の中身です。</span></li>
        <li><strong>マスター</strong><span>制度を医療機関やシステムが扱えるよう、公費負担者番号、制度名、都道府県や市町村、施行日、分類などの行データにします。</span></li>
        <li><strong>公開資料</strong><span>支払基金などの公式サイトに、CSV、Excel、PDF、ZIP 形式の資料が掲載されます。ファイル名や掲載日が業務上の手がかりになります。</span></li>
        <li><strong>検知</strong><span>GitHub Actions が公開ページを確認し、前回保存したファイルやマスター行と比べます。ファイル追加、更新、削除、行変更を change として記録します。</span></li>
        <li><strong>判断</strong><span>通知は作業命令ではありません。担当システムの取込対象か、公式資料で根拠を確認できるか、社内手順に進めるかを人が判断します。</span></li>
      </ol>
    </section>
    <div class="guide-grid">
      <article class="guide-section">
        <h2>地単公費マスターとは</h2>
        <p>制度をコンピューターが扱うための一覧表です。自治体名や制度名だけでは請求処理に使いにくいため、公費負担者番号、制度分類、適用期間などをそろえた形で管理します。</p>
      </article>
      <article class="guide-section">
        <h2>行データの見方</h2>
        <dl class="term-list">
          <div><dt>公費負担者番号</dt><dd>制度を識別するための番号です。請求、資格確認、マスター取込で重要なキーになります。</dd></div>
          <div><dt>自治体コード</dt><dd>都道府県や市町村を表します。同じ制度名でも自治体が違えば別の扱いになります。</dd></div>
          <div><dt>施行日</dt><dd>制度やマスター行がいつから効くかを示します。通知日と施行日は別の概念です。</dd></div>
        </dl>
      </article>
      <article class="guide-section">
        <h2>現物給付と償還払い</h2>
        <p>現物給付は、窓口や請求の時点で助成を反映する運用です。償還払いは、患者がいったん支払い、後から自治体へ申請して払い戻しを受ける運用です。マスター監視で特に問題になりやすいのは、システム処理に乗る現物給付側です。</p>
      </article>
      <article class="guide-section">
        <h2>Chitan Watch の設計</h2>
        <p>サイトはサーバーを持たず、GitHub Pages で静的ファイルとして公開します。Source Registry に登録した公式ページと資料を定期確認し、生成した JSON を画面が読みます。RSS は同じ変更データから作ります。</p>
      </article>
      <article class="guide-section">
        <h2>現在の監視範囲</h2>
        <p>MVP では、支払基金の地単公費マスター関連ページ、確定事業一覧 CSV と Excel、項目一覧、入力要領、入力例、FAQ、委託状況、厚労省の関連資料を監視します。自治体個別ページは公式裏取り候補として段階導入します。</p>
      </article>
      <article class="guide-section">
        <h2>データの構造</h2>
        <dl class="term-list">
          <div><dt>run</dt><dd>ある時点のクロール実行です。取得時刻、成功状態、検知数、ソース状態を持ちます。</dd></div>
          <div><dt>source</dt><dd>確認対象の公式ページや公開ファイルです。取得失敗やハッシュ変化もここで見ます。</dd></div>
          <div><dt>change</dt><dd>利用者が読む通知単位です。severity、confidence、evidence、recommended action を持ちます。</dd></div>
          <div><dt>evidence</dt><dd>変更候補の根拠です。差分項目、前後値、公式ソース URL、確認レベルを残します。</dd></div>
        </dl>
      </article>
      <article class="guide-section">
        <h2>解釈の境界</h2>
        <p>現在の公開版では、外部 LLM に判断を任せていません。見出し、想定影響、推奨対応、確度はルールベースで付けています。制度の最終判断、請求可否、施設ごとの運用判断は公式資料と社内手順で確認します。</p>
      </article>
      <article class="guide-section">
        <h2>通知で見る順番</h2>
        <ol>
          <li>対象の自治体、制度名、ファイル名を確認します。</li>
          <li>施行日と検知日時を分けて見ます。</li>
          <li>確度、想定影響、推奨対応を読みます。</li>
          <li>Detail の根拠と公式ソースを確認します。</li>
        </ol>
      </article>
      <article class="guide-section">
        <h2>確度の意味</h2>
        <dl class="term-list">
          <div><dt>CONFIRMED</dt><dd>公式ソースや差分から変更候補を確認できた状態です。業務反映の前には対象システムとの対応を確認します。</dd></div>
          <div><dt>UNRESOLVED</dt><dd>候補はありますが、対応関係や行の同一性に人の確認が必要な状態です。</dd></div>
          <div><dt>INFO</dt><dd>参考情報として扱う通知です。すぐに更新作業へ進むとは限りません。</dd></div>
        </dl>
      </article>
      <article class="guide-section">
        <h2>更新の流れ</h2>
        <p>自治体側の制度変更があり、公式資料が更新され、Chitan Watch が差分を検知し、RSS と画面に反映されます。通知が来た時点では、制度変更そのものがすでに始まっている場合も、将来の施行に向けた準備期間の場合もあります。</p>
      </article>
      <article class="guide-section">
        <h2>業務での受け止め方</h2>
        <p>通知は「調べるべき候補」を早く見つけるためのものです。マスター取込、資格確認、患者登録、請求点検のどれに関係するかを切り分け、施設やベンダーの更新手順に沿って扱います。</p>
      </article>
      <article class="guide-section">
        <h2>再通知と実変更</h2>
        <p>再通知は、同じ変更候補を改めて知らせるものです。実変更は、公開元の内容やファイルが前回確認時から変わったものです。再通知だけであれば、すぐにマスター更新が必要とは限りません。</p>
      </article>
      <article class="guide-section">
        <h2>よくある読み違い</h2>
        <p>公費負担者番号だけで制度や作業内容を決めると、自治体、適用期間、制度分類の違いを見落とします。ファイルの公開日、検知日時、施行日も別の意味を持ちます。</p>
      </article>
      <article class="guide-section">
        <h2>具体例</h2>
        <p>「地単公費マスター確定事業一覧」の CSV が追加された通知なら、まず自施設が取り込む対象かを見ます。マスター行変更なら、公費負担者番号、制度名、自治体、施行日、差分項目を Detail で確認します。</p>
      </article>
    </div>
    <section class="guide-section guide-wide">
      <h2>情報源</h2>
      <ul class="source-list">
        <li><a href="https://www.ssk.or.jp/seikyushiharai/chitan/chitan_01.html" target="_blank" rel="noopener">社会保険診療報酬支払基金 地方単独医療費助成事業関連情報</a></li>
        <li><a href="https://shinryohoshu.mhlw.go.jp/shinryohoshu/" target="_blank" rel="noopener">診療報酬情報提供サービス</a></li>
        <li><a href="https://www.mhlw.go.jp/" target="_blank" rel="noopener">厚生労働省</a></li>
      </ul>
    </section>
  </section>`;
}

function renderSources() {
  const run = latestRun();
  const groups = state.sources.reduce((acc, source) => {
    const key = source.source_group || "uncategorized";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
  const groupText = Object.entries(groups).map(([name, count]) => `${escapeHtml(name)} ${count}`).join(" / ");
  const rows = state.sources.map(source => `<tr><td>${escapeHtml(source.title)}</td><td><span class="source-state">${escapeHtml(source.state)}</span></td><td>${escapeHtml(source.type)}</td><td>${escapeHtml(source.source_group ?? "")}</td><td>${escapeHtml(source.monitor_mode ?? "")}</td><td>${escapeHtml(source.notify_policy ?? "")}</td><td>${escapeHtml(source.review_policy ?? "")}</td><td>${escapeHtml(source.sha256 ? source.sha256.slice(0, 12) : "")}</td><td>${escapeHtml(source.error ?? "")}</td></tr>`).join("");
  return `<section class="table-panel"><div class="run-strip"><span class="status-dot ${statusClass(run?.status)}"></span><strong>${escapeHtml(run?.status ?? "NO_RUN")}</strong><span class="meta">Latest: ${escapeHtml(state.latest_run_id ?? "-")}</span></div><p class="page-note">監視対象: ${groupText || "未設定"}</p><table class="table"><tr><th>Source</th><th>State</th><th>Type</th><th>Group</th><th>Monitor</th><th>Notify</th><th>Review</th><th>SHA-256</th><th>Error</th></tr>${rows}</table></section>`;
}

function titleFor(route) {
  return ({ "changes": "Changes", "change-detail": "Change Detail", "guide": "公費制度ガイド", "upcoming": "Upcoming", "master": "Master", "sources": "Source Health" })[route] ?? "Changes";
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
