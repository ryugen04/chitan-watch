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

async function loadState() {
  try {
    const [runsPayload, changesPayload, sourcePayload] = await Promise.all([
      getJson("/api/runs"),
      getJson("/api/changes"),
      getJson("/api/source-health"),
    ]);
    state = {
      runs: runsPayload.runs ?? [],
      changes: changesPayload.changes ?? [],
      sources: sourcePayload.sources ?? [],
      latest_run_id: sourcePayload.latest_run_id ?? runsPayload.runs?.[0]?.run_id ?? null,
      apiOnline: true,
    };
  } catch (_error) {
    state = fallbackState;
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
    <h2><a href="#change-detail/${encodeURIComponent(change.id)}">${escapeHtml(place(change))}<br>${escapeHtml(change.program?.name ?? "地単公費マスター")}</a></h2>
    <p>${escapeHtml(change.summary)}</p>
    <p class="meta">施行: ${escapeHtml(change.effective_from ?? "未確定")} / 検知: ${escapeHtml(formatDate(change.detected_at))}</p>
    <div class="tags">${(change.change_categories ?? []).map(item => `<span>${escapeHtml(item)}</span>`).join("")}</div>
  </article>`).join("");
  return `${kpis()}<div class="grid">${rows || '<section class="empty">変更はまだありません。</section>'}</div>`;
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
  return `<section class="detail-panel">
    <div class="card-top"><span class="severity ${severityClass(change.severity)}">${escapeHtml(change.severity)}</span>${change.review_required ? '<span class="review-badge">Review</span>' : ""}</div>
    <h2>${escapeHtml(place(change))} ${escapeHtml(change.program?.name ?? "地単公費マスター")}</h2>
    <p>${escapeHtml(change.summary)}</p>
    <dl class="facts"><div><dt>Run</dt><dd>${escapeHtml(change.run_id)}</dd></div><div><dt>公費負担者番号</dt><dd>${escapeHtml(change.program?.public_funding_number ?? "")}</dd></div><div><dt>施行</dt><dd>${escapeHtml(change.effective_from ?? "未確定")}</dd></div></dl>
    <h2>Evidence</h2>
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

function renderSources() {
  const run = latestRun();
  const rows = state.sources.map(source => `<tr><td>${escapeHtml(source.title)}</td><td><span class="source-state">${escapeHtml(source.state)}</span></td><td>${escapeHtml(source.type)}</td><td>${escapeHtml(source.sha256 ? source.sha256.slice(0, 12) : "")}</td><td>${escapeHtml(source.error ?? "")}</td></tr>`).join("");
  return `<section class="table-panel"><div class="run-strip"><span class="status-dot ${statusClass(run?.status)}"></span><strong>${escapeHtml(run?.status ?? "NO_RUN")}</strong><span class="meta">Latest: ${escapeHtml(state.latest_run_id ?? "-")}</span></div><table class="table"><tr><th>Source</th><th>State</th><th>Type</th><th>SHA-256</th><th>Error</th></tr>${rows}</table></section>`;
}

function titleFor(route) {
  return ({ "changes": "Changes", "change-detail": "Change Detail", "upcoming": "Upcoming", "master": "Master", "sources": "Source Health" })[route] ?? "Changes";
}

function render() {
  const route = (location.hash.replace("#", "") || "changes").split("/")[0];
  const app = document.querySelector("#app");
  document.querySelector("h1").textContent = titleFor(route);
  document.querySelector(".status-pill").textContent = state.apiOnline ? "API connected" : "Fixture fallback";
  app.innerHTML = ({
    changes: renderChanges,
    "change-detail": renderDetail,
    upcoming: renderUpcoming,
    master: renderMaster,
    sources: renderSources,
  })[route]?.() ?? renderChanges();
}

addEventListener("hashchange", render);
await loadState();
render();
