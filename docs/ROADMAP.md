# Enterprise Agent Platform 后续开发路线图

> 本文档用于约束和指导 `enterprise-agent-platform` 后续开发方向。  
> 目标不是继续堆叠更多预置 Agent，而是把当前项目演进成一套真正可以 **创建、发布、运行、治理、观测和评测 Agent** 的企业级 Agent Platform。

---

# 1. 当前阶段

当前版本已经具备：

- Data Agent
- Knowledge Agent
- Ops Agent
- Supervisor
- Session Login
- Bearer Token
- RBAC
- Tool Policy
- Human Approval
- Run / Trace
- Deterministic Eval
- Regression
- Prometheus Metrics
- Structured Logging
- Enterprise Web Console
- 中英文切换
- 在线 Demo
- 独立文档站

当前产品已经不再是简单的 Prompt Demo，但仍然存在一个核心限制：

> Data / Knowledge / Ops / Supervisor 仍然主要是代码中预定义的 Agent，而不是平台中可以动态创建、配置、版本化和发布的一等资源。

因此后续开发主线应从：

```text
我实现了几个 Agent
```

转变为：

```text
我实现了一个可以托管 Agent 的平台
```

---

# 2. 最终目标

最终目标：

```text
Enterprise Agent Platform v1.0

Organization / Workspace
        │
        ├── Agents
        │    ├── Definition
        │    ├── Version
        │    ├── Publish
        │    ├── Playground
        │    ├── Tools
        │    ├── Knowledge
        │    ├── Data Sources
        │    └── Guardrails
        │
        ├── Agent Runtime
        │    ├── Async Run
        │    ├── Queue / Worker
        │    ├── Streaming
        │    ├── Cancel / Retry
        │    └── Trace Span
        │
        ├── Tool Platform
        │    ├── Tool Registry
        │    ├── MCP
        │    ├── OpenAPI
        │    └── Policy
        │
        ├── Knowledge Platform
        │    ├── Knowledge Base
        │    ├── pgvector
        │    ├── Hybrid Search
        │    └── ACL
        │
        ├── Evaluation
        │    ├── Dataset
        │    ├── Evaluator
        │    ├── Experiment
        │    └── Regression Gate
        │
        ├── Governance
        │    ├── RBAC
        │    ├── Approval
        │    ├── Policy Engine
        │    ├── Audit Log
        │    └── OIDC
        │
        └── Observability
             ├── Trace
             ├── Token
             ├── Cost
             ├── Metrics
             └── Alerts
```

最终最重要的架构变化是：

> Data Agent、Knowledge Agent、Ops Agent、Supervisor 不再是“平台本身”，而只是平台中的四个 Built-in Agent Template。

---

# 3. 长期开发原则

后续所有技术决策遵循以下原则。

## 3.1 平台能力优先于 Agent 数量

暂不以继续增加 HR Agent、Finance Agent、Research Agent 等业务 Agent 为主线。

优先建设：

- Agent Definition
- Agent Runtime
- Tool Platform
- Eval
- Governance
- Observability

## 3.2 Prompt 不是安全边界

所有安全规则必须落在代码层：

```text
Identity
    ↓
RBAC
    ↓
Tool Policy
    ↓
Approval
    ↓
Execution
```

LLM 输出不能直接决定系统权限。

## 3.3 所有重要对象必须资源化

包括：

- Agent
- Tool
- Data Source
- Knowledge Base
- Credential
- Run
- Approval
- Evaluation Dataset
- Workspace

资源应具备明确：

- ID
- 状态
- 生命周期
- 权限
- 审计
- API

## 3.4 Agent 配置必须版本化

Prompt、Model、Tool、Knowledge、Data Source、Guardrail 的变更都应该产生 Version。

Run 必须知道自己运行的是哪个 Agent Version。

## 3.5 所有执行都必须可追踪

任何 Agent 执行都必须形成：

```text
Run
  ↓
Trace
  ↓
Span
```

不能存在“执行了，但是无法解释发生了什么”的路径。

## 3.6 基础设施按实际复杂度引入

不要为了技术栈完整度提前增加：

- Kafka
- Kubernetes
- 微服务
- Service Mesh
- 大型 Workflow Engine

只有真实规模或复杂度证明值得引入时才升级。

