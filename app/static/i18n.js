(() => {
  const STORAGE_KEY = "eapLanguage";
  const DEFAULT_LANGUAGE = "zh";

  const zh = {
    "Control Plane": "控制平面",
    "Primary navigation": "主导航",
    "Home": "首页",
    "Build": "构建",
    "Agents": "智能体",
    "New agent": "新建智能体",
    "Agent": "智能体",
    "Managed agent resource.": "平台托管的智能体资源。",
    "Draft": "草稿",
    "Published": "已发布",
    "Archived": "已归档",
    "Overview": "概览",
    "Versions": "版本",
    "Lifecycle": "生命周期",
    "Type": "类型",
    "Published version": "已发布版本",
    "Latest version": "最新版本",
    "Created by": "创建人",
    "Draft, evaluate, and publish immutable agent versions.": "通过草稿、评测和发布管理不可变的智能体版本。",
    "Playground": "调试台",
    "Evaluation": "评测",
    "Agent playground": "智能体调试台",
    "Runs the currently published version": "运行当前已发布版本",
    "Explain what you can help with.": "介绍一下你可以提供哪些帮助。",
    "Published version trace": "已发布版本的执行 Trace",
    "Published versions are immutable. Configuration changes create a new draft.": "已发布版本不可变，更改配置会创建新的草稿版本。",
    "Agent details": "智能体信息",
    "Name and description belong to the Agent resource.": "名称和描述属于智能体资源本身。",
    "Description": "描述",
    "Save details": "保存信息",
    "Tools": "工具",
    "Platform tool registry shared by agents, policies, approvals, and future MCP integrations.": "平台统一工具注册表，供智能体、策略、审批以及后续 MCP 集成共同使用。",
    "Provider": "提供方",
    "Mode": "模式",
    "Risk": "风险",
    "Approval": "审批",
    "Status": "状态",
    "Required": "需要",
    "Enabled": "已启用",
    "Disabled": "已禁用",
    "Browse the platform tool registry": "浏览平台工具注册表",
    "Tool access is versioned with the Agent configuration.": "工具权限随智能体版本一起管理。",
    "Save tools": "保存工具配置",
    "Loading tools…": "正在加载工具……",
    "Changes affect this draft version only.": "修改仅影响当前草稿版本。",
    "Published versions are read-only. Create a draft version to change tools.": "已发布版本只读；如需修改工具，请先创建新的草稿版本。",
    "Approval required": "需要审批",
    "No tools available.": "暂无可用工具。",
    "Tool assignments saved": "工具配置已保存",
    "New draft version": "新草稿版本",
    "Create a new immutable configuration version from the latest version.": "基于最新版本创建新的不可变配置版本。",
    "Instructions": "指令",
    "Model": "模型",
    "Temperature": "温度",
    "Max steps": "最大步骤数",
    "Timeout": "超时",
    "Use platform default": "使用平台默认模型",
    "Create draft version": "创建草稿版本",
    "Open workspace": "打开工作区",
    "Archive": "归档",
    "Create agent": "创建智能体",
    "Create a draft Agent with its first configuration version.": "创建智能体草稿及其首个配置版本。",
    "Research Assistant": "研究助手",
    "What this agent is responsible for.": "描述这个智能体负责什么。",
    "Generic": "通用",
    "You are an enterprise assistant...": "你是一名企业智能助手……",
    "Create draft": "创建草稿",
    "Custom": "自定义",
    "Built-in": "内置",
    "No published version": "暂无已发布版本",
    "Platform default model": "平台默认模型",
    "No versions.": "暂无版本。",
    "No agents yet.": "暂无智能体。",
    "No matching agents.": "没有匹配的智能体。",
    "Agent name is required": "智能体名称必填",
    "Creating draft…": "正在创建草稿……",
    "Agent draft created": "智能体草稿已创建",
    "Agent details saved": "智能体信息已保存",
    "Draft version created": "草稿版本已创建",
    "Agent version published": "智能体版本已发布",
    "Agent archived": "智能体已归档",
    "Running published version…": "正在运行已发布版本……",
    "Agent run completed": "智能体运行完成",
    "Agent version": "智能体版本",
    "Agent ID": "智能体 ID",
    "Created": "创建时间",
    "Knowledge": "知识库",
    "Data sources": "数据源",
    "Operate": "运行",
    "Runs": "运行记录",
    "Evaluations": "评测",
    "Approvals": "审批",
    "Platform": "平台",
    "Integrations": "集成",
    "Credentials": "凭据",
    "Policies": "策略",
    "Settings": "设置",
    "Production": "生产环境",
    "Search agents, runs, resources…": "搜索智能体、运行记录或资源…",
    "Help": "帮助",
    "Notifications": "通知",
    "Account menu": "账户菜单",
    "Sign out": "退出登录",
    "Sign in": "登录",
    "authentication required": "需要登录",
    "Good evening,": "晚上好，",
    "Good morning,": "早上好，",
    "Good afternoon,": "下午好，",
    "Here’s what needs your attention across the platform.": "这里是当前平台最需要你关注的内容。",
    "Runtime health and recent performance": "运行健康状态与近期表现",
    "View all": "查看全部",
    "Activity": "动态",
    "Latest platform events": "最近的平台事件",
    "Runtime": "运行时",
    "Last 200 agent runs": "最近 200 次智能体运行",
    "Explore runs": "查看运行记录",
    "Total runs": "运行总数",
    "Success rate": "成功率",
    "P95 latency": "P95 延迟",
    "Eval average": "平均评测分",
    "Build, inspect, and operate agents from one place.": "在一个工作台中构建、查看并运行所有智能体。",
    "Search agents": "搜索智能体",
    "Data Agent": "数据智能体",
    "Knowledge Agent": "知识智能体",
    "Ops Agent": "运维智能体",
    "Supervisor": "监督智能体",
    "Active": "运行中",
    "Guardrails enabled": "安全护栏已启用",
    "Natural-language analytics with guarded SQL execution.": "通过受控 SQL 执行实现自然语言数据分析。",
    "Role-scoped retrieval with citations and versioned knowledge.": "支持角色权限、来源引用和版本管理的知识检索。",
    "Infrastructure evidence, diagnostics, and governed actions.": "基础设施证据采集、诊断与受控操作。",
    "Cross-agent incident investigation and evidence synthesis.": "跨智能体故障调查与证据综合。",
    "Analytics": "数据分析",
    "Operations": "运维",
    "Ops": "运维",
    "Orchestration": "编排",
    "Playground": "调试台",
    "Configuration": "配置",
    "Knowledge base": "知识库",
    "Diagnose": "诊断",
    "Investigation": "调查",
    "Test the agent against a live data source": "使用实时数据源测试智能体",
    "You": "你",
    "Run the agent to see its answer here.": "运行智能体后，回答会显示在这里。",
    "Run agent": "运行智能体",
    "Download report": "下载报告",
    "Execution": "执行过程",
    "Trace and tool calls": "Trace 与工具调用",
    "No execution yet.": "暂无执行记录。",
    "Database schema": "数据库 Schema",
    "Loading…": "加载中…",
    "SQL console": "SQL 控制台",
    "Run SQL": "执行 SQL",
    "Retrieval playground": "检索调试台",
    "Ask against the current role-scoped knowledge base": "针对当前角色可见的知识库进行提问",
    "Ask a question to inspect retrieval and citations.": "提问后可查看检索结果和引用来源。",
    "Retrieval and answer trace": "检索与回答 Trace",
    "Refresh snapshot": "刷新快照",
    "Diagnostic workspace": "诊断工作台",
    "Reason over runtime evidence without executing unapproved changes": "基于运行证据进行分析，不执行未经审批的变更",
    "Run a diagnosis to inspect evidence and recommendations.": "运行诊断后查看证据和建议。",
    "Run diagnosis": "运行诊断",
    "Evidence": "证据",
    "Runtime sources used by the agent": "智能体使用的运行时数据源",
    "Prometheus": "Prometheus",
    "Run": "运行",
    "No query yet.": "尚未执行查询。",
    "Runtime inventory": "运行环境清单",
    "Docker": "Docker",
    "Kubernetes": "Kubernetes",
    "Not loaded.": "尚未加载。",
    "Logs": "日志",
    "Read logs": "读取日志",
    "Controlled action": "受控操作",
    "Request restart": "申请重启",
    "Execution graph": "执行图",
    "Ready": "就绪",
    "Incident": "故障",
    "User request": "用户请求",
    "Orchestrate": "编排",
    "Policy-aware routing": "策略感知路由",
    "Runtime evidence": "运行时证据",
    "Metrics · Logs": "指标 · 日志",
    "Knowledge evidence": "知识证据",
    "RAG · Citations": "RAG · 引用",
    "Historical evidence": "历史证据",
    "SQL · Analytics": "SQL · 分析",
    "Conclusion": "结论",
    "Evidence synthesis": "证据综合",
    "Compose and run an incident query": "编写并执行故障调查问题",
    "Historical source": "历史数据源",
    "Question": "问题",
    "Start investigation": "开始调查",
    "Offline demo": "离线 Demo",
    "No investigation yet.": "尚未开始调查。",
    "Execution trace": "执行 Trace",
    "Agent delegation and synthesis steps": "智能体委派与综合步骤",
    "No trace yet.": "暂无 Trace。",
    "Manage versioned documents and role-scoped access.": "管理带版本控制和角色权限的知识文档。",
    "Add document": "添加文档",
    "Document": "文档",
    "Version": "版本",
    "Chunks": "分块",
    "Access": "权限",
    "Tags": "标签",
    "Connections available to Data Agent and Supervisor.": "供数据智能体和监督智能体使用的数据连接。",
    "Add source": "添加数据源",
    "Inspect execution, latency, trace, and evaluation results.": "查看执行状态、延迟、Trace 与评测结果。",
    "All agents": "全部智能体",
    "All statuses": "全部状态",
    "Success": "成功",
    "Error": "失败",
    "Refresh": "刷新",
    "Status": "状态",
    "Agent": "智能体",
    "Duration": "耗时",
    "Request": "请求",
    "Correlation": "关联 ID",
    "Started": "开始时间",
    "Deterministic quality checks across agent execution paths.": "对智能体执行路径进行确定性质量评测。",
    "Run regression": "运行回归",
    "Back to agent": "返回智能体",
    "Regression suite": "回归测试集",
    "Fixed samples with no external LLM dependency": "固定样本，不依赖外部 LLM",
    "Run regression to validate the core paths.": "运行回归测试以验证核心执行路径。",
    "Review sensitive tool actions before execution.": "在执行前审核敏感工具操作。",
    "Connect observability and infrastructure services used by Ops Agent.": "连接运维智能体使用的可观测与基础设施服务。",
    "Manage model provider connections and secrets.": "管理模型服务连接与密钥。",
    "Tool access, risk classification, and approval requirements.": "管理工具权限、风险等级与审批要求。",
    "Tool": "工具",
    "Risk": "风险",
    "Mode": "模式",
    "Approval": "审批",
    "Runtime defaults, security, and local console preferences.": "管理运行时默认值、安全策略与本地控制台偏好。",
    "Save changes": "保存更改",
    "Security & access": "安全与访问",
    "Console": "控制台",
    "Agent execution": "智能体执行",
    "Defaults used across agent runs.": "所有智能体运行使用的默认参数。",
    "LLM timeout": "LLM 超时",
    "seconds": "秒",
    "Maximum attempts": "最大尝试次数",
    "per agent run": "每次智能体运行",
    "Retrieval and upload limits.": "检索与上传限制。",
    "Retrieval top K": "检索 Top K",
    "documents": "文档",
    "Maximum upload": "最大上传大小",
    "Network and command execution timeouts.": "网络与命令执行超时。",
    "HTTP timeout": "HTTP 超时",
    "Command timeout": "命令超时",
    "Server": "服务端",
    "Environment and API protection.": "环境与 API 安全保护。",
    "Environment": "环境",
    "Authentication": "身份认证",
    "Current user": "当前用户",
    "Role": "角色",
    "API rate limit": "API 限流",
    "Requests per minute for the current process.": "当前进程每分钟允许的请求数。",
    "Rate limit": "限流",
    "requires restart": "需要重启",
    "Browser authentication": "浏览器认证",
    "The bearer token is stored only in this browser.": "Bearer Token 仅保存在当前浏览器。",
    "Bearer token": "Bearer Token",
    "Save browser token": "保存浏览器 Token",
    "Add knowledge document": "添加知识文档",
    "Upload a file or paste content.": "上传文件或直接粘贴内容。",
    "Document ID": "文档 ID",
    "Only for updates": "仅更新时填写",
    "Title": "标题",
    "Allowed roles": "允许角色",
    "File": "文件",
    "Content": "内容",
    "Cancel": "取消",
    "Save document": "保存文档",
    "Configure model provider": "配置模型服务",
    "OpenAI-compatible Chat Completions and Embeddings.": "兼容 OpenAI Chat Completions 与 Embeddings。",
    "API base URL": "API Base URL",
    "API key": "API Key",
    "Not configured": "未配置",
    "Configured": "已配置",
    "Connected": "已连接",
    "Chat model": "对话模型",
    "Embedding model": "Embedding 模型",
    "Test chat": "测试对话模型",
    "Test embedding": "测试 Embedding",
    "Save connection": "保存连接",
    "Configure data source": "配置数据源",
    "Connections are used for read-only agent analytics.": "数据连接用于智能体只读分析。",
    "Name": "名称",
    "default is reserved": "default 为保留名称",
    "Database URL": "数据库 URL",
    "Schema": "Schema",
    "Max result rows": "最大返回行数",
    "SQL timeout": "SQL 超时",
    "Delete source": "删除数据源",
    "Save source": "保存数据源",
    "Configure integration": "配置集成",
    "Ops Agent integration.": "运维智能体集成。",
    "Save integration": "保存集成",
    "RUN INSPECTOR": "运行检查器",
    "Search or jump to…": "搜索或跳转…",
    "Go to": "前往",
    "No results.": "没有搜索结果。",
    "Request ID": "请求 ID",
    "Correlation ID": "关联 ID",
    "No trace captured.": "未捕获 Trace。",
    "Add data source": "添加数据源",
    "Metrics endpoint used by Ops Agent.": "运维智能体使用的指标服务地址。",
    "Read-only evidence sources for diagnostics.": "用于诊断的只读证据源。",
    "Read-only container inventory.": "只读容器清单。",
    "Read-only pod inventory.": "只读 Pod 清单。",
    "Services allowed to enter the Human Approval restart flow.": "允许进入人工审批重启流程的服务。",
    "Enable Docker inventory": "启用 Docker 清单",
    "Enable Kubernetes inventory": "启用 Kubernetes 清单",
    "Log paths": "日志路径",
    "comma separated": "使用英文逗号分隔",
    "Allowed services": "允许的服务",
    "Prometheus URL": "Prometheus URL",
    "Platform overview and attention": "平台概览与待处理事项",
    "Browse all agents": "浏览全部智能体",
    "Open analytics playground": "打开数据分析调试台",
    "Open retrieval playground": "打开知识检索调试台",
    "Open diagnostic workspace": "打开运维诊断工作台",
    "Open investigation canvas": "打开调查画布",
    "Manage documents": "管理知识文档",
    "Manage database connections": "管理数据库连接",
    "Inspect execution history": "查看执行历史",
    "Review governed actions": "审核受控操作",
    "Connect Ops infrastructure": "连接运维基础设施",
    "Manage model provider secrets": "管理模型服务密钥",
    "Tool access and risk": "工具权限与风险",
    "Runtime and access defaults": "运行时与访问默认配置",
    "Healthy": "健康",
    "Degraded": "异常",
    "No data": "暂无数据",
    "No runtime metrics": "暂无运行指标",
    "Platform is healthy": "平台运行正常",
    "No pending approvals or recent agent failures need attention.": "当前没有待审批事项或近期智能体失败需要处理。",
    "Sensitive actions require human review before execution.": "敏感操作必须经过人工审批后才能执行。",
    "No chat model is configured": "尚未配置对话模型",
    "Connect a model provider before running AI-powered agents.": "运行 AI 智能体前请先连接模型服务。",
    "No activity yet.": "暂无动态。",
    "No tables found.": "未找到数据表。",
    "No data sources.": "暂无数据源。",
    "Name and database URL are required": "名称和数据库 URL 必填",
    "No base URL": "未配置 Base URL",
    "Disabled": "已禁用",
    "Execution error": "执行错误",
    "unknown": "未知",
    "PASS": "通过",
    "FAIL": "失败",
    "Chat connection OK": "对话模型连接正常",
    "Embedding connection OK": "Embedding 连接正常",
    "No trace available.": "暂无 Trace。",
    "Analyzing schema and generating a guarded query…": "正在分析 Schema 并生成受保护的查询…",
    "Data Agent completed": "数据智能体执行完成",
    "Query completed": "查询执行完成",
    "Retrieving role-scoped knowledge…": "正在检索当前角色可访问的知识…",
    "No knowledge documents.": "暂无知识文档。",
    "Deletion approval created": "删除审批已创建",
    "Saving…": "保存中…",
    "Document saved": "文档已保存",
    "Collecting evidence and diagnosing…": "正在收集证据并进行诊断…",
    "Loading…": "加载中…",
    "No log files configured.": "未配置日志文件。",
    "Querying…": "查询中…",
    "Enter a service name": "请输入服务名称",
    "Restart approval created": "重启审批已创建",
    "Building isolated demo evidence…": "正在构建隔离 Demo 证据…",
    "Supervisor is delegating the investigation…": "监督智能体正在委派调查任务…",
    "No conclusion returned.": "未返回调查结论。",
    "Completed": "已完成",
    "Running": "运行中",
    "Failed": "失败",
    "Investigation completed": "调查完成",
    "No matching runs.": "没有匹配的运行记录。",
    "Loading run…": "正在加载运行记录…",
    "Eval": "评测",
    "Evaluation": "评测",
    "No trace captured.": "未捕获 Trace。",
    "Running deterministic regression…": "正在运行确定性回归测试…",
    "No evaluation metrics yet.": "暂无评测指标。",
    "No approval requests.": "暂无审批请求。",
    "Requester": "申请人",
    "Approve": "批准",
    "Reject": "拒绝",
    "Execute": "执行",
    "Approved action executed": "已批准操作执行完成",
    "Required": "需要",
    "Pending": "待审批",
    "Approved": "已批准",
    "Rejected": "已拒绝",
    "Consumed": "已执行",
    "Low": "低",
    "Medium": "中",
    "High": "高",
    "Read": "只读",
    "Write": "写入",
    "Service Restart": "服务重启",
    "Document Delete": "文档删除",
    "No": "否",
    "Available": "可用",
    "Default database": "默认数据库",
    "Not configured": "未配置",
    "Metrics provider is not connected": "尚未连接指标服务",
    "Observability": "可观测",
    "Log files": "日志文件",
    "No log sources configured": "未配置日志源",
    "Read-only container inventory enabled": "已启用容器只读清单",
    "Container inventory disabled": "容器清单已禁用",
    "Infrastructure": "基础设施",
    "Read-only pod inventory enabled": "已启用 Pod 只读清单",
    "Kubernetes inventory disabled": "Kubernetes 清单已禁用",
    "Controlled services": "受控服务",
    "No restart targets allowlisted": "未配置允许重启的目标",
    "Governed actions": "受控操作",
    "Configure": "配置",
    "OpenAI-compatible": "OpenAI 兼容服务",
    "Platform authentication": "平台认证",
    "Bearer token authentication is enabled": "Bearer Token 认证已启用",
    "Development authentication mode": "开发环境认证模式",
    "Enabled": "已启用",
    "Development": "开发环境",
    "Saving and testing…": "正在保存并测试…",
    "connection OK": "连接正常",
    "Runtime settings saved": "运行时设置已保存",
    "Browser token saved": "浏览器 Token 已保存",
    "Model provider saved": "模型服务已保存",
    "Data source saved": "数据源已保存",
    "Data source deleted": "数据源已删除",
    "Integration saved": "集成已保存",
    "Saved. Restart required for:": "已保存，需要重启后生效：",
    "Create and run an incident query": "创建并运行故障调查问题",
    "Edit this page": "编辑此页",

    "Sign in · Enterprise Agent": "登录 · Enterprise Agent",
    "ENTERPRISE AI OPERATIONS": "企业级 AI 运营",
    "Build, operate, and govern agents from one control plane.": "在一个控制平面中构建、运行并治理企业智能体。",
    "Manage agent execution, knowledge, data access, observability, approvals, and runtime policies in one place.": "统一管理智能体执行、知识、数据访问、可观测、审批与运行时策略。",
    "Agent operations": "智能体运行",
    "Inspect runs, trace execution, and evaluate quality.": "查看运行记录、追踪执行链路并评估质量。",
    "Governed actions": "受控操作",
    "Human approval for sensitive tools and infrastructure changes.": "敏感工具和基础设施变更必须经过人工审批。",
    "Connected resources": "连接资源",
    "Models, databases, knowledge, and observability integrations.": "统一连接模型、数据库、知识库与可观测服务。",
    "Enterprise Agent Platform · Demo Environment": "Enterprise Agent Platform · 演示环境",
    "Access the Enterprise Agent control plane.": "登录 Enterprise Agent 控制平面。",
    "Username": "用户名",
    "Password": "密码",
    "Demo credentials": "演示账号",
    "Protected by session-based authentication": "受 Session 身份认证保护",
    "Signing in…": "正在登录…",
    "Sign in failed": "登录失败",
    "Invalid username or password": "用户名或密码错误",
    "Please sign in": "请先登录",
    "Invalid Bearer Token": "无效 Bearer Token",
    "Insufficient permissions": "权限不足",

    "Paste bearer token": "粘贴 Bearer Token",
    "systemd service": "systemd 服务",
    "Search documents": "搜索文档",
    "Run ID, request ID, correlation ID": "Run ID、Request ID、Correlation ID",
    "https://api.openai.com/v1": "https://api.openai.com/v1",
    "Enter API key": "输入 API Key",
    "Leave blank to keep current key": "留空表示保留当前 Key",
    "Configured · enter a new key to replace": "已配置 · 输入新 Key 可替换",
    "gpt-5.6": "gpt-5.6",
    "text-embedding-3-small": "text-embedding-3-small",
    "postgresql+psycopg://user:pass@host/db": "postgresql+psycopg://user:pass@host/db",
    "analytics": "analytics",
    "http://prometheus:9090": "http://prometheus:9090",
    "/var/log/app.log,/var/log/nginx/error.log": "/var/log/app.log,/var/log/nginx/error.log",
    "nginx,my-api": "nginx,my-api",
    "operations, radar": "operations, radar"
  };

  const defaultValues = {
    "统计每类数据的数量，并指出数量最多的类别。": "Count the records in each category and identify the category with the largest count.",
    "雷达资料验收时需要检查什么？": "What should be checked when accepting radar data?",
    "当前服务器资源状态是否存在明显异常？结合日志和监控数据分析，并说明还需要检查哪些信息。": "Are there any obvious anomalies in the current server resources? Analyze the logs and monitoring data, and explain what else should be checked.",
    "为什么最近导入任务失败？请结合当前运维状态、知识库手册和历史数据给出排查结论。": "Why have recent import jobs failed? Combine current operations status, the knowledge runbook, and historical data to provide an investigation conclusion."
  };

  const reverseExact = Object.fromEntries(Object.entries(zh).map(([en, cn]) => [cn, en]));
  const reverseValues = Object.fromEntries(Object.entries(defaultValues).map(([cn, en]) => [en, cn]));

  function language() {
    return localStorage.getItem(STORAGE_KEY) || DEFAULT_LANGUAGE;
  }

  function patterns(text, lang) {
    if (lang === "zh") {
      let m;
      if ((m = text.match(/^(\d+) approval requests? (?:are|is) waiting$/))) return m[1] + " 个审批请求待处理";
      if ((m = text.match(/^(\d+) agents?$/))) return m[1] + " 个智能体";
      if ((m = text.match(/^(\d+) \/ (\d+) tools$/))) return m[1] + " / " + m[2] + " 个工具";
      if ((m = text.match(/^(.+) has a failed recent run$/))) return agentName(m[1], "zh") + " 最近一次运行失败";
      if ((m = text.match(/^Back to (.+)$/))) return "返回 " + agentName(m[1], "zh");
      if ((m = text.match(/^Execution history for (.+)\.$/))) return agentName(m[1], "zh") + " 的运行记录。";
      if ((m = text.match(/^Evaluation results for (.+)\.$/))) return agentName(m[1], "zh") + " 的评测结果。";
      if ((m = text.match(/^(.+) completed run #(\d+)$/))) return agentName(m[1], "zh") + " 已完成运行 #" + m[2];
      if ((m = text.match(/^(.+) failed run #(\d+)$/))) return agentName(m[1], "zh") + " 运行 #" + m[2] + " 失败";
      if ((m = text.match(/^Run #(\d+)$/))) return "运行 #" + m[1];
      if ((m = text.match(/^(\d+(?:\.\d+)?)% success$/))) return "成功率 " + m[1] + "%";
      if ((m = text.match(/^P95 (.+)$/))) return "P95 " + m[1];
      if ((m = text.match(/^(\d+) runs?$/))) return m[1] + " 次运行";
      if ((m = text.match(/^v(\d+) published$/i))) return "已发布 v" + m[1];
      if ((m = text.match(/^v(\d+) latest$/i))) return "最新 v" + m[1];
      if ((m = text.match(/^(\d+) cores$/))) return m[1] + " 核";
      if ((m = text.match(/^(.+) free$/))) return "剩余 " + m[1];
      if ((m = text.match(/^Approval (.+) (pending|approved|rejected|consumed)$/i))) {
        const status = {pending:"待审批",approved:"已批准",rejected:"已拒绝",consumed:"已执行"}[m[2].toLowerCase()] || m[2];
        return "审批 " + m[1] + " · " + status;
      }
      if ((m = text.match(/^(.+) approval (pending|approved|rejected|consumed)$/i))) {
        const tool = zh[m[1]] || m[1];
        const status = {pending:"待审批",approved:"已批准",rejected:"已拒绝",consumed:"已执行"}[m[2].toLowerCase()] || m[2];
        return tool + "审批 · " + status;
      }
      if ((m = text.match(/^Failed · (.+)$/))) return "失败 · " + m[1];
      if ((m = text.match(/^No trace captured\.\s*(.*)$/))) return "未捕获 Trace。" + (m[1] ? " " + m[1] : "");
      if ((m = text.match(/^Approval (approved|rejected)$/i))) return "审批已" + (m[1].toLowerCase() === "approved" ? "批准" : "拒绝");
      if ((m = text.match(/^Saved #(\d+)$/))) return "已保存 #" + m[1];
      if ((m = text.match(/^(\d+)\/(\d+) cases passed$/))) return m[1] + "/" + m[2] + " 个用例通过";
      if ((m = text.match(/^Pass (.+)% · Success (.+)%$/))) return "评测通过 " + m[1] + "% · 运行成功 " + m[2] + "%";
      if ((m = text.match(/^score (.+)$/))) return "相关度 " + m[1];
      if ((m = text.match(/^schema (.+)$/i))) return "Schema " + m[1];
      if ((m = text.match(/^Configured · (.+)$/))) return "已配置 · " + m[1];
      if ((m = text.match(/^Saved\. Restart required for: (.+)$/))) return "已保存，需要重启后生效：" + m[1];
      if ((m = text.match(/^✓ (.+) · (\d+) ms · (.+)$/))) return "✓ " + m[1] + " · " + m[2] + " ms · " + m[3];
    }
    return text;
  }

  function agentName(name, lang) {
    if (lang !== "zh") return name;
    return ({
      "Data Agent": "数据智能体",
      "Knowledge Agent": "知识智能体",
      "Ops Agent": "运维智能体",
      "Supervisor": "监督智能体"
    })[name] || name;
  }

  function t(source, lang = language()) {
    if (source == null) return source;
    const text = String(source);
    if (lang === "zh") return zh[text] || patterns(text, lang);
    return reverseExact[text] || text;
  }

  function tExternal(value, lang = language()) {
    if (value == null) return value;
    const text = String(value);
    if (lang === "en") return reverseExact[text] || reverseValues[text] || text;
    return zh[text] || patterns(text, lang);
  }

  function translateTextNode(node, lang) {
    const parent = node.parentElement;
    if (!parent || ["SCRIPT", "STYLE", "SVG", "CODE", "PRE"].includes(parent.tagName)) return;
    const raw = node.nodeValue;
    const trimmed = raw.trim();
    if (!trimmed) return;

    if (node.__eapI18nSource == null) {
      const source = reverseExact[trimmed] || trimmed;
      node.__eapI18nSource = source;
      node.__eapI18nPrefix = raw.slice(0, raw.indexOf(trimmed));
      node.__eapI18nSuffix = raw.slice(raw.indexOf(trimmed) + trimmed.length);
    }

    const translated = t(node.__eapI18nSource, lang);
    const next = node.__eapI18nPrefix + translated + node.__eapI18nSuffix;
    if (node.nodeValue !== next) node.nodeValue = next;
  }

  function translateAttribute(el, attr, lang) {
    if (el.hasAttribute("data-language-switch") && attr === "aria-label") return;
    const camelAttr = attr.replace(/-([a-z])/g, (_, ch) => ch.toUpperCase());
    const suffix = camelAttr[0].toUpperCase() + camelAttr.slice(1);
    const sourceKey = "eapI18n" + suffix;
    const lastKey = "eapI18nLast" + suffix;
    const current = el.getAttribute(attr);
    if (!current) return;

    if (!el.dataset[sourceKey] || (el.dataset[lastKey] && current !== el.dataset[lastKey])) {
      el.dataset[sourceKey] = reverseExact[current] || current;
    }

    const next = t(el.dataset[sourceKey], lang);
    if (current !== next) el.setAttribute(attr, next);
    el.dataset[lastKey] = next;
  }

  function translateValue(el, lang) {
    if (!(el instanceof HTMLTextAreaElement)) return;
    if (!el.dataset.eapI18nSourceValue) {
      const current = el.value;
      const source = reverseValues[current] || (defaultValues[current] ? current : null);
      if (!source) return;
      el.dataset.eapI18nSourceValue = source;
      el.dataset.eapI18nLastValue = current;
    }

    const last = el.dataset.eapI18nLastValue;
    if (last && el.value !== last) return;

    const source = el.dataset.eapI18nSourceValue;
    const next = lang === "zh" ? source : (defaultValues[source] || source);
    el.value = next;
    el.dataset.eapI18nLastValue = next;
  }

  function apply(root = document) {
    const lang = language();
    document.documentElement.lang = lang === "zh" ? "zh-CN" : "en-US";
    document.title = location.pathname.startsWith("/login") ? t("Sign in · Enterprise Agent", lang) : "Enterprise Agent";

    const walker = document.createTreeWalker(
      root === document ? document.body : root,
      NodeFilter.SHOW_TEXT
    );
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(node => translateTextNode(node, lang));

    const scope = root === document ? document : root;
    if (scope.querySelectorAll) {
      scope.querySelectorAll("[placeholder]").forEach(el => translateAttribute(el, "placeholder", lang));
      scope.querySelectorAll("[title]").forEach(el => translateAttribute(el, "title", lang));
      scope.querySelectorAll("[aria-label]").forEach(el => translateAttribute(el, "aria-label", lang));
      scope.querySelectorAll("textarea").forEach(el => translateValue(el, lang));
    }

    document.dispatchEvent(new CustomEvent("eap-language-applied", {detail:{language:lang}}));
  }

  function setLanguage(lang) {
    const next = lang === "en" ? "en" : "zh";
    localStorage.setItem(STORAGE_KEY, next);
    apply(document);
    document.dispatchEvent(new CustomEvent("eap-language-changed", {detail:{language:next}}));
  }

  function toggle() {
    setLanguage(language() === "zh" ? "en" : "zh");
  }

  function updateSwitches() {
    const lang = language();
    document.querySelectorAll("[data-language-switch]").forEach(el => {
      el.dataset.language = lang;
      el.setAttribute("aria-label", lang === "zh" ? "切换到英文" : "Switch to Chinese");
      el.querySelectorAll("[data-lang]").forEach(part => {
        part.classList.toggle("active", part.dataset.lang === lang);
      });
    });
  }

  document.addEventListener("eap-language-applied", updateSwitches);

  const observer = new MutationObserver(mutations => {
    const lang = language();
    for (const mutation of mutations) {
      if (mutation.type === "characterData") {
        translateTextNode(mutation.target, lang);
      }
      if (mutation.type === "attributes") {
        translateAttribute(mutation.target, mutation.attributeName, lang);
      }
      mutation.addedNodes.forEach(node => {
        if (node.nodeType === Node.TEXT_NODE) {
          translateTextNode(node, lang);
        } else if (node.nodeType === Node.ELEMENT_NODE) {
          apply(node);
        }
      });
    }
  });

  window.EAPI18n = {
    language,
    setLanguage,
    toggle,
    t,
    external: tExternal,
    apply,
    updateSwitches
  };

  document.addEventListener("DOMContentLoaded", () => {
    apply(document);
    document.body.classList.remove("i18n-pending");
    document.querySelectorAll("[data-language-switch]").forEach(el => {
      el.addEventListener("click", event => {
        event.preventDefault();
        event.stopPropagation();
        toggle();
      });
    });
    observer.observe(document.body, {
      subtree:true,
      childList:true,
      characterData:true,
      attributes:true,
      attributeFilter:["placeholder","title","aria-label"]
    });
  });
})();