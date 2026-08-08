const changes = [
  {
    id: "chg_fixture_tokyo_age",
    severity: "HIGH",
    place: "東京都 千代田区",
    program: "こども医療費助成",
    effectiveFrom: "2026-10-01",
    detectedAt: "2026-08-03",
    summary: "対象年齢条件が 18 歳未満から 22 歳未満へ変更されたサンプルです。",
    impacts: ["eligibility-determination", "patient-registration", "testing"],
  },
  {
    id: "chg_fixture_schema",
    severity: "CRITICAL",
    place: "全国",
    program: "地単公費マスター schema",
    effectiveFrom: null,
    detectedAt: "2026-08-03",
    summary: "項目一覧の変更を schema break として review queue に送るサンプルです。",
    impacts: ["master-import", "operations"],
  },
];

const sources = [
  ["SSK Hub", "OK", "2026-08-08 06:00 JST", "8 artifacts"],
  ["Master CSV", "OK", "2026-08-03", "CSV UTF-8"],
  ["Schema PDF", "OK", "2026-03-30", "PDF"],
  ["MHLW Hub", "OK", "2026-01-28", "HTML/PDF"],
];

function severityClass(value) {
  if (value === "HIGH" || value === "CRITICAL") return "high";
  if (value === "MEDIUM") return "medium";
  return "info";
}

function renderChanges() {
  return `<div class="kpis"><div class="kpi"><span class="meta">Open changes</span><strong>2</strong></div><div class="kpi"><span class="meta">Review queue</span><strong>1</strong></div><div class="kpi"><span class="meta">Crawler state</span><strong>OK</strong></div></div><div class="grid">${changes.map(change => `<article class="card"><span class="severity ${severityClass(change.severity)}">${change.severity}</span><h2>${change.place}<br>${change.program}</h2><p>${change.summary}</p><p class="meta">施行: ${change.effectiveFrom ?? "未確定"} / 検知: ${change.detectedAt}</p></article>`).join("")}</div>`;
}

function renderDetail() {
  const change = changes[0];
  return `<section class="detail-panel"><span class="severity high">${change.severity}</span><h2>${change.place} ${change.program}</h2><p>${change.summary}</p><h2>Structured Diff</h2><table class="table"><tr><th>項目</th><th>Before</th><th>After</th></tr><tr><td>age_upper</td><td>18</td><td>22</td></tr><tr><td>valid_from</td><td>2025-04-01</td><td>2026-10-01</td></tr></table><h2>Evidence</h2><p class="meta">CONFIRMED: master_diff fixture. INFERRED: vendor impact candidates only.</p></section>`;
}

function renderUpcoming() {
  return `<section class="table-panel"><table class="table"><tr><th>施行日</th><th>自治体</th><th>制度</th><th>Severity</th></tr>${changes.filter(c => c.effectiveFrom).map(c => `<tr><td>${c.effectiveFrom}</td><td>${c.place}</td><td>${c.program}</td><td>${c.severity}</td></tr>`).join("")}</table></section>`;
}

function renderMaster() {
  return `<section class="detail-panel"><h2>東京都 千代田区 / こども医療費助成</h2><table class="table"><tr><th>Version</th><th>有効期間</th><th>対象年齢</th></tr><tr><td>1</td><td>2025-04-01 - 2026-09-30</td><td>18歳未満</td></tr><tr><td>2</td><td>2026-10-01 -</td><td>22歳未満</td></tr></table></section>`;
}

function renderSources() {
  return `<section class="table-panel"><table class="table"><tr><th>Source</th><th>Status</th><th>Last success</th><th>Detail</th></tr>${sources.map(row => `<tr><td>${row[0]}</td><td>${row[1]}</td><td>${row[2]}</td><td>${row[3]}</td></tr>`).join("")}</table></section>`;
}

function render() {
  const route = location.hash.replace("#", "") || "changes";
  const app = document.querySelector("#app");
  document.querySelector("h1").textContent = route === "change-detail" ? "Change Detail" : route.replace(/^./, c => c.toUpperCase());
  app.innerHTML = {
    "changes": renderChanges,
    "change-detail": renderDetail,
    "upcoming": renderUpcoming,
    "master": renderMaster,
    "sources": renderSources,
  }[route]?.() ?? renderChanges();
}

addEventListener("hashchange", render);
render();