---

# 4. 版本路线

建议正式采用如下版本路线。

| Version | 目标 |
| --- | --- |
| v0.1 | 当前 Multi-Agent + Governance + Console |
| v0.2 | Dynamic Agent Platform |
| v0.3 | Async Agent Runtime |
| v0.4 | Trace / Cost / Eval Platform |
| v0.5 | Knowledge / MCP / Credential Platform |
| v0.6 | Multi-Tenant / OIDC / Audit |
| v1.0 | Production Ready |

---

# 5. M0：冻结当前 v0.1

在开始大规模平台化重构前，先冻结当前稳定版本。

建议 Tag：

```text
v0.1.0
```

当前能力作为 Baseline：

```text
Data Agent
Knowledge Agent
Ops Agent
Supervisor

Session Login
Bearer Token
RBAC
Tool Policy
Human Approval

Run
Trace
Eval
Regression

Prometheus Metrics
Structured Logging

Enterprise Web Console
Bilingual UI
Documentation Site
```

## M0 交付物

文档：

```text
docs/
├── ARCHITECTURE.md
├── DEMO.md
├── INTERVIEW.md
├── ROADMAP.md
├── SECURITY.md
├── AGENT_RUNTIME.md
└── DATA_MODEL.md
```

## M0 验收

- [ ] 当前测试全部通过
- [ ] Demo 正常登录
- [ ] Data / Knowledge / Ops / Supervisor 可运行
- [ ] Approval 可正常创建/批准/消费
- [ ] 文档站可访问
- [ ] 创建 `v0.1.0` Tag
- [ ] main 分支保持可部署状态

---

# 6. M1：Dynamic Agent Platform

**优先级：P0**

这是后续最重要的阶段。

目标：

> Agent 从代码对象升级为平台资源。

---

## 6.1 Agent Definition

新增核心数据表：

```text
agents
```

建议字段：

```text
id
name
slug
description

type
status
built_in

created_by
created_at
updated_at
```

状态：

```text
draft
published
archived
```

---

## 6.2 Agent Version

新增：

```text
agent_versions
```

建议字段：

```text
id
agent_id
version

instructions

model_provider
model
temperature
max_tokens

max_steps
timeout_seconds

tool_config
knowledge_config
data_config
guardrail_config

created_by
created_at
```

规则：

- Published Version 不允许直接覆盖。
- 修改 Agent 时创建新 Draft Version。
- Run 必须保存 `agent_id + agent_version`。
- Rollback 本质上是重新发布旧 Version。

---

## 6.3 Agent Publish

生命周期：

```text
Draft
  ↓
Playground
  ↓
Evaluation
  ↓
Publish
```

首期 API：

```text
POST /api/v1/agents

GET  /api/v1/agents
GET  /api/v1/agents/{id}

POST /api/v1/agents/{id}/versions
GET  /api/v1/agents/{id}/versions

POST /api/v1/agents/{id}/publish
POST /api/v1/agents/{id}/archive
```

---

## 6.4 Agent Builder UI

Agents：

```text
Agents                                      + New agent

Data Analyst
Published · v4
GPT-5.6
4 Tools · 2 Data Sources

Knowledge Assistant
Published · v2
2 Knowledge Bases
```

Agent Detail：

```text
Overview
Playground
Runs
Evaluations
Versions
Configuration
```

Configuration：

```text
General
Model
Instructions
Tools
Knowledge
Data
Guardrails
Advanced
```

---

## 6.5 迁移 Built-in Agent

当前：

```text
Data Agent
Knowledge Agent
Ops Agent
Supervisor
```

迁移成数据库中的 Built-in Agent。

例如：

```text
name      = Data Agent
type      = data
built_in  = true
```

运行时不再硬编码实例，而是：

```text
Agent Definition
        ↓
Agent Runtime
        ↓
Model / Tools / Knowledge / Data
```

---

## M1 验收

- [ ] 创建 Agent
- [ ] 编辑 Agent
- [ ] Draft Version
- [ ] Version History
- [ ] Publish
- [ ] Archive
- [ ] Playground
- [ ] Run 保存 Agent Version
- [ ] 4 个 Built-in Agent 完成迁移
- [ ] 新建一个 Custom Agent 可以运行

---

