const $ = id => document.getElementById(id);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const state = {
  page: "home",
  runs: [],
  metrics: [],
  approvals: [],
  policies: [],
  settings: null,
  identity: null,
  lastReport: "",
  editingSource: null,
  editingIntegration: null,
};

const PAGES = {
  home: "Home",
  agents: "Agents",
  data: "Data Agent",
  "knowledge-agent": "Knowledge Agent",
  ops: "Ops Agent",
  supervisor: "Supervisor",
  knowledge: "Knowledge",
  "data-sources": "Data sources",
  runs: "Runs",
  evaluations: "Evaluations",
  approvals: "Approvals",
  integrations: "Integrations",
  credentials: "Credentials",
  policies: "Policies",
  settings: "Settings",
};

const AGENTS = {
  data: {page:"data", name:"Data Agent", kind:"Analytics", desc:"Natural-language analytics with schema-aware, guarded SQL.", icon:"database", cls:""},
  knowledge: {page:"knowledge-agent", name:"Knowledge Agent", kind:"RAG", desc:"Role-scoped retrieval with citations and versioned knowledge.", icon:"book", cls:"knowledge"},
  ops: {page:"ops", name:"Ops Agent", kind:"Operations", desc:"Infrastructure evidence, diagnostics, and governed actions.", icon:"activity", cls:"ops"},
  supervisor: {page:"supervisor", name:"Supervisor", kind:"Orchestration", desc:"Cross-agent incident investigation and evidence synthesis.", icon:"bot", cls:"supervisor"},
};

const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({
  "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
}[c]));

const icon = name => '<svg><use href="#i-' + name + '"/></svg>';
const duration = ms => ms >= 1000 ? (ms / 1000).toFixed(ms >= 10000 ? 1 : 2) + "s" : (ms ?? 0) + "ms";
const shortId = value => value ? String(value).slice(0, 8) : "—";
const titleCase = value => String(value || "").replace(/(^|[_-])([a-z])/g, (_, p, c) => (p ? " " : "") + c.toUpperCase());
const bytes = n => n == null ? "—" : n >= 1073741824 ? (n/1073741824).toFixed(1)+" GB" : n >= 1048576 ? (n/1048576).toFixed(1)+" MB" : n >= 1024 ? Math.round(n/1024)+" KB" : n+" B";

function toast(message, type = "ok") {
  const el = $("toast");
  el.textContent = message;
  el.className = "toast show" + (type === "error" ? " error" : "");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => el.className = "toast", 2600);
}

function token() { return localStorage.getItem("apiToken") || ""; }

