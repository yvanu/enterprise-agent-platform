const $ = id => document.getElementById(id);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const uiText = text => window.EAPI18n ? EAPI18n.t(text) : text;

const state = {
  page: "home",
  runs: [],
  metrics: [],
  approvals: [],
  policies: [],
  tools: [],
  mcpServers: [],
  openapiServices: [],
  settings: null,
  identity: null,
  lastReport: "",
  editingSource: null,
  editingIntegration: null,
  agents: [],
  selectedAgentId: sessionStorage.getItem("eapSelectedAgentId") || null,
  selectedAgent: null,
  contextAgentId: null,
  contextAgentName: null,
  contextAgentKey: null,
};

const PAGES = {
  home: "Home",
  agents: "Agents",
  "agent-detail": "Agent",
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
  tools: "Tools",
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
const toolLabel = value => value === "mcp" ? "MCP" : value === "openapi" ? "OpenAPI" : value === "builtin" ? "Built-in" : titleCase(value);
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
    const error = new Error(detail);
    error.status = response.status;
    if (response.status === 401) {
      location.replace("/login");
    }
    throw error;
  }
  return data;
}
const post = (url, body) => api(url, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
const put = (url, body) => api(url, {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
const patch = (url, body) => api(url, {method:"PATCH", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});

function parseRoute() {
  const raw = location.hash.slice(1) || "home";
  const [pagePart, query = ""] = raw.split("?");
  const page = PAGES[pagePart] ? pagePart : "home";
  return {page, params:new URLSearchParams(query)};
}

function routeHash(page) {
  const params = new URLSearchParams();
  if (page === "agent-detail" && state.selectedAgentId) {
    params.set("agent", state.selectedAgentId);
  }
  if (["runs","evaluations"].includes(page) && state.contextAgentId) {
    params.set("from", "agent-detail");
    params.set("agent", state.contextAgentId);
    if (state.contextAgentKey) params.set("key", state.contextAgentKey);
  }
  const query = params.toString();
  return "#" + page + (query ? "?" + query : "");
}

function setRouteContext(page, options = {}) {
  if (page === "agent-detail") {
    if (options.agentId) state.selectedAgentId = options.agentId;
    if (state.selectedAgentId) sessionStorage.setItem("eapSelectedAgentId", state.selectedAgentId);
    state.contextAgentId = null;
    state.contextAgentName = null;
    state.contextAgentKey = null;
    return;
  }

  if (["runs","evaluations"].includes(page)) {
    const fromAgent = options.fromAgent || null;
    if (fromAgent) {
      state.contextAgentId = fromAgent.id;
      state.contextAgentName = fromAgent.name;
      state.contextAgentKey = fromAgent.key;
    } else if (!options.preserveContext) {
      state.contextAgentId = null;
      state.contextAgentName = null;
      state.contextAgentKey = null;
    }
  } else if (!options.preserveContext) {
    state.contextAgentId = null;
    state.contextAgentName = null;
    state.contextAgentKey = null;
  }
}

function setNav(page) {
  const navPage = ["agent-detail","data","knowledge-agent","ops","supervisor"].includes(page) ? "agents" : page;
  $$(".nav-item").forEach(el => el.classList.toggle("active", el.dataset.page === navPage));
}

function navigate(page, options = {}) {
  if (!PAGES[page]) return;
  setRouteContext(page, options);
  state.page = page;
  setNav(page);
  $$(".page").forEach(el => el.classList.toggle("active", el.dataset.pagePanel === page));

  if (options.history !== "none") {
    const method = options.history === "replace" ? "replaceState" : "pushState";
    history[method]({
      page,
      agentId: state.selectedAgentId,
      contextAgentId: state.contextAgentId,
      contextAgentName: state.contextAgentName,
      contextAgentKey: state.contextAgentKey,
    }, "", routeHash(page));
  }

  refreshPage(page);
  window.scrollTo({top:0, behavior: options.history === "none" ? "auto" : "smooth"});
}

function navigateFromLocation() {
  const route = parseRoute();
  if (route.page === "agent-detail") {
    state.selectedAgentId = route.params.get("agent") || state.selectedAgentId;
  }

  if (["runs","evaluations"].includes(route.page) && route.params.get("from") === "agent-detail") {
    state.contextAgentId = route.params.get("agent");
    state.contextAgentKey = route.params.get("key");
    state.contextAgentName = null;
    navigate(route.page, {history:"none", preserveContext:true});
    return;
  }

  navigate(route.page, {
    history:"none",
    agentId: route.page === "agent-detail" ? state.selectedAgentId : undefined,
  });
}

async function refreshPage(page) {
  try {
    if (page === "home") await loadHome();
    if (page === "agents") await loadAgentDirectory();
    if (page === "agent-detail") await loadManagedAgentDetail();
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
    if (page === "tools") await loadTools();
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
    const hour = new Date().getHours();
    $("homeGreeting").textContent = hour < 12 ? "Good morning," : hour < 18 ? "Good afternoon," : "Good evening,";
    $("homeUser").textContent = me.username;
    const initials = me.username.slice(0, 2).toUpperCase();
    $$(".avatar").forEach(el => el.textContent = initials);
    if ($("identityName")) $("identityName").textContent = me.username;
    if ($("identityRole")) $("identityRole").textContent = me.role;
    $("accountMenuName").textContent = me.username;
    $("accountMenuRole").textContent = me.role;
    return true;
  } catch (error) {
    $("sidebarUser").textContent = "Sign in";
    $("sidebarRole").textContent = "authentication required";
    return false;
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
  const [metrics, runs, approvals, settings, agents] = await Promise.all([
    api("/api/v1/platform/metrics?limit=200").catch(() => []),
    api("/api/v1/platform/runs?limit=200").catch(() => []),
    api("/api/v1/platform/approvals?limit=50").catch(() => []),
    getPlatformSettings(true).catch(() => null),
    api("/api/v1/agents").catch(() => []),
  ]);
  state.metrics = metrics;
  state.runs = runs;
  state.approvals = approvals;
  state.agents = agents;
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

async function getContextAgent() {
  if (!state.contextAgentId) return null;
  let agent = state.agents.find(item => item.id === state.contextAgentId);
  if (!agent && state.selectedAgent?.id === state.contextAgentId) agent = state.selectedAgent;
  if (!agent) {
    try {
      agent = await api("/api/v1/agents/" + encodeURIComponent(state.contextAgentId));
      if (!state.agents.some(item => item.id === agent.id)) state.agents.push(agent);
    } catch {
      return null;
    }
  }
  state.contextAgentName = agent.name;
  state.contextAgentKey = agent.type === "generic" ? agent.slug : agent.type;
  return agent;
}

async function updateContextReturn(page) {
  const button = page === "runs" ? $("runsAgentReturn") : $("evaluationsAgentReturn");
  const description = page === "runs" ? $("runsPageDescription") : $("evaluationsPageDescription");
  if (!button || !description) return null;

  if (!state.contextAgentId) {
    button.classList.add("hidden");
    description.textContent = page === "runs"
      ? "Inspect execution, latency, trace, and evaluation results."
      : "Deterministic quality checks across agent execution paths.";
    return null;
  }

  const agent = await getContextAgent();
  if (!agent) {
    button.classList.add("hidden");
    return null;
  }

  button.classList.remove("hidden");
  button.querySelector("span").textContent = "Back to " + agent.name;
  description.textContent = page === "runs"
    ? "Execution history for " + agent.name + "."
    : "Evaluation results for " + agent.name + ".";
  return agent;
}

function returnToContextAgent() {
  if (!state.contextAgentId) return navigate("agents");
  navigate("agent-detail", {agentId:state.contextAgentId});
}

function agentTypeMeta(type) {
  const preset = AGENTS[type];
  if (preset) return preset;
  return {page:"agent-detail", name:"Agent", kind:"Custom", desc:"Custom managed agent.", icon:"bot", cls:"supervisor"};
}

function agentResourceStatus(agent) {
  if (agent.status === "archived") return {label:"Archived", cls:"neutral"};
  if (agent.status === "draft") return {label:"Draft", cls:"warning"};
  const metric = metricFor(agent.type === "generic" ? agent.slug : agent.type);
  const last = latestRun(agent.type === "generic" ? agent.slug : agent.type);
  if (last?.status === "error") return {label:"Degraded", cls:"warning"};
  if (!metric) return {label:"Published", cls:"healthy"};
  return {label:"Healthy", cls:"healthy"};
}

function agentResourceRow(agent) {
  const meta = agentTypeMeta(agent.type);
  const metricKey = agent.type === "generic" ? agent.slug : agent.type;
  const metric = metricFor(metricKey);
  const last = latestRun(metricKey);
  const status = agentResourceStatus(agent);
  const versionMeta = '<span>' + (agent.published_version ? "v" + agent.published_version + " published" : "No published version") + '</span>' +
    '<span>v' + (agent.latest_version || 1) + ' latest</span>' +
    (agent.built_in ? '<span>Built-in</span>' : '<span>Custom</span>');
  const runtimeMeta = metric
    ? '<span>' + metric.success_rate + '% success</span><span>P95 ' + esc(duration(metric.p95_duration_ms)) + '</span>'
    : versionMeta;
  return '<div class="resource-row" data-managed-agent-id="' + esc(agent.id) + '">' +
    '<div class="resource-icon ' + meta.cls + '">' + icon(meta.icon) + '</div>' +
    '<div class="resource-main"><strong>' + esc(agent.name) + '</strong><p>' + esc(agent.description || meta.desc) + '</p></div>' +
    '<div class="resource-actions"><div class="resource-meta">' + runtimeMeta + '</div><span class="status-chip ' + status.cls + '">' + status.label + '</span>' +
    (last ? '<button class="icon-btn" data-open-run="' + last.id + '" title="Open latest run">' + icon("chevron") + '</button>' : '') + '</div></div>';
}

function bindManagedAgentRows(root) {
  $$("[data-managed-agent-id]", root).forEach(row => row.onclick = e => {
    if (e.target.closest("[data-open-run]")) return;
    state.selectedAgentId = row.dataset.managedAgentId;
    navigate("agent-detail");
  });
  $$("[data-open-run]", root).forEach(button => button.onclick = e => {
    e.stopPropagation();
    openRun(button.dataset.openRun);
  });
}

function renderHomeAgents() {
  const agents = state.agents.filter(x => x.status !== "archived").slice(0, 5);
  $("homeAgents").innerHTML = agents.length ? agents.map(agentResourceRow).join("") : '<div class="empty-state">No agents yet.</div>';
  bindManagedAgentRows($("homeAgents"));
}

async function loadAgentDirectory() {
  const [agents, metrics, runs] = await Promise.all([
    api("/api/v1/agents"),
    api("/api/v1/platform/metrics?limit=200").catch(() => []),
    api("/api/v1/platform/runs?limit=200").catch(() => []),
  ]);
  state.agents = agents; state.metrics = metrics; state.runs = runs;
  renderAgentDirectory();
}

function renderAgentDirectory() {
  const q = ($("agentSearch").value || "").trim().toLowerCase();
  const agents = state.agents.filter(agent => {
    const meta = agentTypeMeta(agent.type);
    return !q || [agent.name,agent.slug,agent.description,agent.type,meta.kind,uiText(agent.name),uiText(agent.description)].some(v => String(v || "").toLowerCase().includes(q));
  });
  $("agentCount").textContent = agents.length + " agent" + (agents.length === 1 ? "" : "s");
  $("agentDirectory").innerHTML = agents.length ? agents.map(agentResourceRow).join("") : '<div class="empty-state">No matching agents.</div>';
  bindManagedAgentRows($("agentDirectory"));
}

async function loadManagedAgentDetail() {
  if (!state.selectedAgentId) {
    navigate("agents");
    return;
  }
  const agent = await api("/api/v1/agents/" + encodeURIComponent(state.selectedAgentId));
  state.selectedAgent = agent;
  const meta = agentTypeMeta(agent.type);
  $("managedAgentName").textContent = agent.name;
  $("managedAgentDescription").textContent = agent.description || meta.desc;
  $("managedAgentStatus").textContent = titleCase(agent.status);
  $("managedAgentStatus").className = "status-chip " + (agent.status === "published" ? "healthy" : agent.status === "draft" ? "warning" : "neutral");
  $("managedAgentIcon").className = "agent-icon " + meta.cls;
  $("managedAgentIcon").innerHTML = icon(meta.icon);
  $("managedAgentType").textContent = titleCase(agent.type);
  $("managedAgentPublishedVersion").textContent = agent.published_version ? "v" + agent.published_version : "—";
  $("managedAgentLatestVersion").textContent = agent.latest_version ? "v" + agent.latest_version : "—";
  $("managedAgentCreatedBy").textContent = agent.created_by;
  $("managedAgentMessageName").textContent = agent.name;

  const builtInPage = AGENTS[agent.type]?.page;
  $("openBuiltinWorkspace").classList.toggle("hidden", !builtInPage);
  $("openBuiltinWorkspace").dataset.page = builtInPage || "";
  $("archiveManagedAgent").classList.toggle("hidden", agent.built_in || agent.status === "archived" || state.identity?.role !== "admin");

  $("managedAgentEditName").value = agent.name;
  $("managedAgentEditDescription").value = agent.description || "";
  const latest = agent.versions[0];
  if (latest) {
    $("managedAgentInstructions").value = latest.instructions || "";
    $("managedAgentModel").value = latest.model || "";
    $("managedAgentTemperature").value = latest.temperature ?? 0.2;
    $("managedAgentMaxSteps").value = latest.max_steps ?? 8;
    $("managedAgentTimeout").value = latest.timeout_seconds ?? 60;
  }
  renderManagedAgentVersions(agent);
  await loadManagedAgentTools(agent);
  await loadManagedMcpApprovals(agent);
}

async function loadManagedAgentTools(agent) {
  const latest = agent.versions[0];
  if (!latest) {
    $("managedAgentTools").innerHTML = '<div class="empty-state">No versions.</div>';
    $("saveManagedAgentTools").classList.add("hidden");
    return;
  }

  try {
    const [tools, assignments] = await Promise.all([
      api("/api/v1/tools?enabled_only=true"),
      api("/api/v1/agents/" + encodeURIComponent(agent.id) + "/versions/" + latest.version + "/tools"),
    ]);
    state.tools = tools;
    const assigned = new Set(assignments.map(item => item.tool.id));
    const editable = latest.status === "draft" && agent.status !== "archived" && ["operator","admin"].includes(state.identity?.role);

    $("managedAgentToolVersion").textContent = "v" + latest.version;
    $("managedAgentToolState").textContent = titleCase(latest.status);
    $("managedAgentToolCount").textContent = assigned.size + " / " + tools.length + " tools";
    $("managedAgentToolHint").textContent = editable
      ? "Changes affect this draft version only."
      : "Published versions are read-only. Create a draft version to change tools.";
    $("saveManagedAgentTools").classList.toggle("hidden", !editable);

    $("managedAgentTools").innerHTML = tools.length ? tools.map(tool => {
      const riskClass = tool.risk === "high" ? "error" : tool.risk === "medium" ? "warning" : "healthy";
      return '<label class="tool-assignment-row"><input type="checkbox" data-tool-assignment="' + esc(tool.id) + '" ' +
        (assigned.has(tool.id) ? "checked " : "") + (editable ? "" : "disabled ") + 'aria-label="Assign ' + esc(tool.display_name) + '">' +
        '<div class="tool-assignment-main"><strong>' + esc(tool.display_name) + '</strong><p>' + esc(tool.key) + ' · ' + esc(tool.description) + '</p></div>' +
        '<div class="tool-assignment-meta"><span class="status-chip neutral">' + esc(titleCase(tool.mode)) + '</span>' +
        '<span class="status-chip ' + riskClass + '">' + esc(titleCase(tool.risk)) + '</span>' +
        (tool.approval_required ? '<span class="status-chip warning">Approval required</span>' : '') + '</div></label>';
    }).join("") : '<div class="empty-state">No tools available.</div>';
  } catch (error) {
    $("managedAgentTools").innerHTML = '<div class="empty-state">' + esc(error.message) + '</div>';
    $("managedAgentToolHint").textContent = "";
    $("saveManagedAgentTools").classList.add("hidden");
  }
}

async function loadManagedMcpApprovals(agent) {
  const root = $("managedMcpApprovals");
  root.classList.add("hidden");
  root.innerHTML = "";
  if (agent.type !== "generic" || !agent.published_version ||
      !["operator","admin"].includes(state.identity?.role)) return;
  const assigned = await api("/api/v1/agents/" + encodeURIComponent(agent.id) +
    "/versions/" + agent.published_version + "/tools");
  if (!assigned.some(x => x.enabled && x.tool.enabled && ["mcp", "openapi"].includes(x.tool.provider))) return;
  root.classList.remove("hidden");
  const approvals = await api("/api/v1/platform/approvals?limit=100");
  const related = approvals.filter(x => x.agent_id === agent.id &&
    x.agent_version === agent.published_version && x.arguments !== null &&
    (x.status === "pending" || x.status === "approved"));
  root.innerHTML = '<span class="muted-label">Run the agent to generate a parameter-specific proposal.</span>' +
    related.map(x => '<div class="mcp-proposal"><strong>' + esc(x.agent + "." + x.tool) +
      ' · #' + x.id + ' (' + esc(x.status) + ')</strong><pre>' +
      esc(JSON.stringify(x.arguments, null, 2)) + '</pre>' +
      (x.status === "approved" ? '<button class="primary-btn small" data-resume-existing="' + x.id +
      '">Resume approved operation</button>' : '<span class="muted-label">Awaiting reviewer decision</span>') +
      '</div>').join("");
  $$("[data-resume-existing]", root).forEach(button => button.onclick = async () => {
    button.disabled = true;
    try {
      const result = await post("/api/v1/agents/" + encodeURIComponent(agent.id) +
        "/approvals/" + button.dataset.resumeExisting + "/resume",
        {input:$("managedAgentInput").value});
      $("managedAgentAnswer").textContent = result.answer;
      renderTrace("managedAgentTrace", result.trace || []);
      toast("Approved remote tool operation completed");
      await loadManagedMcpApprovals(agent);
    } catch (error) { toast(error.message, "error"); button.disabled = false; }
  });
}

function renderPendingMcpApprovals(agent, proposals, originalInput) {
  const root = $("managedMcpApprovals");
  if (!proposals.length) return;
  root.classList.remove("hidden");
  root.innerHTML = '<strong>Pending remote tool operation — not executed</strong>' +
    '<span class="muted-label">Review exact arguments, request approval, then resume once approved.</span>' +
    proposals.map((tool, index) =>
      '<div class="mcp-proposal"><strong>' + esc(tool.namespace + "." + tool.tool) +
      '</strong><pre>' + esc(JSON.stringify(tool.arguments, null, 2)) + '</pre>' +
      '<div class="mcp-approval-row"><button class="secondary-btn small" data-propose-index="' + index +
      '">Request approval</button><button class="primary-btn small hidden" data-resume-index="' + index +
      '">Resume approved operation</button><span data-approval-state="' + index + '"></span></div></div>'
    ).join("");
  $$("[data-propose-index]", root).forEach(button => button.onclick = async () => {
    const index = Number(button.dataset.proposeIndex);
    const tool = proposals[index];
    button.disabled = true;
    try {
      const approval = await post("/api/v1/platform/approvals", {
        agent:tool.namespace, tool:tool.tool, target:"tool:" + tool.tool_id,
        arguments:tool.arguments, agent_id:agent.id, agent_version:agent.published_version,
        reason:"Remote tool operation proposed by " + agent.name,
      });
      root.querySelector('[data-approval-state="' + index + '"]').textContent =
        "Approval #" + approval.id + " pending. Review under Approvals.";
      const resume = root.querySelector('[data-resume-index="' + index + '"]');
      resume.dataset.approvalId = approval.id;
      resume.classList.remove("hidden");
      button.classList.add("hidden");
    } catch (error) { toast(error.message, "error"); button.disabled = false; }
  });
  $$("[data-resume-index]", root).forEach(button => button.onclick = async () => {
    button.disabled = true;
    try {
      const result = await post("/api/v1/agents/" + encodeURIComponent(agent.id) +
        "/approvals/" + button.dataset.approvalId + "/resume", {input:originalInput});
      $("managedAgentAnswer").textContent = result.answer;
      renderTrace("managedAgentTrace", result.trace || []);
      toast("Approved remote tool operation completed");
      root.classList.add("hidden");
    } catch (error) { toast(error.message, "error"); button.disabled = false; }
  });
}

async function saveManagedAgentTools() {
  const agent = state.selectedAgent;
  const latest = agent?.versions?.[0];
  if (!agent || !latest || latest.status !== "draft") return;
  const toolIds = $$('[data-tool-assignment]:checked', $("managedAgentTools")).map(item => item.dataset.toolAssignment);
  $("saveManagedAgentTools").disabled = true;
  try {
    await put("/api/v1/agents/" + encodeURIComponent(agent.id) + "/versions/" + latest.version + "/tools", {tool_ids:toolIds});
    toast("Tool assignments saved");
    await loadManagedAgentTools(agent);
  } catch (error) {
    toast(error.message, "error");
  } finally {
    $("saveManagedAgentTools").disabled = false;
  }
}

function renderManagedAgentVersions(agent) {
  $("managedAgentVersions").innerHTML = agent.versions.map(version => {
    const statusClass = version.status === "published" ? "healthy" : version.status === "draft" ? "warning" : "neutral";
    const publish = version.status === "draft" && agent.status !== "archived"
      ? '<button class="secondary-btn small" data-publish-agent-version="' + version.version + '">Publish</button>'
      : "";
    return '<div class="resource-row"><div class="resource-icon">' + icon("activity") + '</div><div class="resource-main"><strong>v' +
      version.version + '</strong><p>' + esc(version.model || "Platform default model") + ' · ' + esc(version.created_by) + ' · ' +
      esc(new Date(version.created_at).toLocaleString()) + '</p></div><div class="resource-actions"><span class="status-chip ' + statusClass + '">' +
      esc(titleCase(version.status)) + '</span>' + publish + '</div></div>';
  }).join("") || '<div class="empty-state">No versions.</div>';

  $$("[data-publish-agent-version]", $("managedAgentVersions")).forEach(button => {
    button.onclick = async () => {
      button.disabled = true;
      try {
        await post("/api/v1/agents/" + encodeURIComponent(agent.id) + "/publish", {version:Number(button.dataset.publishAgentVersion)});
        toast("Agent version published");
        await loadManagedAgentDetail();
        await loadAgentDirectory();
      } catch (error) {
        toast(error.message, "error");
      } finally {
        button.disabled = false;
      }
    };
  });
}

async function createAgent() {
  const name = $("newAgentName").value.trim();
  if (!name) return toast("Agent name is required", "error");
  $("createAgentButton").disabled = true;
  $("newAgentStatus").textContent = "Creating draft…";
  try {
    const agent = await post("/api/v1/agents", {
      name,
      description:$("newAgentDescription").value.trim(),
      type:$("newAgentType").value,
      version:{
        instructions:$("newAgentInstructions").value,
        model:$("newAgentModel").value.trim(),
        temperature:Number($("newAgentTemperature").value) || 0,
        timeout_seconds:Number($("newAgentTimeout").value) || 60,
      },
    });
    state.selectedAgentId = agent.id;
    closeModal("agentModal");
    $("newAgentStatus").textContent = "";
    toast("Agent draft created");
    navigate("agent-detail");
  } catch (error) {
    $("newAgentStatus").textContent = error.message;
    toast(error.message, "error");
  } finally {
    $("createAgentButton").disabled = false;
  }
}

function resetAgentModal() {
  $("newAgentName").value = "";
  $("newAgentDescription").value = "";
  $("newAgentType").value = "generic";
  $("newAgentModel").value = "";
  $("newAgentInstructions").value = "";
  $("newAgentTemperature").value = "0.2";
  $("newAgentTimeout").value = "60";
  $("newAgentStatus").textContent = "";
}

async function saveManagedAgentDetails() {
  const agent = state.selectedAgent;
  if (!agent) return;
  try {
    await patch("/api/v1/agents/" + encodeURIComponent(agent.id), {
      name:$("managedAgentEditName").value.trim(),
      description:$("managedAgentEditDescription").value.trim(),
    });
    toast("Agent details saved");
    await loadManagedAgentDetail();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function createManagedAgentVersion() {
  const agent = state.selectedAgent;
  if (!agent) return;
  $("createManagedAgentVersion").disabled = true;
  try {
    await post("/api/v1/agents/" + encodeURIComponent(agent.id) + "/versions", {
      instructions:$("managedAgentInstructions").value,
      model:$("managedAgentModel").value.trim(),
      temperature:Number($("managedAgentTemperature").value) || 0,
      max_steps:Number($("managedAgentMaxSteps").value) || 8,
      timeout_seconds:Number($("managedAgentTimeout").value) || 60,
    });
    toast("Draft version created");
    await loadManagedAgentDetail();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    $("createManagedAgentVersion").disabled = false;
  }
}

async function runManagedAgent() {
  const agent = state.selectedAgent;
  if (!agent) return;
  $("runManagedAgent").disabled = true;
  $("managedAgentAnswer").textContent = "Running published version…";
  try {
    const input = $("managedAgentInput").value;
    const result = await post("/api/v1/agents/" + encodeURIComponent(agent.id) + "/run", {
      input, source:"default",
    });
    $("managedAgentAnswer").textContent = result.answer;
    renderTrace("managedAgentTrace", result.trace || []);
    if (result.pending_tools?.length) {
      renderPendingMcpApprovals(agent, result.pending_tools, input);
      toast("Remote tool action needs parameter-scoped approval");
    } else {
      $("managedMcpApprovals").classList.add("hidden");
      toast("Agent run completed");
    }
  } catch (error) {
    $("managedAgentAnswer").textContent = error.message;
    toast(error.message, "error");
  } finally {
    $("runManagedAgent").disabled = false;
  }
}

async function archiveManagedAgent() {
  const agent = state.selectedAgent;
  if (!agent) return;
  try {
    await post("/api/v1/agents/" + encodeURIComponent(agent.id) + "/archive", {});
    toast("Agent archived");
    navigate("agents");
  } catch (error) {
    toast(error.message, "error");
  }
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
  const contextAgent = await updateContextReturn("runs");
  if (contextAgent) {
    const key = state.contextAgentKey;
    let option = [...$("runAgentFilter").options].find(item => item.value === key);
    if (!option) {
      option = new Option(contextAgent.name, key);
      $("runAgentFilter").add(option);
    }
    $("runAgentFilter").value = key;
  }

  const agent = $("runAgentFilter").value;
  const url = "/api/v1/platform/runs?limit=200" + (agent ? "&agent=" + encodeURIComponent(agent) : "");
  state.runs = await api(url);
  renderRuns();
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
      '<div class="run-summary" style="margin-top:8px"><div class="summary-box"><span>Agent version</span><strong>' +
      esc(run.agent_version ? "v" + run.agent_version : "—") + '</strong></div><div class="summary-box"><span>Agent ID</span><strong>' +
      esc(run.agent_id || "—") + '</strong></div><div class="summary-box"><span>Eval</span><strong>' + esc(ev.score) + '/100</strong></div></div>' +
      '<div class="run-summary" style="margin-top:8px"><div class="summary-box"><span>Request ID</span><strong>' + esc(run.request_id || "—") +
      '</strong></div><div class="summary-box"><span>Correlation</span><strong>' + esc(run.correlation_id || "—") +
      '</strong></div><div class="summary-box"><span>Created</span><strong>' + esc(run.created_at || "—") + '</strong></div></div>' +
      '<h3 class="trace-title">Execution trace</h3><div class="trace-stack">' + (run.trace?.length ? run.trace.map(step =>
      '<div class="trace-step ' + (step.status === "error" ? "error" : "") + '"><strong>' + esc(titleCase(step.name)) + '</strong><span>' +
      esc(step.kind) + (step.detail ? " · " + esc(step.detail) : "") + '</span></div>').join("") : '<div class="empty-state">No trace captured. ' + esc(run.error_type || "") + '</div>') +
      '</div><h3 class="trace-title">Evaluation</h3>' + ev.checks.map(check => '<div class="eval-check ' + (!check.passed ? "failed" : "") +
      '"><span>' + (check.passed ? "✓" : "×") + '</span><div><strong>' + esc(check.name) + '</strong><small>' + esc(check.detail) + '</small></div></div>').join("");
  } catch (error) { $("runDrawerBody").innerHTML = '<div class="empty-state">' + esc(error.message) + '</div>'; }
}

async function loadEvaluations() {
  await updateContextReturn("evaluations");
  state.metrics = await api("/api/v1/platform/metrics?limit=200");
  const metrics = state.contextAgentKey
    ? state.metrics.filter(item => item.agent === state.contextAgentKey)
    : state.metrics;
  $("evalMetrics").innerHTML = metrics.length ? metrics.map(m =>
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
    return '<div class="approval-row"><div class="approval-risk">' + ((x.agent.startsWith("mcp.") || x.agent.startsWith("openapi.")) || x.tool === "service_restart" ? "H" : "M") +
      '</div><div class="approval-main"><strong>' + esc(titleCase(x.tool)) + '</strong><span>' + esc(x.reason || x.target) +
      '</span>' + (x.arguments === null ? '' :
      '<div class="muted-label">Agent ' + esc(shortId(x.agent_id)) + ' · v' + esc(x.agent_version) + ' · ' + esc(x.target) +
      '</div><pre class="approval-arguments">' + esc(JSON.stringify(x.arguments, null, 2)) + '</pre>') + '</div><div class="approval-meta"><span>Requester</span><strong>' + esc(x.requested_by || "—") +
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

async function loadTools() {
  if (!state.identity) await loadIdentity();
  state.tools = await api("/api/v1/tools");
  await Promise.all([loadMcpServers(), loadOpenapiServices()]);
  $("toolCatalogCount").textContent = state.tools.length + (state.tools.length === 1 ? " tool" : " tools");
  $("toolsTable").innerHTML = state.tools.map(tool => {
    const riskClass = tool.risk === "high" ? "error" : tool.risk === "medium" ? "warning" : "healthy";
    return '<tr><td><strong>' + esc(tool.display_name || tool.name) + '</strong><div class="muted-label">' + esc(tool.key) + '</div></td><td>' +
      esc(toolLabel(tool.provider)) + '</td><td>' + esc(toolLabel(tool.type)) + '</td><td>' + esc(titleCase(tool.mode)) +
      '</td><td><span class="status-chip ' + riskClass + '">' + esc(titleCase(tool.risk)) + '</span></td><td>' +
      (tool.approval_required ? "Required" : "No") + '</td><td><span class="status-chip ' + (tool.enabled ? "healthy" : "neutral") + '">' +
      (tool.enabled ? "Enabled" : "Disabled") + '</span></td></tr>';
  }).join("") || '<tr><td colspan="7"><div class="empty-state">No tools available.</div></td></tr>';
  renderToolConnections();
}

function renderToolConnections() {
  const root = $("connectionDirectory");
  const admin = state.identity?.role === "admin";
  const servers = state.mcpServers || [];
  const services = state.openapiServices || [];
  const connectionTotal = servers.length + services.length;
  const externalToolTotal = state.tools.filter(tool => tool.provider === "mcp" || tool.provider === "openapi").length;

  $("openToolConnection").classList.toggle("hidden", !admin);
  $("connectionCount").textContent = connectionTotal + (connectionTotal === 1 ? " connection" : " connections");
  $("externalToolCount").textContent = externalToolTotal + (externalToolTotal === 1 ? " external tool" : " external tools");

  const rows = [
    ...servers.map(item =>
      '<div class="connection-row"><div class="resource-icon integration">' + icon("plug") +
      '</div><div class="connection-main"><span class="connection-kind">MCP server</span><strong>' + esc(item.name) +
      '</strong><p>' + esc(item.url) + '</p></div><div class="connection-meta"><span>Discovery</span><strong>On demand</strong></div><div class="resource-actions">' +
      '<span class="status-chip ' + (item.status === "connected" ? "healthy" : "neutral") + '">' + esc(titleCase(item.status)) + '</span>' +
      (admin ? '<button class="secondary-btn small" data-mcp-discover="' + esc(item.id) + '">Discover tools</button>' : '') + '</div></div>'
    ),
    ...services.map(item =>
      '<div class="connection-row"><div class="resource-icon">' + icon("tool") +
      '</div><div class="connection-main"><span class="connection-kind">OpenAPI service</span><strong>' + esc(item.name) +
      '</strong><p>' + esc(item.base_url) + '</p></div><div class="connection-meta"><span>Imported operations</span><strong>' + Number(item.operation_count || 0) +
      '</strong></div><div class="resource-actions"><span class="status-chip healthy">Imported</span></div></div>'
    ),
  ];

  root.innerHTML = rows.join("") || '<div class="connection-empty"><div class="connection-empty-icon">' + icon("plug") +
    '</div><div><strong>No external connections</strong><p>Built-in tools are ready. Add MCP or OpenAPI only when agents need external capabilities.</p></div>' +
    (admin ? '<button class="secondary-btn small" data-open-tool-connection>Add connection</button>' : '') + '</div>';

  $$("[data-open-tool-connection]", root).forEach(button => button.onclick = openToolConnectionModal);
  $$("[data-mcp-discover]", root).forEach(button => button.onclick = async () => {
    button.disabled = true;
    try {
      const tools = await post("/api/v1/mcp/servers/" + encodeURIComponent(button.dataset.mcpDiscover) + "/discover", {});
      toast(tools.length + " MCP tools imported");
      await loadTools();
    } catch (error) { toast(error.message, "error"); }
    finally { button.disabled = false; }
  });
}

async function loadMcpServers() {
  try {
    state.mcpServers = await api("/api/v1/mcp/servers");
  } catch (error) {
    state.mcpServers = [];
    toast(error.message, "error");
  }
  renderToolConnections();
}

function setToolConnectionKind(kind = "mcp") {
  $$("[data-connection-kind]").forEach(button => button.classList.toggle("active", button.dataset.connectionKind === kind));
  $$("[data-connection-pane]").forEach(pane => pane.classList.toggle("hidden", pane.dataset.connectionPane !== kind));
  $("addMcpServer").classList.toggle("hidden", kind !== "mcp");
  $("addOpenapiService").classList.toggle("hidden", kind !== "openapi");
}

function openToolConnectionModal() {
  setToolConnectionKind("mcp");
  openModal("toolConnectionModal");
}

async function addMcpServer() {
  const name = $("mcpServerName").value.trim();
  const url = $("mcpServerUrl").value.trim();
  if (!name || !url) return toast("Server name and URL required", "error");
  $("addMcpServer").disabled = true;
  try {
    await post("/api/v1/mcp/servers", {name, url});
    $("mcpServerName").value = "";
    $("mcpServerUrl").value = "";
    closeModal("toolConnectionModal");
    toast("MCP server registered");
    await loadMcpServers();
  } catch (error) { toast(error.message, "error"); }
  finally { $("addMcpServer").disabled = false; }
}

async function loadOpenapiServices() {
  try {
    state.openapiServices = await api("/api/v1/openapi/services");
  } catch (error) {
    state.openapiServices = [];
    toast(error.message, "error");
  }
  renderToolConnections();
}

async function addOpenapiService() {
  const name = $("openapiServiceName").value.trim();
  const base_url = $("openapiBaseUrl").value.trim();
  const file = $("openapiFile").files[0];
  if (!name || !base_url || !file) return toast("Name, approved URL and JSON file are required", "error");
  if (file.size > 262144) return toast("OpenAPI JSON must be 256KB or smaller", "error");
  const button = $("addOpenapiService");
  button.disabled = true;
  try {
    const document = JSON.parse(await file.text());
    const service = await post("/api/v1/openapi/services", {name, base_url, document});
    $("openapiServiceName").value = "";
    $("openapiBaseUrl").value = "";
    $("openapiFile").value = "";
    closeModal("toolConnectionModal");
    toast(service.operation_count + " OpenAPI tools imported");
    await loadTools();
  } catch (error) { toast(error.message, "error"); }
  finally { button.disabled = false; }
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
  {label:"Tools", sub:"Browse the platform tool registry", page:"tools", icon:"tool"},
  {label:"Policies", sub:"Tool access and risk", page:"policies", icon:"shield"},
  {label:"Settings", sub:"Runtime and access defaults", page:"settings", icon:"settings"},
];
function openCommandPalette() {
  $("commandPalette").classList.remove("hidden"); $("commandInput").value=""; renderCommands(); setTimeout(()=>$("commandInput").focus(),20);
}
function closeCommandPalette() { $("commandPalette").classList.add("hidden"); }
function renderCommands() {
  const q = $("commandInput").value.trim().toLowerCase();
  const items = COMMANDS.filter(x => !q || (x.label+" "+x.sub+" "+uiText(x.label)+" "+uiText(x.sub)).toLowerCase().includes(q)).slice(0,10);
  $("commandResults").innerHTML = items.map(x => '<button class="command-result" data-command-page="' + x.page + '">' + icon(x.icon) +
    '<div><strong>' + esc(x.label) + '</strong><span>' + esc(x.sub) + '</span></div><em>Go to</em></button>').join("") || '<div class="empty-state" style="padding:14px">No results.</div>';
  $$("[data-command-page]", $("commandResults")).forEach(b => b.onclick = () => { closeCommandPalette(); navigate(b.dataset.commandPage); });
}

bindGo();
$$(".nav-item[data-page]").forEach(b => b.onclick = () => navigate(b.dataset.page));
$("agentSearch").oninput = renderAgentDirectory;
$("newAgentButton").onclick = () => { resetAgentModal(); openModal("agentModal"); };
$("createAgentButton").onclick = createAgent;
$("saveManagedAgentDetails").onclick = saveManagedAgentDetails;
$("saveManagedAgentTools").onclick = saveManagedAgentTools;
$("refreshTools").onclick = loadTools;
$("openToolConnection").onclick = openToolConnectionModal;
$$("[data-connection-kind]").forEach(button => button.onclick = () => setToolConnectionKind(button.dataset.connectionKind));
$("addMcpServer").onclick = addMcpServer;
$("addOpenapiService").onclick = addOpenapiService;
$("createManagedAgentVersion").onclick = createManagedAgentVersion;
$("runManagedAgent").onclick = runManagedAgent;
$("archiveManagedAgent").onclick = archiveManagedAgent;
$("openBuiltinWorkspace").onclick = () => {
  const page = $("openBuiltinWorkspace").dataset.page;
  if (page) navigate(page);
};
$$("[data-managed-agent-tab]").forEach(button => button.onclick = () => {
  $$("[data-managed-agent-tab]").forEach(item => item.classList.toggle("active", item === button));
  $$("[data-managed-agent-pane]").forEach(pane => pane.classList.toggle("active", pane.dataset.managedAgentPane === button.dataset.managedAgentTab));
});
$$("[data-managed-agent-go]").forEach(button => button.onclick = () => {
  const agent = state.selectedAgent;
  if (!agent) return;
  const fromAgent = {
    id:agent.id,
    name:agent.name,
    key:agent.type === "generic" ? agent.slug : agent.type,
  };
  navigate(button.dataset.managedAgentGo, {fromAgent});
});
$("runsAgentReturn").onclick = returnToContextAgent;
$("evaluationsAgentReturn").onclick = returnToContextAgent;
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
$("accountButton").onclick = event => {
  event.stopPropagation();
  $("accountMenu").classList.toggle("hidden");
};
$("logoutButton").onclick = async () => {
  try { await fetch("/api/v1/auth/logout", {method:"POST", credentials:"same-origin"}); }
  finally {
    localStorage.removeItem("apiToken");
    location.replace("/login");
  }
};
document.addEventListener("click", event => {
  if (!event.target.closest("#accountMenu") && !event.target.closest("#accountButton")) $("accountMenu").classList.add("hidden");
});

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

window.addEventListener("popstate", navigateFromLocation);

(async function boot() {
  if (!await loadIdentity()) return;
  document.body.classList.remove("auth-pending");
  await updateApprovalCountFromApi();

  const route = parseRoute();
  if (route.page === "agent-detail") {
    state.selectedAgentId = route.params.get("agent") || state.selectedAgentId;
  }
  if (["runs","evaluations"].includes(route.page) && route.params.get("from") === "agent-detail") {
    state.contextAgentId = route.params.get("agent");
    state.contextAgentKey = route.params.get("key");
  }

  navigate(route.page, {
    history:"replace",
    agentId:state.selectedAgentId,
    preserveContext:!!state.contextAgentId,
  });
})();