# 7. M2：Tool Platform

**优先级：P0**

目标：

> Tool 不再分散在代码里，而成为平台统一管理的资源。

---

## 7.1 Tool Registry

新增：

```text
tools
```

建议：

```text
id
name
display_name
description

provider
type

input_schema
output_schema

mode
risk_level
approval_required

timeout_seconds

enabled

created_at
updated_at
```

Tool Type：

```text
builtin
mcp
http
database
```

未来再考虑：

```text
python
workflow
function
```

---

## 7.2 Agent Tool Assignment

新增：

```text
agent_tools
```

UI：

```text
Tools

☑ database.schema
☑ database.query
☑ report.generate

□ prometheus.query
□ kubernetes.pods
□ service.restart
```

每个 Agent Tool 可以覆盖：

- timeout
- retry
- approval policy
- credential
- tool-specific settings

---

## 7.3 Policy Evaluation

标准调用链：

```text
Agent
 ↓
Tool Request
 ↓
Policy Evaluation
 ↓
ALLOW
DENY
APPROVAL_REQUIRED
```

Policy 输入：

```text
identity
workspace
agent
tool
target
environment
```

首期暂不引 OPA，先实现清晰、可测试的小型规则系统。

---

# 8. M2.5：MCP

**优先级：P0/P1**

新增：

```text
MCP Servers
```

模型：

```text
id
name
transport
url
credential_id
status
created_at
updated_at
```

流程：

```text
Add MCP Server
      ↓
Connect
      ↓
tools/list
      ↓
Discover Tools
      ↓
Tool Registry
      ↓
Policy Review
      ↓
Assign to Agent
```

必须坚持：

```text
MCP Tool
  ↓
Tool Registry
  ↓
Policy
  ↓
Approval
  ↓
Agent Runtime
```

禁止：

```text
MCP → 直接暴露给模型
```

---

## M2 验收

- [ ] Tool Registry
- [ ] Built-in Tool 注册
- [ ] Agent ↔ Tool
- [ ] Tool Policy
- [ ] Risk Level
- [ ] Approval Required
- [ ] MCP Server
- [ ] MCP Tool Discovery
- [ ] MCP Tool Execution
- [ ] MCP Tool 经过统一 Policy

---

# 9. M3：Async Agent Runtime

**优先级：P0**

这是后端最大的一次升级。

当前：

```text
HTTP
 ↓
Agent
 ↓
Response
```

目标：

```text
HTTP API
   ↓
Create Run
   ↓
Queue
   ↓
Worker
   ↓
Agent Runtime
   ↓
Tool
   ↓
Run Store
```

---

## 9.1 基础设施

建议：

```text
PostgreSQL
Redis
Celery
```

理由：

- PostgreSQL：平台主数据
- Redis：Queue / shared state / future rate limit
- Celery：用户已有技术基础，生态成熟

---

## 9.2 Run State Machine

正式状态：

```text
queued
running
waiting_approval
cancelling
cancelled
completed
failed
timeout
```

转换：

```text
queued
 ↓
running
 ├──→ waiting_approval
 │       ↓
 │     running
 │
 ├──→ completed
 ├──→ failed
 ├──→ timeout
 └──→ cancelling
         ↓
       cancelled
```

---

## 9.3 Run API

```text
POST /api/v1/runs

GET  /api/v1/runs
GET  /api/v1/runs/{id}

POST /api/v1/runs/{id}/cancel
POST /api/v1/runs/{id}/retry

GET  /api/v1/runs/{id}/events
```

---

## 9.4 SSE Streaming

首期采用：

```text
Server-Sent Events
```

而不是 WebSocket。

事件：

```text
run.created
run.started

step.started
step.completed

tool.started
tool.completed

approval.required

answer.delta

run.completed
run.failed
```

Playground：

```text
Planning...
   ↓
Calling database.schema
   ↓
Calling database.query
   ↓
Generating response
   ↓
Streaming answer
```

---

## 9.5 Cancel

Run 引入 Cancellation Token。

检查点：

- Agent step 前
- LLM call 前后
- Tool call 前后
- Retry 前

Tool 必须支持：

- Timeout
- Cooperative Cancel

---

## 9.6 Retry

新增：

```text
parent_run_id
retry_of
```