async function api(url, options = {}) {
  const headers = new Headers(options.headers || {});
  if (token()) headers.set("Authorization", "Bearer " + token());
  const response = await fetch(url, {...options, headers});
  const type = response.headers.get("content-type") || "";
  const data = type.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = data?.error?.message || data?.detail || (typeof data === "string" ? data : JSON.stringify(data));
    throw new Error(detail);
  }
  return data;
}
const post = (url, body) => api(url, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
const put = (url, body) => api(url, {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});

function setNav(page) {
  const navPage = ["data","knowledge-agent","ops","supervisor"].includes(page) ? "agents" : page;
  $$(".nav-item").forEach(el => el.classList.toggle("active", el.dataset.page === navPage));
}

function navigate(page) {
  if (!PAGES[page]) return;
  state.page = page;
  setNav(page);
  $$(".page").forEach(el => el.classList.toggle("active", el.dataset.pagePanel === page));
  history.replaceState(null, "", "#" + page);
  refreshPage(page);
  window.scrollTo({top:0, behavior:"smooth"});
}

async function refreshPage(page) {
  try {
    if (page === "home") await loadHome();
    if (page === "agents") await loadAgentDirectory();
    if (page === "data") await Promise.all([loadSources(), loadSchema()]);
    if (page === "ops") await loadOps();
    if (page === "supervisor") await loadSources();
    if (page === "knowledge") await loadKnowledgeDocs();
    if (page === "data-sources") await loadDataSourcesPage();
    if (page === "runs") await loadRuns();
    if (page === "evaluations") await loadEvaluations();
    if (page === "approvals") await loadApprovals();
    if (page === "integrations") await loadIntegrations();
    if (page === "credentials") await loadCredentials();
    if (page === "policies") await loadPolicies();
    if (page === "settings") await Promise.all([loadIdentity(), loadRuntimeSettings()]);
  } catch (error) {
    toast(error.message, "error");
  }
}

async function loadIdentity() {
  try {
    const me = await api("/api/v1/auth/me");
    state.identity = me;
    $("sidebarUser").textContent = me.username;
    $("sidebarRole").textContent = me.role;
    $("homeUser").textContent = me.username;
    if ($("identityName")) $("identityName").textContent = me.username;
    if ($("identityRole")) $("identityRole").textContent = me.role;
  } catch (error) {
    $("sidebarUser").textContent = "Sign in";
    $("sidebarRole").textContent = "authentication required";
  }
}

async function getPlatformSettings(force = false) {
  if (state.settings && !force) return state.settings;
  state.settings = await api("/api/v1/platform/settings");
  return state.settings;
}

function metricFor(agent) { return state.metrics.find(x => x.agent === agent); }
function latestRun(agent) { return state.runs.find(x => x.agent === agent); }

async function loadHome() {
  const [metrics, runs, approvals, settings] = await Promise.all([
    api("/api/v1/platform/metrics?limit=200").catch(() => []),
    api("/api/v1/platform/runs?limit=200").catch(() => []),
    api("/api/v1/platform/approvals?limit=50").catch(() => []),
    getPlatformSettings(true).catch(() => null),
  ]);
  state.metrics = metrics;
  state.runs = runs;
  state.approvals = approvals;
  if (settings) state.settings = settings;
  await loadIdentity();

  const total = metrics.reduce((sum, x) => sum + x.runs, 0);
  const successes = metrics.reduce((sum, x) => sum + x.runs * x.success_rate / 100, 0);
  const evalWeighted = metrics.reduce((sum, x) => sum + x.runs * x.eval_avg_score, 0);
  $("metricRuns").textContent = total.toLocaleString();
  $("metricSuccess").textContent = total ? Math.round(successes / total * 100) + "%" : "—";
  $("metricP95").textContent = metrics.length ? duration(Math.max(...metrics.map(x => x.p95_duration_ms))) : "—";
  $("metricEval").textContent = total ? Math.round(evalWeighted / total) : "—";
  renderAttention(settings);
  renderHomeAgents();
  renderActivity();
  renderPerformance(metrics);
  updateApprovalCount();
}

function renderAttention(settings) {
  const items = [];
  const pending = state.approvals.filter(x => x.status === "pending");
  if (pending.length) items.push({
    tone:"warning", icon:"approval", title:pending.length + " approval request" + (pending.length > 1 ? "s are" : " is") + " waiting",
    sub:"Sensitive actions require human review before execution.", page:"approvals"
  });

  for (const [key, agent] of Object.entries(AGENTS)) {
    const last = latestRun(key);
    if (last?.status === "error") items.push({
      tone:"warning", icon:"activity", title:agent.name + " has a failed recent run",
      sub:"Run #" + last.id + " · " + (last.error_type || "Execution error"), page:"runs"
    });
  }

  if (settings && !settings.llm_model) items.push({
    tone:"warning", icon:"key", title:"No chat model is configured",
    sub:"Connect a model provider before running AI-powered agents.", page:"credentials"
  });

  if (!items.length) items.push({
    tone:"success", icon:"check", title:"Platform is healthy",
    sub:"No pending approvals or recent agent failures need attention.", page:"runs"
  });

  $("attentionList").innerHTML = items.slice(0, 4).map(item =>
    '<div class="attention-item ' + item.tone + '"><div class="attention-icon">' + icon(item.icon) +
    '</div><div><strong>' + esc(item.title) + '</strong><span>' + esc(item.sub) +
    '</span></div><button data-go="' + item.page + '">' + icon("arrow") + '</button></div>'
  ).join("");
  bindGo($("attentionList"));
}

function agentStatus(agent) {
  const metric = metricFor(agent);
  const last = latestRun(agent);
  if (last?.status === "error") return {label:"Degraded", cls:"warning"};
  if (!metric) return {label:"No data", cls:"neutral"};
  return {label:"Healthy", cls:"healthy"};
}

function agentRow(key, large = false) {
  const a = AGENTS[key];
  const metric = metricFor(key);
  const last = latestRun(key);
  const status = agentStatus(key);
  const meta = metric
    ? '<span>' + metric.success_rate + '% success</span><span>P95 ' + esc(duration(metric.p95_duration_ms)) + '</span><span>' + metric.runs + ' runs</span>'
    : '<span>No runtime metrics</span>';
  return '<div class="resource-row" data-agent-page="' + a.page + '" data-agent-key="' + key + '">' +
    '<div class="resource-icon ' + a.cls + '">' + icon(a.icon) + '</div>' +
    '<div class="resource-main"><strong>' + esc(a.name) + '</strong><p>' + esc(a.desc) + '</p></div>' +
    '<div class="resource-actions"><div class="resource-meta">' + meta + '</div><span class="status-chip ' + status.cls + '">' + status.label + '</span>' +
    (last ? '<button class="icon-btn" data-open-run="' + last.id + '" title="Open latest run">' + icon("chevron") + '</button>' : '') + '</div></div>';
}

function bindAgentRows(root) {
  $$("[data-agent-page]", root).forEach(row => row.onclick = e => {
    if (e.target.closest("[data-open-run]")) return;
    navigate(row.dataset.agentPage);
  });
  $$("[data-open-run]", root).forEach(button => button.onclick = e => {
    e.stopPropagation();
    openRun(button.dataset.openRun);
  });
}

function renderHomeAgents() {
  $("homeAgents").innerHTML = Object.keys(AGENTS).map(key => agentRow(key)).join("");
  bindAgentRows($("homeAgents"));
}

async function loadAgentDirectory() {
  const [metrics, runs] = await Promise.all([
    api("/api/v1/platform/metrics?limit=200").catch(() => []),
    api("/api/v1/platform/runs?limit=200").catch(() => []),
  ]);
  state.metrics = metrics; state.runs = runs;
  renderAgentDirectory();
}

function renderAgentDirectory() {
  const q = ($("agentSearch").value || "").trim().toLowerCase();
  const keys = Object.keys(AGENTS).filter(key => {
    const a = AGENTS[key];
    return !q || [a.name,a.kind,a.desc].some(v => v.toLowerCase().includes(q));
  });
  $("agentCount").textContent = keys.length + " agent" + (keys.length === 1 ? "" : "s");
  $("agentDirectory").innerHTML = keys.map(key => agentRow(key, true)).join("");
  bindAgentRows($("agentDirectory"));
}

function renderActivity() {
  const events = [
    ...state.runs.slice(0, 12).map(x => ({
      time:x.created_at, tone:x.status === "ok" ? "success" : "error",
      title:(AGENTS[x.agent]?.name || titleCase(x.agent)) + " " + (x.status === "ok" ? "completed" : "failed") + " run #" + x.id,
      sub:duration(x.duration_ms) + (x.error_type ? " · " + x.error_type : "")
    })),
    ...state.approvals.slice(0, 12).map(x => ({
      time:x.created_at, tone:x.status === "pending" ? "warning" : x.status === "rejected" ? "error" : "success",
      title:titleCase(x.tool) + " approval " + x.status,
      sub:(x.requested_by || "unknown") + " · " + x.target
    }))
  ].sort((a,b) => String(b.time).localeCompare(String(a.time))).slice(0, 7);

  $("activityFeed").innerHTML = events.length ? events.map(e =>
    '<div class="activity-item"><span class="activity-dot ' + e.tone + '"></span><div><strong>' + esc(e.title) +
    '</strong><span>' + esc(e.sub) + ' · ' + esc(e.time) + '</span></div></div>'
  ).join("") : '<div class="empty-state">No activity yet.</div>';
}

function renderPerformance(metrics) {
  const root = $("performanceChart");
  if (!metrics.length) { root.innerHTML = '<div class="empty-state">Run an agent to populate runtime metrics.</div>'; return; }
  const maxLatency = Math.max(...metrics.map(x => x.p95_duration_ms), 1);
  root.innerHTML = metrics.map(m => {
    const successHeight = Math.max(3, m.success_rate * 1.05);
    const latencyHeight = Math.max(3, m.p95_duration_ms / maxLatency * 105);
    return '<div class="performance-column"><div class="performance-bars"><div class="performance-bar" style="height:' +
      successHeight + 'px" title="Success ' + m.success_rate + '%"></div><div class="performance-bar latency" style="height:' +
      latencyHeight + 'px" title="P95 ' + esc(duration(m.p95_duration_ms)) + '"></div></div><strong>' +
      esc(AGENTS[m.agent]?.name || m.agent) + '</strong><small>' + m.success_rate + '% · ' + esc(duration(m.p95_duration_ms)) + '</small></div>';
  }).join("");
}

async function loadSources() {
  const sources = await api("/api/v1/data/sources");
  const html = sources.map(x => '<option value="' + esc(x.name) + '">' + esc(x.name) + (x.schema_name ? " · " + esc(x.schema_name) : "") + '</option>').join("");
  $("dataSource").innerHTML = html;
  $("supervisorSource").innerHTML = html;
}

async function loadSchema() {
  try {
    const source = $("dataSource").value || "default";
    const schema = await api("/api/v1/data/schema?source=" + encodeURIComponent(source));
    $("schema").innerHTML = schema.tables?.length ? schema.tables.map(t =>
      '<div class="schema-item"><strong>' + esc(t.name) + '</strong><span>' +
      t.columns.map(c => esc(c.name) + " · " + esc(c.type)).join("<br>") + '</span></div>'
    ).join("") : '<div class="empty-state">No tables found.</div>';
  } catch (error) { $("schema").innerHTML = '<div class="empty-state">' + esc(error.message) + '</div>'; }
}

function renderTrace(id, trace = []) {
  const root = $(id);
  if (!trace.length) { root.className = "trace-stack empty-state"; root.innerHTML = "No trace available."; return; }
  root.className = "trace-stack";
  root.innerHTML = trace.map(step => '<div class="trace-step ' + (step.status === "error" ? "error" : "") +
    '"><strong>' + esc(titleCase(step.name)) + '</strong><span>' + esc(step.kind) + (step.detail ? " · " + esc(step.detail) : "") + '</span></div>').join("");
}

function renderDataChart(chart) {
  const root = $("dataChart");
  if (!chart?.labels?.length) { root.innerHTML = ""; return; }
  const max = Math.max(...chart.values.map(v => Math.abs(Number(v) || 0)), 1);
  root.innerHTML = '<div class="chart-bars">' + chart.labels.map((label,i) =>
    '<div class="chart-row"><span>' + esc(label) + '</span><div class="chart-track"><div class="chart-fill" style="width:' +
    Math.max(2, Math.abs(Number(chart.values[i]) || 0) / max * 100) + '%"></div></div><strong>' + esc(chart.values[i]) + '</strong></div>'
  ).join("") + '</div>';
}

function renderQueryTable(data) {
  if (!data?.rows?.length) { $("table").innerHTML = ""; return; }
  $("table").innerHTML = '<div class="dense-table"><table><thead><tr>' + data.columns.map(c => '<th>' + esc(c) + '</th>').join("") +
    '</tr></thead><tbody>' + data.rows.map(row => '<tr>' + data.columns.map(c => '<td>' + esc(row[c]) + '</td>').join("") + '</tr>').join("") +
    '</tbody></table></div>';
}

async function runDataAsk() {
  $("dataAnswer").textContent = "Analyzing schema and generating a guarded query…";
  $("dataAsk").disabled = true;
  try {
    const d = await post("/api/v1/data/ask", {question:$("dataQuestion").value, source:$("dataSource").value});
    $("dataAnswer").textContent = d.answer + (d.insights?.length ? "\n\n" + d.insights.map(x => "• " + x).join("\n") : "") + (d.sql ? "\n\nSQL\n" + d.sql : "");
    state.lastReport = d.report_markdown || "";
    $("downloadReport").disabled = !state.lastReport;
    renderDataChart(d.chart); renderQueryTable(d.result); renderTrace("dataTrace", d.trace);
    toast("Data Agent completed");
  } catch (error) { $("dataAnswer").textContent = error.message; toast(error.message, "error"); }
  finally { $("dataAsk").disabled = false; }
}

async function runSql() {
  try { renderQueryTable(await post("/api/v1/data/sql", {sql:$("sql").value, source:$("dataSource").value})); toast("Query completed"); }
  catch (error) { toast(error.message, "error"); }
}

function downloadReport() {
  if (!state.lastReport) return;
  const blob = new Blob([state.lastReport], {type:"text/markdown;charset=utf-8"});
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob); link.download = "data-agent-report.md"; link.click(); URL.revokeObjectURL(link.href);
}

