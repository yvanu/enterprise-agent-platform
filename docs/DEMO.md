# 演示指南

## 最快 Demo：不依赖外部 LLM

安装项目后执行：

```bash
python scripts/demo_incident.py
```

预期流程：

1. Ops Agent 读取模拟的导入服务 Timeout 日志。
2. Knowledge Agent 检索导入服务运维手册。
3. Data Agent 查询历史 `import_jobs`。
4. Supervisor 汇总三类证据。
5. 最终回答明确说明“没有执行任何修复动作”。

需要 JSON 输出：

```bash
python scripts/demo_incident.py --json
```

## Web Demo

本地：

```bash
cp .env.example .env
docker compose up --build
```

打开：

```text
http://127.0.0.1:8000/
```

线上 Demo：

```text
https://agent.majhoon.site
```

默认演示账号：

```text
demo / demo
```

Web Console 按资源化 Enterprise SaaS 方式组织：

```text
Home

BUILD
  Agents
  Knowledge
  Data sources

OPERATE
  Runs
  Evaluations
  Approvals

PLATFORM
  Integrations
  Credentials
  Policies

Settings
```

当 `AUTH_ENABLED=false` 时，应用以 `development/admin` 身份运行。

共享演示环境建议同时配置 API Token 和 Console Login：

```text
AUTH_ENABLED=true
AUTH_TOKENS={"user-token":"alice:user","operator-token":"operator:operator","approver-token":"reviewer:approver","admin-token":"admin:admin"}

CONSOLE_USERNAME=demo
CONSOLE_PASSWORD=demo
CONSOLE_ROLE=admin
```

Web Console 使用 HttpOnly Session Cookie，API Client 仍可以使用 Bearer Token。

## 5 分钟面试演示路线

### 1. 登录和 Home

打开 Web Console，用 `demo / demo` 登录。

展示：

- Attention Items
- Agent Health
- Recent Activity
- Runtime Metrics

可以说明：

> 首页优先回答“现在什么需要处理”，而不是传统后台那样先放四个 KPI Card。

### 2. Agents

打开 Agents Directory。

说明 Agent 是一等资源，不是写死在 Sidebar 的四个 Tab。

进入 Data Agent，展示统一 Detail Shell：

```text
Agent
├── Playground
├── Runs
├── Evaluations
└── Configuration
```

向 Data Agent 提问：

> 统计每类数据的数量，并指出数量最多的类别。

展示：

- Schema-aware SQL Generation
- SQL Guard
- Query Result
- Chart
- Markdown Report
- Execution Trace

### 3. Knowledge

进入 Knowledge，添加一个带 Tags 与 Allowed Roles 的文档。

然后打开 Knowledge Agent 提问，展示：

- Role-scoped Retrieval
- Citations
- Retrieval Trace

如果需要进一步演示 RBAC，可以用 user/operator/approver Bearer Token 调 API。

### 4. Human Approval

以 Operator/Admin 身份创建文档删除或 Service Restart Approval。

展示：

```text
pending
  ↓
approved
  ↓
consumed
```

强调 Approval 绑定精确的 `Agent + Tool + Target`，而且只能消费一次。

### 5. Supervisor

进入 Supervisor，运行 Offline Demo，或者提问：

> 为什么最近导入任务失败？请结合当前运维状态、知识库手册和历史数据给出排查结论。

展示执行图：

```text
Incident
   ↓
Supervisor
   ↓
Ops / Knowledge / Data
   ↓
Synthesis
```

再打开 Execution Trace。

### 6. Runs

进入 Runs，打开 Supervisor 的 Run。

展示：

- Status
- Duration
- Request ID
- Correlation ID
- Trace
- Eval

这里最适合解释平台工程化能力。

### 7. Integrations / Credentials

展示：

- Credentials → Model Provider
- Data Sources → Database Resource
- Integrations → Prometheus / Logs / Docker / Kubernetes / Controlled Services

强调这些能力都被建模成平台资源，而不是让用户编辑原始 `.env` JSON。

## 面试时重点强调

- LLM Prompt 不是安全边界，Tool 才是。
- RBAC 回答“谁能做”，Tool Policy 回答“允许什么能力”，Approval 回答“这一次高风险 Target 由谁批准”。
- Run / Trace / Eval 让 Agent 行为可以定位、审计和回归。
- Offline Demo 执行的是真实 Agent Class，而不是 UI Mock。
- Supervisor 只编排 Child Agent，不绕过 Child Agent 的 Tool Boundary。
- 产品 UI 采用资源模型：Agents、Runs、Approvals、Credentials、Data Sources、Integrations 都是一等对象。
- 在没有真实规模证据之前，基础设施保持简单。