关系：

```text
Run #101
   ↓ retry
Run #105
```

不能覆盖原 Run。

---

## M3 验收

- [ ] PostgreSQL Platform Store
- [ ] Redis
- [ ] Worker
- [ ] Run Queue
- [ ] State Machine
- [ ] SSE
- [ ] Cancel
- [ ] Retry
- [ ] Timeout
- [ ] Waiting Approval
- [ ] Worker Failure Recovery

---

# 10. M4：Trace 2.0 / Token / Cost

**优先级：P1**

---

## 10.1 Span

当前 Trace Step 升级为 Span。

模型：

```text
trace_id
span_id
parent_span_id

run_id

type
name

start_time
end_time
duration_ms

status

input
output

error
```

类型：

```text
agent
llm
tool
retrieval
database
approval
```

---

## 10.2 Trace UI

目标：

```text
Trace Tree        Span Detail        Run Info
```

例：

```text
Run

▼ Supervisor
  ├─ Ops Agent
  │   ├─ prometheus.query
  │   └─ LLM summarize
  │
  ├─ Knowledge Agent
  │   ├─ retrieval
  │   └─ LLM answer
  │
  └─ Data Agent
      ├─ schema
      ├─ SQL generate
      ├─ query
      └─ summarize
```

---

## 10.3 Token

LLM Span 记录：

```text
provider
model

prompt_tokens
completion_tokens
total_tokens
```

---

## 10.4 Cost

增加模型价格表：

```text
model_prices
```

字段：

```text
provider
model
input_price
output_price
currency
effective_at
```

Run 聚合：

```text
total_tokens
estimated_cost
```

---

## 10.5 Dashboard

Home：

```text
Today

Runs       1,284
Tokens     8.4M
Cost       $61.20
P95        2.8s
Success    96%
```

Agent：

```text
Cost / Run
Tokens / Run
Latency
Success
Eval
```

---

## M4 验收

- [ ] Parent/Child Span
- [ ] Agent Span
- [ ] Tool Span
- [ ] LLM Span
- [ ] Retrieval Span
- [ ] Token Usage
- [ ] Estimated Cost
- [ ] Trace Tree UI
- [ ] Agent Cost Metrics
- [ ] Prometheus Export

---

# 11. M5：Evaluation Platform

**优先级：P1**

目标：

> Eval 从“Run 后检查”升级成正式 AgentOps 平台能力。

---

## 11.1 Dataset

新增：

```text
eval_datasets
eval_cases
```

Case：

```text
input

expected_output
expected_tool
expected_sql
expected_trace

metadata
```

---

## 11.2 Evaluator

支持：

```text
deterministic
regex
json
sql
trace
llm_judge
human
```

优先策略：

```text
Deterministic
      ↓
LLM Judge
```

---

## 11.3 Experiment

对比：

```text
Agent v12 + Model A

vs

Agent v13 + Model B
```

指标：

| Metric | v12 | v13 |
| --- | ---: | ---: |
| Success | 91% | 96% |
| Eval | 87 | 92 |
| P95 | 3.1s | 2.8s |
| Cost | $0.06 | $0.05 |

---

## 11.4 Regression Gate

Agent Publish：

```text
Draft
 ↓
Evaluate
 ↓
Regression Gate
 ↓
Publish
```

规则示例：

```text
success_rate >= 95%
eval_score >= 90
critical_failures == 0
```

---

## M5 验收

- [ ] Dataset
- [ ] Case
- [ ] Evaluator
- [ ] Experiment
- [ ] Agent Version Compare
- [ ] Regression
- [ ] Publish Gate
- [ ] Eval UI

---

# 12. M6：Knowledge / Data / Credential 平台化

**优先级：P1**

---

# 12.1 Knowledge Base

从：

```text
Documents
```

升级为：

```text
Knowledge Bases
```

例如：

```text
Operations KB
Product KB
Radar KB
Technical KB
```

字段：

```text
id
name

embedding_model

chunk_strategy
chunk_size
chunk_overlap

retrieval_top_k

reranker

acl
```

---

## 12.2 Agent ↔ Knowledge Base

```text
Knowledge

☑ Operations KB
☑ Product KB
□ HR KB
```

---

## 12.3 pgvector

在 KB 抽象稳定后：