async function askKnowledge() {
  $("knowledgeAnswer").textContent = "Retrieving role-scoped knowledge…";
  try {
    const d = await post("/api/v1/knowledge/ask", {question:$("knowledgeQuestion").value});
    $("knowledgeAnswer").textContent = d.answer;
    $("sources").innerHTML = d.sources?.length ? d.sources.map((s,i) =>
      '<div class="source-card"><strong>[' + (i+1) + '] ' + esc(s.title) + '</strong><p>' + esc(s.text) +
      '</p><small>score ' + Number(s.score || 0).toFixed(3) + '</small></div>'
    ).join("") : "";
    renderTrace("knowledgeTrace", d.trace);
  } catch (error) { $("knowledgeAnswer").textContent = error.message; toast(error.message, "error"); }
}

async function loadKnowledgeDocs() {
  try {
    const docs = await api("/api/v1/knowledge/documents");
    $("knowledgeDocs").innerHTML = docs.length ? docs.map(x =>
      '<div class="data-row knowledge-columns"><div><strong>' + esc(x.title) + '</strong><span class="sub">#' + x.document_id +
      '</span></div><div>v' + esc(x.version || 1) + '</div><div>' + esc(x.chunks || 0) + '</div><div>' +
      esc((x.allowed_roles || []).join(", ") || "All") + '</div><div>' + esc((x.tags || []).join(", ") || "—") +
      '</div><div><button class="secondary-btn small" data-delete-doc="' + x.document_id + '" data-title="' + esc(x.title) +
      '">Delete</button></div></div>'
    ).join("") : '<div class="empty-state">No knowledge documents.</div>';
    $$("[data-delete-doc]", $("knowledgeDocs")).forEach(b => b.onclick = () => requestDocumentDelete(b.dataset.deleteDoc, b.dataset.title));
  } catch (error) { $("knowledgeDocs").innerHTML = '<div class="empty-state">' + esc(error.message) + '</div>'; }
}

async function requestDocumentDelete(documentId, title) {
  try {
    await post("/api/v1/platform/approvals", {agent:"knowledge", tool:"document_delete", target:"document:" + documentId, reason:"Delete knowledge document: " + title});
    toast("Deletion approval created"); await updateApprovalCount();
  } catch (error) { toast(error.message, "error"); }
}

async function saveDocument() {
  $("docStatus").textContent = "Saving…";
  try {
    const file = $("docFile").files[0];
    const tags = $("docTags").value.split(",").map(x => x.trim()).filter(Boolean);
    const allowed_roles = $("docRoles").value.split(",").map(x => x.trim()).filter(Boolean);
    let result;
    if (file) {
      const form = new FormData(); form.append("file", file); form.append("tags", tags.join(",")); form.append("allowed_roles", allowed_roles.join(","));
      result = await api("/api/v1/knowledge/documents/upload", {method:"POST", body:form});
    } else if ($("docId").value.trim()) {
      result = await put("/api/v1/knowledge/documents/" + encodeURIComponent($("docId").value.trim()), {title:$("docTitle").value, content:$("docContent").value, tags, allowed_roles});
    } else {
      result = await post("/api/v1/knowledge/documents", {title:$("docTitle").value, content:$("docContent").value, tags, allowed_roles});
    }
    $("docStatus").textContent = "Saved #" + result.document_id; closeModal("docModal"); toast("Document saved"); await loadKnowledgeDocs();
  } catch (error) { $("docStatus").textContent = error.message; toast(error.message, "error"); }
}

