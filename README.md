# Enterprise Agent Platform

[![CI](https://github.com/yvanu/enterprise-agent-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/yvanu/enterprise-agent-platform/actions/workflows/ci.yml)

[Documentation](https://docs.agent.majhoon.site) · [Live Demo](https://agent.majhoon.site) · [Architecture](docs/ARCHITECTURE.md) · [Roadmap](docs/roadmap.md) · [Progress](docs/PROGRESS.md) · [Safe Deployment](docs/deployment.md) · [Demo Guide](docs/DEMO.md) · [Interview Guide](docs/INTERVIEW.md) · [Changelog](CHANGELOG.md)

面向企业场景的多 Agent 平台。Data、Knowledge、Ops 三个业务 Agent 共用同一套 LLM Runtime、配置、Web Session / Bearer Token 身份认证、RBAC、Tool Policy、Human Approval、运行审计、确定性 Eval、Regression Suite 和 API 服务；Supervisor 只在真实跨 Agent 故障调查场景中负责只读编排。Web Console 采用资源化 Enterprise SaaS 信息架构，统一管理 Agents、Knowledge、Data Sources、Runs、Evaluations、Approvals、Integrations、Credentials 与 Policies。

> **开发进度（2026-10-08）**：M1 / M2 / M2.5 首版代码已完成；73 项自动化测试通过。M3 异步运行时待开发，真实 MCP/REST 联调、生产迁移和线上部署仍需验收。完整状态见 [开发进度](docs/PROGRESS.md)。

## v0.2 Dynamic Agent Platform

Agent 已从代码中的固定对象升级为平台一等资源。当前支持：

- 动态创建 Custom Agent
- Draft / Published / Archived 生命周期
- 不可变 Agent Version
- Published Version 回滚/重新发布
- Agent Detail / Playground / Versions / Configuration
- Run 记录 `agent_id + agent_version`
- Data / Knowledge / Ops / Supervisor 作为数据库中的 Built-in Agent Definition
- Generic Agent 使用统一 Runtime Adapter 执行当前 Published Version
- `agents` / `agent_versions` 采用 SQLAlchemy 模型与 Alembic Migration
- Compose 环境使用 PostgreSQL 保存 Dynamic Agent Platform 资源

当前仍保留 Runs / Approvals 的 v0.1 SQLite Store，等 v0.3 Async Runtime 时一起迁移，避免在 M1 提前耦合未来的 Queue / Worker / Run State Machine。

### M2 Tool Platform

Tool 已从静态 Policy 列表升级成平台资源，并与 Agent Version 绑定：

- `tools`：统一保存 Tool Key、Provider、Type、Input/Output Schema、Timeout、Read/Write Mode、Risk、Approval Requirement
- `agent_tools`：按 Agent Version 保存 Tool Assignment，Published Version 的 Tool 集合只读
- 新建 Draft Version 会自动继承上一版本 Tool Assignment
- Data / Knowledge / Ops 内置能力自动注册到 Tool Registry
- 专用工作区与 `/api/v1/agents/{id}/run` 走同一套 Tool Assignment 校验
- Supervisor 委派子 Agent 时切换到各子 Agent 的 Tool Context，不绕过能力边界
- Policies 页面继续复用原 API，但数据源已经切换为 Tool Registry

### M2.5 MCP 工具接入（第一阶段）

支持管理员注册允许列表内的 Streamable HTTP MCP Server、发现并注册工具、在 Agent Version 中分配工具，以及 Generic Agent 的 OpenAI-compatible Function Calling 工具执行循环。每一次 MCP 工具调用仍须经过 Tool Assignment、Policy 和一次性审批检查，执行记录进入 Run/Trace。Web Console 的 Tools 页面管理 MCP Server，Agent Playground 可提交 MCP 审批申请并使用已通过的审批编号。

**安全边界：** 远端 MCP Tool 默认高风险写操作。当前 Generic Agent 采用“具体 JSON 参数提案 → 人工审批 → 确定性恢复”，审批绑定 Agent ID、发布版本、Tool ID 和完整参数，单次消费。执行安全边界已有测试；真实高危生产接入前仍需完成远端联调、超时/幂等设计和多步骤持久化工作流。详见 [MCP 接入与限制](docs/mcp-integration.md)。

### M2.5 OpenAPI REST 工具接入（第一阶段）

支持由管理员上传 OpenAPI 3.x JSON 规范，并将限定的 GET/POST JSON 操作导入统一 Tool Registry。实际 REST 地址必须在服务端 `OPENAPI_ALLOWED_BASE_URLS` 白名单中；规范中内置的服务器地址不参与调用。工具按照 Agent Version 授权，默认高风险并需要完整参数级审批。Generic Agent 可以通过 Function Calling 提议操作，人工审批后按照冻结参数恢复执行。控制台 Tools 页面可以导入规范并查看已接入的服务。

详细用法、安全边界和首版限制见 [OpenAPI 接入说明](docs/openapi-integration.md)。

### MCP / OpenAPI 真实 HTTP Mock 联调

补充真实回环 TCP / HTTP 的集成回归：MCP 握手与 SSE、OpenAPI GET/POST、参数级审批/恢复及重定向拒绝；仅使用 `127.0.0.1` 随机端口和测试临时库，不访问真实业务服务。执行 `nice -n 15 timeout 25s .venv/bin/python -m pytest -q tests/test_wire_mock_integration.py`。参见 [Mock 联调和真实服务接入步骤](docs/mock-integration.md)。

公网只读联调另提供**显式可选**命令：`nice -n 15 timeout 60s .venv/bin/python scripts/live_integration_smoke.py --run-live`。已用独立临时库与固定 LLM 答复，实际通过 DeepWiki MCP 的工具发现/只读调用以及 JSONPlaceholder REST GET，验证了批准前拦截、批准后结果、Run/Trace 与防重放。它不会注册到线上服务，也不加入默认 CI。

## 业务 Agent 与 Supervisor

### Data Agent
自然语言 → Schema 感知 → SQL 生成 → 安全校验 → 自动纠错 → 数据结论。

已实现：
- PostgreSQL / Kingbase / SQLite
- 多数据源配置与按请求切换数据源
- Schema 自动感知
- SELECT/CTE 只读 SQL 安全网关
- 最大结果集限制
- SQL 执行失败反馈给模型并自动纠错
- 查询结果总结
- 数值结果自动生成轻量图表
- 自动生成可下载 Markdown 分析报告

### Knowledge Agent
企业知识检索 → RAG → 带来源回答。

已实现第一版：
- 文本直接写入以及 txt / md / csv / json / PDF / DOCX 文件上传
- PDF / DOCX 文本提取与文档自动分块
- OpenAI-compatible Embedding
- SQLite 存储向量
- 余弦相似度检索
- 检索结果作为上下文回答
- 返回原始来源
- 知识文档目录查询
- 文档版本、标签和允许角色范围；更新文档时版本自动递增并重建分块/Embedding
- 检索和文档目录按当前认证角色过滤
- 知识文档删除采用 Human-in-the-loop 审批，审批通过后才能执行且审批单次消费

当前采用进程内 O(n) 向量扫描，适合项目演示和小规模知识库；访问范围在检索前按认证角色过滤。数据量真正变大时再替换 pgvector / Vectorize，不提前引入向量数据库。

### Ops Agent
系统运行状态 → LLM 诊断。

已实现第一版：
- CPU 数量
- Load Average
- 内存 / Swap
- 磁盘使用情况
- 只读系统快照
- 基于快照的故障分析

已支持通过配置的只读日志文件和 Prometheus API 参与诊断；日志路径只能由服务端配置，不能由请求指定。还可显式启用固定只读命令的 Docker 容器列表与 Kubernetes Pod 列表。受控写操作目前支持白名单 systemd 服务重启，必须经过 Human Approval；仍不接受任意 Shell。

## 架构

```text
app/
├── agents/
│   ├── data/
│   ├── knowledge/
│   ├── ops/
│   └── supervisor/     # 跨 Agent 故障调查编排
├── modules/
│   ├── agents/         # Agent Definition / Version / Repository / Runtime Adapter
│   └── tools/          # Tool Registry / Versioned Agent Tool Assignment
├── platform/
│   ├── llm.py          # Chat + Embedding，共享 Runtime
│   ├── policy.py       # Tool 风险与权限清单
│   ├── approvals.py    # Human-in-the-loop 审批与单次授权
│   ├── runs.py         # Agent Run 审计、Request/Correlation 关联
│   ├── observability.py# 统一错误模型、请求上下文、结构化日志
│   ├── evals.py        # 基于 Trace 的确定性 Eval
│   └── regression.py   # 固定业务样本回归测试
├── api/
│   ├── agents.py       # Dynamic Agent CRUD / Version / Publish / Run
│   ├── tools.py        # Tool Registry / Agent Version Tool Assignment
│   ├── data.py
│   ├── knowledge.py
│   └── ops.py
├── db/
│   ├── engine.py
│   ├── introspection.py
│   └── sql_guard.py
├── core/
│   └── config.py
└── main.py
```

Supervisor 已在真实故障调查链路中启用：Ops 获取当前运行证据，Knowledge 检索运维手册，Data 查询历史业务数据，最后由 Supervisor 汇总结论。它只编排只读分析能力，不绕过各 Agent 的 Tool Policy，也不会自动执行修复动作。

```mermaid
flowchart LR
  UI[Web UI / API Client] --> AUTH[Auth + RBAC]
  AUTH --> DATA[Data Agent]
  AUTH --> KNOW[Knowledge Agent]
  AUTH --> OPS[Ops Agent]
  AUTH --> SUP[Supervisor]
  SUP --> OPS
  SUP --> KNOW
  SUP --> DATA
  DATA --> POLICY[Tool Policy]
  KNOW --> POLICY
  OPS --> POLICY
  POLICY --> APPROVAL[Human Approval]
  DATA --> RUNS[Runs / Eval / Metrics]
  KNOW --> RUNS
  OPS --> RUNS
```

## 一键离线演示

不配置 LLM Key 也可以完整跑一遍跨 Agent 故障调查：

```bash
python scripts/demo_incident.py
```

Web 的 Supervisor 页签也提供“一键离线 Demo”，对应接口为 `POST /api/v1/platform/demo/incident`。离线 Demo 使用临时 SQLite、临时知识库和模拟日志，执行完成后只保留 Run/Trace 元数据。

脚本使用临时 SQLite、固定知识库、模拟超时日志和 Deterministic Fake LLM，实际经过 Data / Knowledge / Ops / Supervisor 的正式业务代码，不访问外部服务，也不会改生产数据。需要机器可读结果时使用：

```bash
python scripts/demo_incident.py --json
```

完整系统边界与时序图见 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)，Web/审批/Supervisor 演示步骤见 [`docs/DEMO.md`](docs/DEMO.md)，简历表述、设计取舍和常见面试问题见 [`docs/INTERVIEW.md`](docs/INTERVIEW.md)。

## 身份认证与 RBAC

默认开发模式下 `AUTH_ENABLED=false`，API 以 `development/admin` 身份运行；共享演示或生产环境应开启认证：

```env
AUTH_ENABLED=true
AUTH_TOKENS={"user-token":"alice:user","operator-token":"operator:operator","approver-token":"reviewer:approver","admin-token":"admin:admin"}

CONSOLE_USERNAME=demo
CONSOLE_PASSWORD=demo
CONSOLE_ROLE=admin
SESSION_MAX_AGE_SECONDS=43200
```

Web Console 使用独立登录页。登录成功后服务端生成随机 Session Token，并通过 HttpOnly / SameSite=Lax Cookie 保存；浏览器不需要持有管理员 Bearer Token。脚本、API Client 和自动化程序仍可继续使用 Bearer Token。演示环境默认账号为 `demo / demo`，生产环境必须替换或关闭演示凭据。

角色分工：`user` 可使用普通只读 Agent 能力；`operator` 可写入知识库、发起审批和执行已批准动作；`approver` 可查看并审批请求；`admin` 拥有全部权限。审批人由认证身份确定，客户端不能伪造审批人；非管理员不能审批自己发起的请求。

当前 Web Session 使用进程内存储，适合单实例演示；多副本生产环境应迁移到 OIDC/JWT、Redis 或数据库 Session Store。启动时会执行配置检查：生产环境必须启用认证、不能使用 `.env.example` 的示例 token；`AUTH_ENABLED=true` 时必须配置合法 `username:role`。`LLM_API_KEY` 与 Console Password 使用 `SecretStr`，`AUTH_TOKENS` 不进入 Settings repr；`.env` 已被 gitignore，生产部署应通过环境变量或 Secret Store 注入真实凭据。

## Request Trace 与统一错误模型

每个 HTTP 请求都会生成新的 `X-Request-ID`；调用方可以通过 `X-Correlation-ID` 传入跨服务/跨步骤关联 ID。两者都会回写到响应头，并写入该请求触发的 Agent Run，便于从 HTTP 请求追踪到 Run/Trace。HTTP 请求和 Agent Run 同时输出 JSON 结构化日志。

API 错误统一为：

```json
{"error":{"code":"NOT_FOUND","message":"Run 不存在","request_id":"...","correlation_id":"...","details":null}}
```

校验错误会使用 `VALIDATION_ERROR` 并在 `details` 中返回字段错误；未处理异常只返回 `INTERNAL_ERROR`，不把服务端堆栈泄露给客户端。

`RATE_LIMIT_PER_MINUTE` 提供单进程、按客户端 IP 的轻量 API 限流，`0` 可关闭；超过限制返回 `429 RATE_LIMITED` 和 `Retry-After: 60`。多副本生产环境应把全局限流下沉到 API Gateway/Redis，而不是依赖进程内计数器。

## CI / Regression

GitHub Actions 会在 `main` push 和 Pull Request 时使用 Python 3.11 执行 `compileall`、完整 `pytest`、`pip check` 和 `pip-audit`。其中包含离线 Regression Suite，因此 CI 不依赖外部 LLM Key，也不会访问生产数据库；Workflow 权限固定为只读仓库内容。

## Docker 部署与压测

镜像使用 Python 3.11、非 root 用户，并已安装 PostgreSQL 驱动：

```bash
cp .env.example .env
docker compose up --build
```

`/app/data` 使用 Docker volume 持久化 legacy Run/Approval、Knowledge 与 Demo 数据；Dynamic Agent Definition / Version 在 Compose 中使用独立 PostgreSQL volume。容器启动时先执行 `alembic upgrade head` 再启动 FastAPI。Compose healthcheck 使用 `/health/ready`。业务数据源仍通过 `DATABASE_URL` 或 `DATA_SOURCES` 独立配置，不会在启动时修改非 SQLite 业务库。

提供一个只依赖 Python 标准库的轻量压测脚本：

```bash
python scripts/load_test.py --url http://127.0.0.1:8000/health --requests 500 --concurrency 20
python scripts/load_test.py --url http://127.0.0.1:8000/api/v1/platform/tools --token admin-token
```

## 快速启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

打开：

- `http://127.0.0.1:8000/`：Multi-Agent Web 演示界面
- `http://127.0.0.1:8000/docs`：完整 API

可选多数据源配置：

```env
DATA_SOURCES={"analytics":{"url":"postgresql+psycopg://readonly:password@db-host/analytics","schema":"public"}}
```

额外数据源只在服务端配置，API 只暴露数据源名称和 schema，不返回连接串。

自然语言能力需要配置：

```env
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=
LLM_MODEL=
EMBEDDING_MODEL=
```

兼容 OpenAI Chat Completions / Embeddings API 的本地服务可以不配置 API Key。

Ops 受控重启需要显式配置服务白名单：

```env
OPS_ALLOWED_SERVICES=nginx,my-api
```

## API

### Health
- `GET /health` / `GET /health/live`：进程存活检查，不探测外部依赖
- `GET /health/ready`：数据库、平台状态库、知识库就绪检查；失败返回 503

### Auth
- `GET /api/v1/auth/status`：返回认证模式状态
- `POST /api/v1/auth/login`：Web Console 用户名/密码登录并创建 HttpOnly Session
- `POST /api/v1/auth/logout`：注销当前 Web Session
- `GET /api/v1/auth/me`：返回当前认证用户和角色

### Agents
- `GET /api/v1/agents`：Agent Directory
- `POST /api/v1/agents`：创建 Custom Agent Draft
- `GET /api/v1/agents/{id}`：Agent Detail + Versions
- `PATCH /api/v1/agents/{id}`：更新 Agent 名称/描述
- `GET /api/v1/agents/{id}/versions`：版本历史
- `POST /api/v1/agents/{id}/versions`：从最新版本创建 Draft Version
- `POST /api/v1/agents/{id}/publish`：发布或回滚到指定 Version
- `POST /api/v1/agents/{id}/archive`：归档 Custom Agent
- `POST /api/v1/agents/{id}/run`：执行当前 Published Version

### Tools
- `GET /api/v1/tools`：Tool Registry，可按 namespace 过滤
- `GET /api/v1/tools/{tool_id}`：Tool Resource Detail
- `GET /api/v1/agents/{id}/versions/{version}/tools`：查看指定 Agent Version 的 Tool Assignment
- `PUT /api/v1/agents/{id}/versions/{version}/tools`：替换 Draft Version 的 Tool Assignment

### Platform
- `GET /api/v1/platform/tools`：统一 Tool Policy 清单
- `GET /api/v1/platform/runs`：Agent 运行记录，可按 Agent 过滤
- `GET /api/v1/platform/runs/{run_id}`：Run 详情、Trace 与对应 Eval 明细
- `GET /api/v1/platform/evals`：对 Run Trace 做确定性评估，可按 Agent 过滤
- `GET /api/v1/platform/metrics`：按 Agent 汇总运行次数、成功率、平均耗时、P50/P95、错误类型和 Eval 指标
- `GET /api/v1/platform/metrics/prometheus`：Prometheus 文本格式平台指标
- `GET /api/v1/platform/approvals`：`operator/approver/admin` 查看审批记录
- `POST /api/v1/platform/approvals`：`operator/admin` 为需要审批的 Tool 创建审批请求
- `POST /api/v1/platform/approvals/{id}/decision`：`approver/admin` 批准或拒绝审批请求
- `POST /api/v1/platform/demo/incident`：`operator/admin` 一键运行隔离的跨 Agent 标准 Demo
- `POST /api/v1/platform/regression/run`：运行隔离的固定业务样本回归测试

### Data
- `GET /api/v1/data/sources`
- `GET /api/v1/data/schema?source=default`
- `POST /api/v1/data/sql`：请求体可指定 `source`
- `POST /api/v1/data/ask`：请求体可指定 `source`

### Knowledge
- `GET /api/v1/knowledge/documents`
- `DELETE /api/v1/knowledge/documents/{document_id}?approval_id=...`：消费已批准的删除审批后执行
- `POST /api/v1/knowledge/documents`：支持 `tags` 和 `allowed_roles`
- `PUT /api/v1/knowledge/documents/{document_id}`：增量更新文档并递增版本
- `POST /api/v1/knowledge/documents/upload`
- `POST /api/v1/knowledge/ask`

### Supervisor
- `POST /api/v1/supervisor/investigate`：`operator/admin` 执行 Ops → Knowledge → Data → 综合结论的只读故障调查

### Ops
- `GET /api/v1/ops/snapshot`
- `GET /api/v1/ops/logs?lines=80`
- `POST /api/v1/ops/prometheus/query`
- `GET /api/v1/ops/docker`
- `GET /api/v1/ops/kubernetes`
- `POST /api/v1/ops/services/{service}/restart?approval_id=...`：白名单服务 + 审批后重启
- `POST /api/v1/ops/diagnose`

## 安全边界

模型不能直接执行任意 SQL。Data Agent 查询必须经过 SQL 安全网关；生产数据库仍应使用独立只读账号。

平台维护并强制执行统一 Tool Registry + Versioned Agent Tool Assignment + Tool Policy，校验 Agent Version 是否拥有该能力、风险等级、读写模式和审批状态；未注册 Tool、未分配 Tool、模式不匹配或待审批 Tool 会被拒绝。Published Version 的 Tool Assignment 不允许原地修改。平台指标会基于最近的 Run 聚合各 Agent 的运行次数、成功率、平均耗时、P50/P95、错误类型、平均 Eval 分和 Eval 通过率，并提供 Prometheus 文本格式出口。Run 详情可直接查看 Trace 与 Eval 检查项，失败 Run 会显示异常类型，便于定位失败阶段。Agent Run 持久化 Agent 类型、状态、耗时、Trace、异常类型、Request ID 和 Correlation ID，不持久化用户问题原文。Eval 直接检查 Run 状态、Trace 错误和关键步骤是否齐全，不额外调用 LLM，结果可重复、成本为零。Regression Suite 使用临时 SQLite 数据库和确定性 Fake LLM，验证 Data Agent 的分类聚合与失败任务统计，以及 Knowledge Agent 的雷达/海洋资料 Top-1 检索，不触碰生产数据。Knowledge Agent 的 `document_delete` 是当前首个真实 Human-in-the-loop 写操作：Tool Policy 标记为 `medium/write/approval_required`，必须先由 `operator/admin` 创建审批、再由 `approver/admin` 通过认证身份批准，并以匹配 Agent/Tool/Target 的审批 ID 单次消费后才能删除；请求人、审批人、执行人都会写入审批审计记录。Ops Agent 除只读系统信息、服务端白名单日志、Prometheus、固定 `docker ps` / `kubectl get pods` 外，现已支持 `OPS_ALLOWED_SERVICES` 白名单内的 `systemctl restart <service>`。该 Tool 标记为 `high/write/approval_required`，审批 ID 会绑定 `service:<name>` 并单次消费；仍不接受任意 Shell。未来配置变更、Kubernetes rollout/scale 等动作继续复用同一审批机制。