```text
SQLite Vector Store
        ↓
PostgreSQL + pgvector
```

迁移条件：

- Corpus 规模增大
- O(n) Scan P95 明显恶化
- 多租户需要统一存储

---

## 12.4 Hybrid Search

目标：

```text
Question

 ├── Vector Search
 └── BM25

        ↓
      Merge
        ↓
     Reranker
        ↓
      Top K
```

---

## 12.5 Data Source 2.0

支持：

```text
PostgreSQL
Kingbase
MySQL
SQLite
```

Data Source Detail：

```text
Overview
Schema
Agents
Queries
Settings
```

---

## 12.6 Schema Explorer

```text
data_assets

id             bigint
main_type      varchar
provider       varchar
create_time    timestamp
size           bigint
```

操作：

```text
Refresh Schema
```

---

## 12.7 Credential Vault

真正资源化：

```text
credentials
```

字段：

```text
id
name
type

encrypted_secret

created_by
created_at
last_used_at
```

API 永远不能返回 Secret 明文。

引用方式：

```text
Agent / Tool
     ↓
credential_id
     ↓
Credential Store
```

生产升级：

- Vault
- Kubernetes Secret
- Cloudflare Secret
- Cloud Secret Manager

---

## M6 验收

- [ ] Knowledge Base
- [ ] Agent ↔ KB
- [ ] pgvector
- [ ] Hybrid Search
- [ ] Data Source Detail
- [ ] Schema Explorer
- [ ] Credential Resource
- [ ] Secret Encryption
- [ ] Test Connection

---

# 13. M7：Enterprise Governance

**优先级：P2**

---

## 13.1 Organization / Workspace

结构：

```text
Organization
      ↓
Workspace
      ↓
Resources
```

例如：

```text
Acme
 ├─ Production
 ├─ Development
 └─ Research
```

---

## 13.2 Tenant Isolation

所有核心资源增加：

```text
organization_id
workspace_id
```

至少覆盖：

- agents
- agent_versions
- tools
- knowledge_bases
- documents
- credentials
- data_sources
- runs
- approvals
- evaluations

Tenant Isolation 必须发生在 Repository/Query 层，不能只依赖前端。

---

## 13.3 RBAC 2.0

建议角色：

```text
Organization Admin
Workspace Admin
Developer
Operator
Approver
Viewer
```

---

## 13.4 OIDC

支持：

```text
Keycloak
Microsoft Entra ID
Generic OIDC
```

链路：

```text
Identity Provider
       ↓
Identity
       ↓
Organization
       ↓
Workspace
       ↓
RBAC
```

---

## 13.5 Audit Log

区别：

```text
Run
=
Agent Execution

Audit
=
Human / Platform Operation
```

Audit：

```text
actor
action

resource_type
resource_id

before
after

ip
request_id

created_at
```

示例：

```text
10:31 admin
Updated Agent Data Analyst

10:30 operator
Requested restart nginx

10:30 approver
Approved restart nginx

10:31 system
Restart completed
```

---

## M7 验收

- [ ] Organization
- [ ] Workspace
- [ ] Tenant Scope
- [ ] Cross Tenant Security Tests
- [ ] RBAC 2.0
- [ ] OIDC
- [ ] Audit Log

---

# 14. M8：Developer Platform / Ecosystem

---

## 14.1 API Keys

支持：

```text
API Keys
```

例如：

```text
CI Key

agents:run
runs:read
```

字段：

```text
scope
workspace
expires_at
last_used_at
```

---

## 14.2 Webhooks

事件：

```text
run.started
run.completed
run.failed

approval.requested
approval.approved

agent.published
```

---

## 14.3 Notifications

Approval / Incident 支持：

```text
Web
Webhook
Slack
企业微信
钉钉
```

---

## 14.4 OpenAPI Tool Import

流程：

```text
OpenAPI Spec
      ↓
Operation Discovery
      ↓
Tool Registry
      ↓
Policy
      ↓
Agent
```

---

## 14.5 SDK

优先：

```text
Python SDK
```

示例：

```python
client.agents.run(...)
client.runs.get(...)
client.approvals.create(...)
```

未来：

```text
JavaScript SDK
```

---

## 14.6 CLI

示例：