async function loadOps() {
  try {
    const d = await api("/api/v1/ops/snapshot");
    const m = d.memory || {}, disk = d.disk || {};
    const memPct = m.MemTotal ? Math.round((m.MemTotal - (m.MemAvailable || 0)) / m.MemTotal * 100) + "%" : bytes(m.MemAvailable) + " free";
    const diskPct = disk.total ? Math.round((disk.total - disk.free) / disk.total * 100) + "%" : bytes(disk.free) + " free";
    const values = [["CPU",(d.cpu_count ?? "—")+" cores"],["Memory",memPct],["Disk",diskPct],["Load",d.load_average ? d.load_average.map(x => Number(x).toFixed(2)).join(" / ") : "—"]];
    $("opsMetrics").innerHTML = values.map(x => '<div><span>' + esc(x[0]) + '</span><strong>' + esc(x[1]) + '</strong></div>').join("");
  } catch (error) { toast(error.message, "error"); }
}

async function diagnoseOps() {
  $("opsAnswer").textContent = "Collecting evidence and diagnosing…";
  try {
    const d = await post("/api/v1/ops/diagnose", {question:$("opsQuestion").value});
    $("opsAnswer").textContent = d.answer; renderTrace("opsTrace", d.trace);
  } catch (error) { $("opsAnswer").textContent = error.message; toast(error.message, "error"); }
}

async function loadLogs() {
  $("opsLogs").textContent = "Loading…";
  try {
    const logs = await api("/api/v1/ops/logs?lines=80");
    $("opsLogs").textContent = logs.length ? logs.map(x => "== "+x.path+" ==\n"+x.lines.join("\n")).join("\n\n") : "No log files configured.";
  } catch (error) { $("opsLogs").textContent = error.message; }
}

async function runPrometheus() {
  $("promResult").textContent = "Querying…";
  try { $("promResult").textContent = JSON.stringify((await post("/api/v1/ops/prometheus/query", {query:$("promQuery").value})).result, null, 2); }
  catch (error) { $("promResult").textContent = error.message; }
}

async function loadRuntime(kind) {
  $("runtimeResult").textContent = "Loading…";
  try { $("runtimeResult").textContent = JSON.stringify((await api("/api/v1/ops/" + kind)).items, null, 2); }
  catch (error) { $("runtimeResult").textContent = error.message; }
}

async function requestServiceRestart() {
  const service = $("restartService").value.trim();
  if (!service) return toast("Enter a service name", "error");
  try {
    await post("/api/v1/platform/approvals", {agent:"ops", tool:"service_restart", target:"service:" + service, reason:"Controlled service restart"});
    toast("Restart approval created"); await updateApprovalCount();
  } catch (error) { toast(error.message, "error"); }
}

function resetGraph() {
  $$("#agentGraph .graph-node").forEach(n => n.classList.remove("running","success","error"));
  document.querySelector('[data-node="incident"]').classList.add("success");
  $("graphStatus").textContent = "Ready";
}
function graphState(name, status) {
  const node = document.querySelector('[data-node="' + name + '"]');
  if (!node) return;
  node.classList.remove("running","success","error");
  if (status) node.classList.add(status);
}
function renderSupervisorResult(d) {
  $("supervisorAnswer").textContent = d.answer || "No conclusion returned.";
  $("supervisorFindings").innerHTML = d.findings?.length ? d.findings.map(x => '<div class="source-card"><strong>' +
    esc(AGENTS[x.agent]?.name || titleCase(x.agent)) + ' · ' + esc(titleCase(x.status)) + '</strong><p>' + esc(x.summary) + '</p></div>').join("") : "";
  renderTrace("supervisorTrace", d.trace);
  graphState("supervisor","success");
  ["ops","knowledge","data"].forEach(agent => {
    const item = d.findings?.find(x => x.agent === agent);
    graphState(agent, item?.status === "error" ? "error" : "success");
  });
  graphState("synthesize","success"); $("graphStatus").textContent = "Completed";
}
async function investigate(demo = false) {
  resetGraph(); graphState("supervisor","running"); ["ops","knowledge","data"].forEach(x => graphState(x,"running")); $("graphStatus").textContent = "Running";
  $("supervisorAnswer").textContent = demo ? "Building isolated demo evidence…" : "Supervisor is delegating the investigation…";
  try {
    const result = demo ? await post("/api/v1/platform/demo/incident", {}) : await post("/api/v1/supervisor/investigate", {question:$("supervisorQuestion").value, source:$("supervisorSource").value});
    const answer = demo ? result.answer : result;
    if (demo && answer.question) $("supervisorQuestion").value = answer.question;
    renderSupervisorResult(answer); toast("Investigation completed");
  } catch (error) { graphState("supervisor","error"); $("graphStatus").textContent = "Failed"; $("supervisorAnswer").textContent = error.message; toast(error.message,"error"); }
}

async function loadRuns() {
  const agent = $("runAgentFilter").value;
  const url = "/api/v1/platform/runs?limit=200" + (agent ? "&agent=" + encodeURIComponent(agent) : "");
  state.runs = await api(url); renderRuns();
}
function renderRuns() {
  const status = $("runStatusFilter").value, q = $("runSearch").value.trim().toLowerCase();
  const rows = state.runs.filter(run => (!status || run.status === status) && (!q || [run.id,run.request_id,run.correlation_id,run.agent].some(v => String(v || "").toLowerCase().includes(q))));
  $("runsTable").innerHTML = rows.length ? rows.map(run =>
    '<tr><td><span class="status-dot-inline ' + (run.status === "error" ? "error" : "") + '">' + (run.status === "ok" ? "Success" : "Error") +
    '</span></td><td><button class="run-button" data-run-id="' + run.id + '">#' + run.id + '</button></td><td><div class="agent-cell"><div class="agent-mini-icon">' +
    esc((AGENTS[run.agent]?.name || run.agent).slice(0,1)) + '</div>' + esc(AGENTS[run.agent]?.name || titleCase(run.agent)) + '</div></td><td>' + esc(duration(run.duration_ms)) +
    '</td><td>' + esc(shortId(run.request_id)) + '</td><td>' + esc(shortId(run.correlation_id)) + '</td><td>' + esc(run.created_at) +
    '</td><td><button class="link-button" data-run-id="' + run.id + '">Inspect ' + icon("arrow") + '</button></td></tr>'
  ).join("") : '<tr><td colspan="8" class="empty-state">No matching runs.</td></tr>';
  $$("[data-run-id]", $("runsTable")).forEach(b => b.onclick = () => openRun(b.dataset.runId));
}

