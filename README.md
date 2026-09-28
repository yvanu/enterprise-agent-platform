# Enterprise Agent Platform

[![CI](https://github.com/yvanu/enterprise-agent-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/yvanu/enterprise-agent-platform/actions/workflows/ci.yml)

[Architecture](docs/ARCHITECTURE.md) · [Demo Guide](docs/DEMO.md) · [Interview Guide](docs/INTERVIEW.md) · [Changelog](CHANGELOG.md)

面向企业场景的多 Agent 平台。Data、Knowledge、Ops 三个业务 Agent 共用同一套 LLM Runtime、配置、Web Session / Bearer Token 身份认证、RBAC、Tool Policy、Human Approval、运行审计、确定性 Eval、Regression Suite 和 API 服务；Supervisor 只在真实跨 Agent 故障调查场景中负责只读编排。Web Console 采用资源化 Enterprise SaaS 信息架构，统一管理 Agents、Knowledge、Data Sources、Runs、Evaluations、Approvals、Integrations、Credentials 与 Policies。

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
├── platform/
│   ├── llm.py          # Chat + Embedding，共享 Runtime
│   ├── policy.py       # Tool 风险与权限清单
│   ├── approvals.py    # Human-in-the-loop 审批与单次授权
│   ├── runs.py         # Agent Run 审计、Request/Correlation 关联
│   ├── observability.py# 统一错误模型、请求上下文、结构化日志
│   ├── evals.py        # 基于 Trace 的确定性 Eval
│   └── regression.py   # 固定业务样本回归测试
├── api/
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

`/app/data` 使用 Docker volume 持久化。Compose healthcheck 使用 `/health/ready`。若接企业 PostgreSQL/Kingbase，只需通过 `DATABASE_URL` 或 `DATA_SOURCES` 配置连接，不会在启动时修改非 SQLite 业务库。

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

平台维护并强制执行统一 Tool Policy，校验所属 Agent、风险等级、读写模式和审批状态；未注册 Tool、模式不匹配或待审批 Tool 会被拒绝。平台指标会基于最近的 Run 聚合各 Agent 的运行次数、成功率、平均耗时、P50/P95、错误类型、平均 Eval 分和 Eval 通过率，并提供 Prometheus 文本格式出口。Run 详情可直接查看 Trace 与 Eval 检查项，失败 Run 会显示异常类型，便于定位失败阶段。Agent Run 持久化 Agent 类型、状态、耗时、Trace、异常类型、Request ID 和 Correlation ID，不持久化用户问题原文。Eval 直接检查 Run 状态、Trace 错误和关键步骤是否齐全，不额外调用 LLM，结果可重复、成本为零。Regression Suite 使用临时 SQLite 数据库和确定性 Fake LLM，验证 Data Agent 的分类聚合与失败任务统计，以及 Knowledge Agent 的雷达/海洋资料 Top-1 检索，不触碰生产数据。Knowledge Agent 的 `document_delete` 是当前首个真实 Human-in-the-loop 写操作：Tool Policy 标记为 `medium/write/approval_required`，必须先由 `operator/admin` 创建审批、再由 `approver/admin` 通过认证身份批准，并以匹配 Agent/Tool/Target 的审批 ID 单次消费后才能删除；请求人、审批人、执行人都会写入审批审计记录。Ops Agent 除只读系统信息、服务端白名单日志、Prometheus、固定 `docker ps` / `kubectl get pods` 外，现已支持 `OPS_ALLOWED_SERVICES` 白名单内的 `systemctl restart <service>`。该 Tool 标记为 `high/write/approval_required`，审批 ID 会绑定 `service:<name>` 并单次消费；仍不接受任意 Shell。未来配置变更、Kubernetes rollout/scale 等动作继续复用同一审批机制。