```bash
eap agents list

eap agents run data-agent \
  --input "统计数据"

eap runs get 123
```

---

# 15. Production Hardening

达到 v1.0 前必须完成。

---

## 15.1 PostgreSQL

正式平台数据统一迁移到 PostgreSQL。

使用：

```text
Alembic
```

要求：

- Migration 可重复
- Upgrade / Downgrade
- Migration CI Test

---

## 15.2 Redis

用于：

- Celery
- Shared Session
- Rate Limit
- Cache
- Distributed Lock

---

## 15.3 Idempotency

重要写操作支持：

```text
Idempotency-Key
```

尤其：

- Create Run
- Approval
- Execute Action
- Webhook Delivery

---

## 15.4 Retry Strategy

外部调用明确区分：

```text
retryable
non-retryable
```

策略：

```text
retry
backoff
jitter
max_attempts
```

---

## 15.5 Timeout Hierarchy

明确：

```text
HTTP Timeout
LLM Timeout
Tool Timeout
Agent Timeout
Run Timeout
Worker Timeout
```

---

## 15.6 Health

标准端点：

```text
/live
/ready
/health
```

Readiness 至少检查：

- PostgreSQL
- Redis
- Worker
- Platform Store

---

## 15.7 Secret Management

生产环境不能完全依赖：

```text
.env
```

需要支持 Secret Manager。

---

# 16. CI / CD

目标 Pipeline：

```text
Lint
  ↓
Unit Test
  ↓
Integration Test
  ↓
Security Scan
  ↓
Agent Regression
  ↓
Docs Build
  ↓
Container Build
  ↓
Deploy
```

---

## 16.1 Security Scan

建议：

```text
pip-audit
Bandit
Trivy
```

复杂度增加后再考虑：

```text
Semgrep
```

---

# 17. 测试体系

后续测试分成五层。

```text
Unit
Integration
Agent Regression
Security
E2E
```

---

## 17.1 Unit Test

重点：

- RBAC
- Policy
- Agent Version
- Publish
- Tool Registry
- Run State
- Approval
- Eval

---

## 17.2 Integration Test

真实运行：

```text
FastAPI
PostgreSQL
Redis
Worker
Fake LLM
```

不依赖真实模型。

---

## 17.3 Agent Regression

固定：

```text
Dataset
Fake LLM
Fixtures
```

要求 CI Deterministic。

---

## 17.4 Security Test

重点场景：

```text
Prompt Injection
SQL Injection
Shell Injection
Cross Tenant Access
Approval Replay
Unauthorized Tool
Credential Leakage
```

---

## 17.5 E2E

前端复杂度上升后引：

```text
Playwright
```

关键场景：

```text
Login
Create Agent
Create Version
Publish
Run
Approval
Trace
```

---

# 18. 最终核心数据模型

预计 v1.0 包含：

```text
organizations
workspaces

users
memberships

agents
agent_versions

tools
agent_tools

credentials

data_sources

knowledge_bases
documents
chunks

runs
spans

approvals

eval_datasets
eval_cases
experiments

audit_logs

api_keys
webhooks
```

不要一次性创建所有表。

按照 Milestone 演进。

---

# 19. 后端目录演进方向

长期目标可演进到：

```text
app/

  api/

  core/

  modules/

    agents/
    tools/
    runtime/
    runs/

    knowledge/
    data_sources/

    approvals/
    policies/

    evaluations/

    credentials/

    organizations/
    workspaces/

    audit/

  infrastructure/

    database/
    redis/
    llm/
    mcp/

  worker/

  platform/
```

重要：

> 不进行一次性“大爆炸重构”。

每实现一个模块，只迁移与该模块相关的代码。

---

# 20. Frontend 演进方向

继续保持当前 IA：

```text
Home

BUILD
  Agents
  Knowledge
  Data Sources

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

不要重新设计全局信息架构，除非产品对象发生明显变化。

---

## 20.1 Agents

增加：

```text
+ New Agent
```

Agent Detail：

```text
Overview
Playground
Runs
Evaluations
Versions
Configuration
```

---

## 20.2 Run Detail

目标三栏：

```text
┌ Trace Tree ─────┬ Span Detail ──────┬ Run Info ─────┐
│                 │                   │               │
│ Supervisor      │ database.query    │ Status        │
│ ├ Ops           │                   │ Duration      │
│ ├ Knowledge     │ Input             │ Tokens        │
│ └ Data          │ Output            │ Cost          │
│                 │ Error             │ Eval          │
└─────────────────┴───────────────────┴───────────────┘
```

---

## 20.3 Supervisor

Canvas：

```text
Node
 ↓ click