async function openRun(id) {
  $("runDrawer").classList.remove("hidden"); $("runDrawerTitle").textContent = "Run #" + id; $("runDrawerBody").innerHTML = '<div class="empty-state">Loading run…</div>';
  try {
    const d = await api("/api/v1/platform/runs/" + id), run = d.run, ev = d.eval;
    $("runDrawerBody").innerHTML =
      '<div class="run-summary"><div class="summary-box"><span>Agent</span><strong>' + esc(AGENTS[run.agent]?.name || titleCase(run.agent)) +
      '</strong></div><div class="summary-box"><span>Status</span><strong>' + esc(run.status === "ok" ? "Success" : "Error") +
      '</strong></div><div class="summary-box"><span>Duration</span><strong>' + esc(duration(run.duration_ms)) + '</strong></div></div>' +
      '<div class="run-summary" style="margin-top:8px"><div class="summary-box"><span>Request ID</span><strong>' + esc(run.request_id || "—") +
      '</strong></div><div class="summary-box"><span>Correlation</span><strong>' + esc(run.correlation_id || "—") +
      '</strong></div><div class="summary-box"><span>Eval</span><strong>' + esc(ev.score) + '/100</strong></div></div>' +
      '<h3 class="trace-title">Execution trace</h3><div class="trace-stack">' + (run.trace?.length ? run.trace.map(step =>
      '<div class="trace-step ' + (step.status === "error" ? "error" : "") + '"><strong>' + esc(titleCase(step.name)) + '</strong><span>' +
      esc(step.kind) + (step.detail ? " · " + esc(step.detail) : "") + '</span></div>').join("") : '<div class="empty-state">No trace captured. ' + esc(run.error_type || "") + '</div>') +
      '</div><h3 class="trace-title">Evaluation</h3>' + ev.checks.map(check => '<div class="eval-check ' + (!check.passed ? "failed" : "") +
      '"><span>' + (check.passed ? "✓" : "×") + '</span><div><strong>' + esc(check.name) + '</strong><small>' + esc(check.detail) + '</small></div></div>').join("");
  } catch (error) { $("runDrawerBody").innerHTML = '<div class="empty-state">' + esc(error.message) + '</div>'; }
}

async function loadEvaluations() {
  state.metrics = await api("/api/v1/platform/metrics?limit=200");
  $("evalMetrics").innerHTML = state.metrics.length ? state.metrics.map(m =>
    '<div class="eval-card"><strong>' + esc(AGENTS[m.agent]?.name || titleCase(m.agent)) + '</strong><div class="eval-score">' + m.eval_avg_score +
    '</div><div class="progress"><span style="width:' + Math.max(0,Math.min(100,m.eval_avg_score)) + '%"></span></div><small>Pass ' +
    m.eval_pass_rate + '% · Success ' + m.success_rate + '%</small></div>'
  ).join("") : '<div class="empty-state">No evaluation metrics yet.</div>';
}
async function runRegression() {
  $("regressionResult").innerHTML = '<div class="empty-state">Running deterministic regression…</div>';
  try {
    const d = await post("/api/v1/platform/regression/run", {});
    $("regressionResult").innerHTML = '<div style="margin-bottom:8px"><strong>' + d.passed_cases + '/' + d.total_cases +
      ' cases passed</strong></div>' + d.cases.map(x => '<div class="regression-case"><div>' + esc(AGENTS[x.agent]?.name || titleCase(x.agent)) +
      ' · ' + esc(x.id) + '<div class="muted-label">' + esc(x.detail) + '</div></div><strong style="color:' + (x.passed ? '#0f8a4b' : '#b42318') +
      '">' + (x.passed ? "PASS" : "FAIL") + '</strong></div>').join("");
  } catch (error) { $("regressionResult").textContent = error.message; toast(error.message,"error"); }
}

async function loadApprovals() {
  try { state.approvals = await api("/api/v1/platform/approvals?limit=100"); }
  catch (error) { state.approvals=[]; $("approvalCards").innerHTML='<div class="empty-state">'+esc(error.message)+'</div>'; return; }
  updateApprovalCount();
  $("approvalCards").innerHTML = state.approvals.length ? state.approvals.map(x => {
    const execute = x.status === "approved" && ["service_restart","document_delete"].includes(x.tool);
    return '<div class="approval-row"><div class="approval-risk">' + (x.tool === "service_restart" ? "H" : "M") +
      '</div><div class="approval-main"><strong>' + esc(titleCase(x.tool)) + '</strong><span>' + esc(x.reason || x.target) +
      '</span></div><div class="approval-meta"><span>Requester</span><strong>' + esc(x.requested_by || "—") +
      '</strong></div><div class="approval-meta"><span>Status</span><strong>' + esc(titleCase(x.status)) +
      '</strong></div><div class="button-row">' + (x.status === "pending" ? '<button class="secondary-btn small" data-decision="rejected" data-approval="' +
      x.id + '">Reject</button><button class="primary-btn small" data-decision="approved" data-approval="' + x.id + '">Approve</button>' : '') +
      (execute ? '<button class="primary-btn small" data-execute-approval="' + x.id + '">Execute</button>' : '') + '</div></div>';
  }).join("") : '<div class="empty-state">No approval requests.</div>';
  $$("[data-decision]", $("approvalCards")).forEach(b => b.onclick = () => decideApproval(b.dataset.approval,b.dataset.decision));
  $$("[data-execute-approval]", $("approvalCards")).forEach(b => b.onclick = () => executeApproval(b.dataset.executeApproval));
}
function updateApprovalCount() {
  const count = state.approvals.filter(x => x.status === "pending").length;
  $("approvalNavCount").textContent = count;
}
async function updateApprovalCountFromApi() {
  state.approvals = await api("/api/v1/platform/approvals?limit=50").catch(() => []);
  updateApprovalCount();
}
async function decideApproval(id, decision) {
  try { await post("/api/v1/platform/approvals/" + id + "/decision", {decision}); toast("Approval " + decision); await loadApprovals(); }
  catch (error) { toast(error.message,"error"); }
}
async function executeApproval(id) {
  const item = state.approvals.find(x => String(x.id) === String(id)); if (!item) return;
  try {
    if (item.tool === "document_delete") await api("/api/v1/knowledge/documents/" + encodeURIComponent(item.target.replace("document:","")) + "?approval_id=" + id, {method:"DELETE"});
    if (item.tool === "service_restart") await post("/api/v1/ops/services/" + encodeURIComponent(item.target.replace("service:","")) + "/restart?approval_id=" + id, {});
    toast("Approved action executed"); await loadApprovals();
  } catch (error) { toast(error.message,"error"); }
}

async function loadPolicies() {
  state.policies = await api("/api/v1/platform/tools");
  $("policyTable").innerHTML = state.policies.map(x =>
    '<tr><td>' + esc(AGENTS[x.agent]?.name || titleCase(x.agent)) + '</td><td><strong>' + esc(x.name) + '</strong></td><td><span class="status-chip ' +
    (x.risk === "high" ? "error" : x.risk === "medium" ? "warning" : "healthy") + '">' + esc(titleCase(x.risk)) + '</span></td><td>' +
    esc(titleCase(x.mode)) + '</td><td>' + (x.approval_required ? "Required" : "No") + '</td></tr>'
  ).join("");
}

async function loadDataSourcesPage() {
  const [settings, sources] = await Promise.all([getPlatformSettings(true), api("/api/v1/data/sources")]);
  state.settings = settings;
  const rows = sources.map(source => {
    const isDefault = source.name === "default";
    const cfg = isDefault ? {url:settings.database_url,schema:settings.database_schema} : (settings.data_sources?.[source.name] || {});
    return '<div class="resource-row" data-source-name="' + esc(source.name) + '"><div class="resource-icon source">' + icon("database") +
      '</div><div class="resource-main"><strong>' + esc(isDefault ? "Default database" : source.name) + '</strong><p>' +
      esc(maskDatabaseUrl(cfg.url || "Not configured")) + (cfg.schema ? " · schema " + esc(cfg.schema) : "") +
      '</p></div><div class="resource-actions"><span class="status-chip healthy">Available</span><button class="secondary-btn small" data-edit-source="' +
      esc(source.name) + '">Configure</button></div></div>';
  });
  $("dataSourceDirectory").innerHTML = rows.join("") || '<div class="empty-state">No data sources.</div>';
  $$("[data-edit-source]", $("dataSourceDirectory")).forEach(b => b.onclick = e => { e.stopPropagation(); openDataSourceModal(b.dataset.editSource); });
}
function maskDatabaseUrl(url) {
  if (!url) return "";
  return String(url).replace(/(\w+:\/\/[^:/@]+:)[^@]+@/, "$1••••••@");
}
function openDataSourceModal(name = null) {
  state.editingSource = name;
  const s = state.settings || {};
  const isDefault = name === "default";
  const cfg = isDefault ? {url:s.database_url, schema:s.database_schema} : (name ? s.data_sources?.[name] : null);
  $("dataSourceModalTitle").textContent = name ? "Configure data source" : "Add data source";
  $("sourceName").value = isDefault ? "default" : (name || "");
  $("sourceName").disabled = isDefault;
  $("settingDatabaseUrl").value = cfg?.url || "";
  $("settingDatabaseSchema").value = cfg?.schema || cfg?.schema_name || "";
  $("settingSqlMaxRows").value = s.sql_max_rows ?? 200;
  $("settingSqlTimeout").value = s.sql_timeout_seconds ?? 8;
  $("deleteDataSource").classList.toggle("hidden", !name || isDefault);
  openModal("dataSourceModal");
}
async function saveDataSource() {
  const name = $("sourceName").value.trim();
  const url = $("settingDatabaseUrl").value.trim();
  if (!name || !url) return toast("Name and database URL are required","error");
  const schema = $("settingDatabaseSchema").value.trim() || null;
  let body = {sql_max_rows:Number($("settingSqlMaxRows").value)||200, sql_timeout_seconds:Number($("settingSqlTimeout").value)||8};
  if (name === "default") body = {...body, database_url:url, database_schema:schema};
  else {
    const map = {...(state.settings?.data_sources || {})};
    if (state.editingSource && state.editingSource !== name) delete map[state.editingSource];
    map[name] = {url, schema};
    body.data_sources = map;
  }
  if (await saveSettings(body, "Data source saved")) { closeModal("dataSourceModal"); await loadDataSourcesPage(); }
}
async function deleteDataSource() {
  const name = state.editingSource;
  if (!name || name === "default") return;
  const map = {...(state.settings?.data_sources || {})}; delete map[name];
  if (await saveSettings({data_sources:map}, "Data source deleted")) { closeModal("dataSourceModal"); await loadDataSourcesPage(); }
}

async function loadIntegrations() {
  const s = await getPlatformSettings(true);
  state.settings = s;
  const items = [
    {key:"prometheus", name:"Prometheus", desc:s.prometheus_url || "Metrics provider is not connected", configured:!!s.prometheus_url, meta:"Observability"},
    {key:"logs", name:"Log files", desc:s.ops_log_files || "No log sources configured", configured:!!s.ops_log_files, meta:"Evidence"},
    {key:"docker", name:"Docker", desc:s.ops_enable_docker ? "Read-only container inventory enabled" : "Container inventory disabled", configured:!!s.ops_enable_docker, meta:"Infrastructure"},
    {key:"kubernetes", name:"Kubernetes", desc:s.ops_enable_kubernetes ? "Read-only pod inventory enabled" : "Kubernetes inventory disabled", configured:!!s.ops_enable_kubernetes, meta:"Infrastructure"},
    {key:"services", name:"Controlled services", desc:s.ops_allowed_services || "No restart targets allowlisted", configured:!!s.ops_allowed_services, meta:"Governed actions"},
  ];
  $("integrationDirectory").innerHTML = items.map(x =>
    '<div class="resource-row"><div class="resource-icon integration">' + icon("plug") + '</div><div class="resource-main"><strong>' + esc(x.name) +
    '</strong><p>' + esc(x.desc) + '</p></div><div class="resource-actions"><span class="muted-label">' + esc(x.meta) + '</span><span class="status-chip ' +
    (x.configured ? "healthy" : "neutral") + '">' + (x.configured ? "Configured" : "Not configured") +
    '</span><button class="secondary-btn small" data-integration="' + x.key + '">Configure</button></div></div>'
  ).join("");
  $$("[data-integration]", $("integrationDirectory")).forEach(b => b.onclick = () => openIntegrationModal(b.dataset.integration));
}
function openIntegrationModal(key) {
  state.editingIntegration = key;
  const s = state.settings || {};
  const configs = {
    prometheus:["Prometheus","Metrics endpoint used by Ops Agent.",'<label>Prometheus URL<input id="integrationValue" value="'+esc(s.prometheus_url || "")+'" placeholder="http://prometheus:9090"></label>'],
    logs:["Log files","Read-only evidence sources for diagnostics.",'<label>Log paths <span>comma separated</span><input id="integrationValue" value="'+esc(s.ops_log_files || "")+'" placeholder="/var/log/app.log,/var/log/nginx/error.log"></label>'],
    docker:["Docker","Read-only container inventory.",'<label class="toggle-config"><input id="integrationToggle" type="checkbox" '+(s.ops_enable_docker?"checked":"")+'> Enable Docker inventory</label>'],
    kubernetes:["Kubernetes","Read-only pod inventory.",'<label class="toggle-config"><input id="integrationToggle" type="checkbox" '+(s.ops_enable_kubernetes?"checked":"")+'> Enable Kubernetes inventory</label>'],
    services:["Controlled services","Services allowed to enter the Human Approval restart flow.",'<label>Allowed services <span>comma separated</span><input id="integrationValue" value="'+esc(s.ops_allowed_services || "")+'" placeholder="nginx,my-api"></label>'],
  };
  const c = configs[key]; $("integrationTitle").textContent = c[0]; $("integrationSubtitle").textContent = c[1]; $("integrationFields").innerHTML = c[2]; openModal("integrationModal");
}
async function saveIntegration() {
  const key = state.editingIntegration; let body = {};
  if (key === "prometheus") body.prometheus_url = $("integrationValue").value.trim();
  if (key === "logs") body.ops_log_files = $("integrationValue").value.trim();
  if (key === "docker") body.ops_enable_docker = $("integrationToggle").checked;
  if (key === "kubernetes") body.ops_enable_kubernetes = $("integrationToggle").checked;
  if (key === "services") body.ops_allowed_services = $("integrationValue").value.trim();
  if (await saveSettings(body, "Integration saved")) { closeModal("integrationModal"); await loadIntegrations(); }
}