Inspector
```

Node 状态：

```text
Pending
Running
Success
Error
Waiting Approval
```

Inspector：

- Input
- Output
- Trace
- Evidence
- Error

---

## 20.4 Evaluations

最终：

```text
Datasets
Experiments
Regression
Evaluators
```

---

## 20.5 Audit

新增：

```text
Audit Logs
```

建议放在 OPERATE。

---

# 21. 不要做的事情

在以下条件未出现前，不做：

## 不继续堆业务 Agent

```text
HR Agent
Finance Agent
Research Agent
...
```

Custom Agent Platform 优先。

## 不提前 Kubernetes 化

单机/Compose 足以支持当前阶段。

## 不提前微服务拆分

保持 Modular Monolith。

## 不引 Kafka

Redis Queue 足够前几个阶段。

## 不做复杂 Workflow Designer

直到真正出现动态 DAG 编辑需求。

## 不因“企业级”重写前端框架

当前 Vanilla 前端仍能支撑现阶段。

当出现：

- 大量复杂共享状态
- 实时交互显著增加
- 多人前端协作
- 大量可视化编辑器

再考虑 React / Vue。

## 不先做几十种 Connector

优先保证 Tool Registry / MCP 架构正确。

---

# 22. Sprint 执行计划

建议近期分成以下 Sprint。

---

## Sprint 1：Platform Store + Agent Definition

目标：

> Agent 成为真实平台资源。

开发：

- PostgreSQL Platform Store
- Alembic
- Agent Model
- Agent Version
- Agent API
- Agent Directory
- Create Agent
- Edit Agent
- Publish Agent

完成标准：

- Custom Agent 可以保存
- Custom Agent 可以创建 Version
- Custom Agent 可以 Publish
- Built-in Agent 开始迁移

---

## Sprint 2：Tool Registry

目标：

> Agent 不再写死 Tool。

开发：

- Tool Registry
- Tool Schema
- Agent Tools
- Tool Configuration
- Tool Policy
- Risk
- Approval Binding

完成标准：

- Agent 可以动态选择 Tool
- 未授权 Tool 不能执行
- 高风险 Tool 可以进入 Approval

---

## Sprint 3：MCP

开发：

- MCP Server
- Connect
- Tool Discovery
- Import to Registry
- Agent Assignment
- Policy

完成标准：

- 添加一个真实 MCP
- 自动发现 Tool
- Tool 经过统一 Policy 执行

---

## Sprint 4：Async Runtime

开发：

- Redis
- Celery
- Run Queue
- Worker
- State Machine
- Cancel
- Retry
- Timeout

---

## Sprint 5：Streaming + Trace Span

开发：

- SSE
- Run Events
- Trace Span
- Parent/Child
- Run Detail UI

---

## Sprint 6：Token / Cost

开发：

- Token Usage
- Model Pricing
- Cost Estimate
- Dashboard
- Agent Cost Metrics

---

## Sprint 7：Eval Platform

开发：

- Dataset
- Cases
- Evaluator
- Experiment
- Compare
- Regression Gate

---

## Sprint 8：Knowledge / Credential

开发：

- Knowledge Base
- pgvector
- Hybrid Search
- Credential Vault
- Data Source Detail

---

## Sprint 9：Enterprise Governance

开发：

- Organization
- Workspace
- Tenant Isolation
- RBAC 2.0
- OIDC
- Audit

---

## Sprint 10：Production Hardening

开发：

- API Keys
- Webhooks
- Secret Manager
- Security Test
- E2E
- Deployment Hardening

---

# 23. 每个 Sprint 的 Definition of Done

一个功能只有满足以下条件才算完成：

## Backend

- API 实现
- 数据模型实现
- Migration 完成
- 权限校验完成
- Error Model 完成

## Frontend

- UI 可操作
- Loading
- Empty
- Error
- Disabled
- 权限状态

## Test

- Unit Test
- 关键 Integration Test
- Security Boundary Test

## Observability

关键执行必须进入：

- Run
- Trace
- Audit 或 Metrics（按场景）

## Documentation

更新：

- README（如需要）
- ARCHITECTURE
- ROADMAP
- API / Demo Guide

## Deployment

- Public Demo Smoke Test
- No Regression

---

# 24. 每次提交前强制检查

至少：

```bash
python -m compileall -q app tests scripts
python -m pytest -q
git diff --check
```

前端：

```bash
node --check app/static/app.js
node --check app/static/i18n.js
```

文档：

```bash
npm run docs:build
```

---

# 25. Git / Release 规范

主分支：

```text
main
```

必须始终保持：

- 可运行
- 可测试
- 可部署

功能分支：

```text
feature/agent-definition
feature/tool-registry
feature/mcp
feature/async-runtime
feature/eval-platform
```

每个重要版本：

```text
v0.1.0
v0.2.0
v0.3.0
...
```

重大架构变更前保留 Tag。

---

# 26. 技术选型触发条件

避免凭感觉升级。

## SQLite → PostgreSQL

当开始实现 Dynamic Agent Definition 时执行。

原因：

平台核心资源正式需要稳定关系模型和 Migration。

## Redis / Celery

当 Async Run 开始实现时引入。

不要提前。

## pgvector

当 Knowledge Base 抽象完成，并且知识库规模使 O(n) Scan 成为问题时引入。

## React / Vue

满足任意多个条件再评估：

- 前端交互状态复杂
- 大量组件共享
- 多人前端开发
- 实时状态很多
- Workflow/Graph 编辑器出现

## Kubernetes

满足：

- 多副本
- Worker 自动扩容
- 多环境 Deployment
- 容器调度成为真实问题

之后再考虑。

---

# 27. 开发优先级

未来 2～3 个月优先级：

## P0

1. PostgreSQL Platform Store
2. Dynamic Agent Definition
3. Agent Version
4. Agent Publish
5. Tool Registry
6. Agent Tool Assignment
7. MCP
8. Async Run Runtime

## P1

9. SSE
10. Cancel / Retry
11. Trace Span
12. Token / Cost
13. Eval Dataset
14. Experiment
15. Regression Gate
16. Credential Vault
17. Knowledge Base

## P2

18. pgvector / Hybrid Search
19. Workspace
20. Multi-Tenant
21. OIDC
22. Audit
23. API Keys
24. Webhooks

---

# 28. 项目定位演进

当前：

> Enterprise Multi-Agent Platform

完成 M1 ～ M3：

> **Enterprise Agent Runtime & Control Plane**

完成 M4 ～ M7：

> **Multi-tenant Enterprise AgentOps Platform**

目标不是靠名称升级，而是让系统真正具备相应能力。

---

# 29. 下一步立即执行项

下一个开发阶段固定为：

# v0.2 — Dynamic Agent Platform

执行顺序：

```text
1. 冻结 v0.1.0

2. PostgreSQL Platform Store
3. Alembic

4. Agent Definition
5. Agent Version
6. Agent Publish

7. Agent Repository
8. Agent Service
9. Agent API

10. Agent Directory UI
11. Create Agent UI
12. Configuration UI
13. Versions UI

14. Built-in Agent Migration
15. Custom Agent Runtime Adapter

16. Tests
17. Docs
18. Demo
19. Tag v0.2.0
```

在 v0.2 完成之前：

- 不新增新的业务 Agent
- 不做 Kubernetes
- 不做微服务拆分
- 不做 Workflow Designer
- 不重写前端框架

---

# 30. 最终原则

后续开发判断某个功能是否应该现在做时，问三个问题：

### 这个功能是否让 Agent 更平台化？

如果只是增加一个新 Demo 场景，优先级低。

### 这个功能是否提升安全、治理、可观测或可评测能力？

如果是，优先级高。

### 当前真实复杂度是否已经证明需要增加基础设施？

如果没有，不提前引入。

最终目标不是：

> 功能越来越多。

而是：

> **平台边界越来越清楚，Agent 越来越可配置，执行越来越可控，问题越来越容易定位，质量越来越可以量化。**

这份路线图应作为后续版本规划和技术取舍的默认依据。