async function loadCredentials() {
  const s = await getPlatformSettings(true);
  state.settings = s;
  const modelConfigured = !!s.llm_model;
  $("credentialDirectory").innerHTML =
    '<div class="resource-row"><div class="resource-icon">' + icon("key") + '</div><div class="resource-main"><strong>OpenAI-compatible</strong><p>' +
    esc(s.llm_base_url || "No base URL") + (s.llm_model ? " · " + esc(s.llm_model) : "") + '</p></div><div class="resource-actions"><span class="status-chip ' +
    (modelConfigured ? "healthy" : "neutral") + '">' + (modelConfigured ? "Connected" : "Not configured") + '</span><button class="secondary-btn small" id="configureProvider">Configure</button></div></div>' +
    '<div class="resource-row"><div class="resource-icon integration">' + icon("shield") + '</div><div class="resource-main"><strong>Platform authentication</strong><p>' +
    (s.auth_enabled ? "Bearer token authentication is enabled" : "Development authentication mode") +
    '</p></div><div class="resource-actions"><span class="status-chip ' + (s.auth_enabled ? "healthy" : "warning") + '">' + (s.auth_enabled ? "Enabled" : "Development") + '</span></div></div>';
  $("configureProvider").onclick = openProviderModal;
}
function openProviderModal() {
  const s = state.settings || {};
  $("settingLlmBaseUrl").value = s.llm_base_url || "";
  $("settingLlmApiKey").value = "";
  $("settingLlmApiKey").placeholder = s.llm_api_key_configured ? "Configured · enter a new key to replace" : "Enter API key";
  $("apiKeyState").textContent = s.llm_api_key_configured ? "Configured" : "Not configured";
  $("settingLlmModel").value = s.llm_model || "";
  $("settingEmbeddingModel").value = s.embedding_model || "";
  $("modelTestResult").textContent = "";
  openModal("providerModal");
}
async function saveProviderSettings(showToast = true) {
  const body = {
    llm_base_url:$("settingLlmBaseUrl").value.trim(),
    llm_model:$("settingLlmModel").value.trim(),
    embedding_model:$("settingEmbeddingModel").value.trim(),
  };
  const key = $("settingLlmApiKey").value.trim(); if (key) body.llm_api_key = key;
  const ok = await saveSettings(body, showToast ? "Model provider saved" : null);
  if (ok) { await getPlatformSettings(true); return true; }
  return false;
}
async function testModel(target) {
  $("modelTestResult").textContent = "Saving and testing…";
  if (!await saveProviderSettings(false)) return;
  try {
    const result = await post("/api/v1/platform/settings/test", {target});
    $("modelTestResult").textContent = "✓ " + result.model + " · " + result.latency_ms + " ms · " + result.detail;
    toast(titleCase(target) + " connection OK");
  } catch (error) { $("modelTestResult").textContent = "Failed · " + error.message; toast(error.message,"error"); }
}

async function loadRuntimeSettings() {
  const s = await getPlatformSettings(true); state.settings = s;
  $("settingLlmTimeout").value = s.llm_timeout_seconds ?? 60;
  $("settingAgentAttempts").value = s.agent_max_attempts ?? 3;
  $("settingKnowledgeTopK").value = s.knowledge_top_k ?? 5;
  $("settingKnowledgeUploadMb").value = Math.max(1,Math.round((s.knowledge_max_upload_bytes || 10485760)/1048576));
  $("settingOpsHttpTimeout").value = s.ops_http_timeout_seconds ?? 5;
  $("settingOpsCommandTimeout").value = s.ops_command_timeout_seconds ?? 5;
  $("settingRateLimit").value = s.rate_limit_per_minute ?? 0;
  $("settingAppEnv").textContent = s.app_env || "—"; $("settingAuthEnabled").textContent = s.auth_enabled ? "Enabled" : "Disabled";
  $("apiToken").value = token(); $("settingsSaveState").textContent = "";
}
async function saveRuntimeSettings() {
  const body = {
    llm_timeout_seconds:Number($("settingLlmTimeout").value)||60,
    agent_max_attempts:Number($("settingAgentAttempts").value)||3,
    knowledge_top_k:Number($("settingKnowledgeTopK").value)||5,
    knowledge_max_upload_bytes:(Number($("settingKnowledgeUploadMb").value)||10)*1048576,
    ops_http_timeout_seconds:Number($("settingOpsHttpTimeout").value)||5,
    ops_command_timeout_seconds:Number($("settingOpsCommandTimeout").value)||5,
    rate_limit_per_minute:Number($("settingRateLimit").value)||0,
  };
  const result = await saveSettings(body,"Runtime settings saved");
  if (result) await loadRuntimeSettings();
}
async function saveSettings(body, successMessage) {
  try {
    const result = await api("/api/v1/platform/settings",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
    state.settings = result.settings;
    if (successMessage) toast(successMessage);
    if ($("settingsSaveState")) $("settingsSaveState").textContent = result.restart_required?.length ? "Saved. Restart required for: " + result.restart_required.join(", ") : "";
    return true;
  } catch (error) { toast(error.message,"error"); return false; }
}

function openModal(id) { $(id).classList.remove("hidden"); }
function closeModal(id) { $(id).classList.add("hidden"); }

function bindGo(root = document) {
  $$("[data-go]", root).forEach(button => button.onclick = () => navigate(button.dataset.go));
}

const COMMANDS = [
  {label:"Home", sub:"Platform overview and attention", page:"home", icon:"home"},
  {label:"Agents", sub:"Browse all agents", page:"agents", icon:"bot"},
  {label:"Data Agent", sub:"Open analytics playground", page:"data", icon:"database"},
  {label:"Knowledge Agent", sub:"Open retrieval playground", page:"knowledge-agent", icon:"book"},
  {label:"Ops Agent", sub:"Open diagnostic workspace", page:"ops", icon:"activity"},
  {label:"Supervisor", sub:"Open investigation canvas", page:"supervisor", icon:"bot"},
  {label:"Knowledge", sub:"Manage documents", page:"knowledge", icon:"book"},
  {label:"Data sources", sub:"Manage database connections", page:"data-sources", icon:"database"},
  {label:"Runs", sub:"Inspect execution history", page:"runs", icon:"activity"},
  {label:"Approvals", sub:"Review governed actions", page:"approvals", icon:"approval"},
  {label:"Integrations", sub:"Connect Ops infrastructure", page:"integrations", icon:"plug"},
  {label:"Credentials", sub:"Manage model provider secrets", page:"credentials", icon:"key"},
  {label:"Policies", sub:"Tool access and risk", page:"policies", icon:"shield"},
  {label:"Settings", sub:"Runtime and access defaults", page:"settings", icon:"settings"},
];
function openCommandPalette() {
  $("commandPalette").classList.remove("hidden"); $("commandInput").value=""; renderCommands(); setTimeout(()=>$("commandInput").focus(),20);
}
function closeCommandPalette() { $("commandPalette").classList.add("hidden"); }
function renderCommands() {
  const q = $("commandInput").value.trim().toLowerCase();
  const items = COMMANDS.filter(x => !q || (x.label+" "+x.sub).toLowerCase().includes(q)).slice(0,10);
  $("commandResults").innerHTML = items.map(x => '<button class="command-result" data-command-page="' + x.page + '">' + icon(x.icon) +
    '<div><strong>' + esc(x.label) + '</strong><span>' + esc(x.sub) + '</span></div><em>Go to</em></button>').join("") || '<div class="empty-state" style="padding:14px">No results.</div>';
  $$("[data-command-page]", $("commandResults")).forEach(b => b.onclick = () => { closeCommandPalette(); navigate(b.dataset.commandPage); });
}

bindGo();
$$(".nav-item[data-page]").forEach(b => b.onclick = () => navigate(b.dataset.page));
$("agentSearch").oninput = renderAgentDirectory;
$("dataSource").onchange = loadSchema;
$("dataAsk").onclick = runDataAsk;
$("runSql").onclick = runSql;
$("downloadReport").onclick = downloadReport;
$("knowledgeAsk").onclick = askKnowledge;
$("refreshOps").onclick = loadOps;
$("opsAsk").onclick = diagnoseOps;
$("refreshLogs").onclick = loadLogs;
$("runProm").onclick = runPrometheus;
$("loadDocker").onclick = () => loadRuntime("docker");
$("loadK8s").onclick = () => loadRuntime("kubernetes");
$("requestRestart").onclick = requestServiceRestart;
$("supervisorAsk").onclick = () => investigate(false);
$("supervisorDemo").onclick = () => investigate(true);
$("runAgentFilter").onchange = loadRuns;
$("runStatusFilter").onchange = renderRuns;
$("runSearch").oninput = renderRuns;
$("refreshRuns").onclick = loadRuns;
$("runRegression").onclick = runRegression;
$("refreshApprovals").onclick = loadApprovals;

$$("[data-agent-tab]").forEach(b => b.onclick = () => {
  if (b.dataset.agentTab === "runs") { $("runAgentFilter").value = b.dataset.agent || ""; navigate("runs"); }
  else if (b.dataset.agentTab === "evaluations") navigate("evaluations");
  else if (b.dataset.agentTab === "settings") navigate("settings");
});

$("openDocForm").onclick = () => openModal("docModal");
$("closeDocForm").onclick = () => closeModal("docModal");
$("cancelDocForm").onclick = () => closeModal("docModal");
$("addDoc").onclick = saveDocument;
$("docFile").onchange = async e => {
  const file=e.target.files[0]; if(!file)return; $("docTitle").value ||= file.name;
  if (/\.(txt|md|csv|json)$/i.test(file.name)) $("docContent").value = await file.text();
};

$("addDataSourceBtn").onclick = () => openDataSourceModal(null);
$("saveDataSource").onclick = saveDataSource;
$("deleteDataSource").onclick = deleteDataSource;
$("saveIntegration").onclick = saveIntegration;
$("saveProviderSettings").onclick = async () => { if (await saveProviderSettings()) { closeModal("providerModal"); await loadCredentials(); } };
$("testChatModel").onclick = () => testModel("chat");
$("testEmbeddingModel").onclick = () => testModel("embedding");
$("saveRuntimeSettings").onclick = saveRuntimeSettings;
$("saveToken").onclick = () => {
  localStorage.setItem("apiToken",$("apiToken").value.trim()); toast("Browser token saved"); loadIdentity(); refreshPage(state.page);
};

$$("[data-close-modal]").forEach(b => b.onclick = () => closeModal(b.dataset.closeModal));
$$(".modal-backdrop").forEach(backdrop => backdrop.onclick = e => { if (e.target === backdrop) closeModal(backdrop.id); });
$("closeRunDrawer").onclick = () => $("runDrawer").classList.add("hidden");
$("runDrawer").onclick = e => { if (e.target === $("runDrawer")) $("runDrawer").classList.add("hidden"); };

$$("[data-settings-section]").forEach(b => b.onclick = () => {
  $$("[data-settings-section]").forEach(x => x.classList.toggle("active",x===b));
  $$("[data-settings-pane]").forEach(x => x.classList.toggle("active",x.dataset.settingsPane===b.dataset.settingsSection));
});

$("commandSearch").onclick = openCommandPalette;
$("commandInput").oninput = renderCommands;
$("commandPalette").onclick = e => { if (e.target === $("commandPalette")) closeCommandPalette(); };
document.addEventListener("keydown", e => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); openCommandPalette(); }
  if (e.key === "Escape") {
    closeCommandPalette(); $("runDrawer").classList.add("hidden");
    $$(".modal-backdrop").forEach(x => x.classList.add("hidden"));
  }
});

(async function boot() {
  await loadIdentity();
  await updateApprovalCountFromApi();
  const page = location.hash.slice(1);
  navigate(PAGES[page] ? page : "home");
})();