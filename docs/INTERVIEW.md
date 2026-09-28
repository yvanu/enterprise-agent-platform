# Enterprise Agent Platform：面试介绍与高频面试题

> 项目仓库：`yvanu/enterprise-agent-platform`
>
> 在线演示：`https://agent.majhoon.site`
>
> 默认演示账号：`demo / demo`

---

# 1. 项目定位

## 30 秒版本

这是一个面向企业场景的 **Multi-Agent Control Plane**。

平台目前有 3 个业务 Agent：

- **Data Agent**：自然语言转 SQL、Schema 感知、只读 SQL Guard、自动纠错、结果总结；
- **Knowledge Agent**：企业知识库 RAG、文档分块、Embedding、角色级权限过滤、来源引用；
- **Ops Agent**：系统快照、日志、Prometheus、Docker/Kubernetes 只读诊断，以及审批后的受控服务重启；

另外还有一个 **Supervisor**，负责把 Ops、Knowledge、Data 三个 Agent 的证据串起来做跨 Agent 故障调查。

平台层统一实现了登录认证、RBAC、Tool Policy、Human-in-the-loop Approval、Run/Trace、Request/Correlation ID、Eval、Regression、Prometheus Metrics、结构化日志和企业级 Web Console。

---

## 1 分钟版本

这个项目不是“几个 Prompt + 几个接口”的 Agent Demo，而是我按企业应用思路做的一套 **Agent 平台**。

我把系统拆成了两层：

第一层是业务 Agent：

- Data Agent 负责结构化数据分析；
- Knowledge Agent 负责非结构化知识检索；
- Ops Agent 负责运行环境诊断；
- Supervisor 负责跨 Agent 编排和证据汇总。

第二层是平台能力：

- 身份认证与 RBAC；
- Tool Policy；
- 高风险操作 Human Approval；
- Run / Trace；
- Request ID / Correlation ID；
- 确定性 Eval；
- Regression Suite；
- Prometheus 指标；
- 结构化日志；
- 配置中心；
- 企业级 Web Console。

我比较关注的点不是“模型会不会回答”，而是 **模型出了错以后系统怎么约束、怎么审计、怎么定位、怎么回归、怎么安全执行动作**。

---

## 3～5 分钟版本

这个项目起点其实是一个 Data Agent，但我后面逐步把它演进成了一个 Multi-Agent Platform。

最早的 Data Agent 只解决一个问题：

> 用户用自然语言提问，系统自动理解数据库 Schema，生成 SQL，查询数据，然后返回结论。

但在做的过程中我发现，真正企业落地时问题远不止“生成 SQL”。

例如：

- LLM 生成了危险 SQL 怎么办？
- 数据库执行失败怎么自动纠错？
- 用户到底有没有权限调用某个 Tool？
- 高风险操作能不能让模型直接执行？
- 某次 Agent 为什么失败？
- 怎么从一次 HTTP 请求定位到具体 Agent Run？
- Agent 质量如何量化？
- 多 Agent 之间如何协作？
- 某个子 Agent 出错时整个链路是否必须失败？
- 如何让前端不像一个 API Demo，而像真正的平台？

所以项目逐步形成了现在的架构：

```text
Web Console / API
        │
        ▼
Authentication / RBAC
        │
        ├──────── Data Agent
        │
        ├──────── Knowledge Agent
        │
        ├──────── Ops Agent
        │
        └──────── Supervisor
                     │
                     ├── Ops
                     ├── Knowledge
                     └── Data

所有 Agent 统一经过：

Tool Policy
Human Approval
Run / Trace
Eval
Metrics
Structured Logs
```

Data Agent 的安全边界在 SQL Guard 和只读数据库权限，而不是 Prompt。

Knowledge Agent 会在检索前按角色过滤可见文档。

Ops Agent 不允许执行任意 Shell，只能调用固定、服务器端配置的只读能力；服务重启需要进入审批流程，而且 Approval 会绑定具体 `Agent + Tool + Target`，只能消费一次。

Supervisor 只做跨 Agent 只读调查，不绕过子 Agent 自己的安全边界。

我还做了统一的 Run/Trace、Request ID、Correlation ID 和确定性 Eval，因此可以做到：

> 从用户报错的一次 HTTP 请求，定位到对应 Agent Run，再定位到具体失败 Tool 和 Trace Step。

前端则重新按 Enterprise SaaS 的方式设计，不再把 4 个 Agent 直接塞到 Sidebar，而是把 Agent、Knowledge、Data Source、Run、Approval、Integration、Credential 都当成平台资源管理。

---

# 2. 项目解决什么问题

项目重点解决 4 类企业 Agent 落地问题。

## 2.1 Agent 能力孤岛

如果分别写 Data Agent、RAG Agent、Ops Agent，很容易变成三个互相独立的 Demo。

因此平台抽出了：

- 统一 LLM Runtime
- Tool Policy
- RBAC
- Approval
- Runs
- Trace
- Eval
- Metrics
- Request Context

业务 Agent 只关心自己的领域能力。

---

## 2.2 LLM 不可靠

LLM 输出不能作为安全边界。

因此：

- SQL 必须经过 SQL Guard；
- 数据库推荐使用独立只读账号；
- Ops 不接受任意 Shell；
- 高风险 Tool 必须审批；
- Tool 参数来自服务端约束，而不是直接执行模型文本；
- Agent 失败会进入 Trace 和 Eval。

---

## 2.3 高风险动作不能自动化裸奔

系统把 Tool 按：

- Agent
- Read / Write
- Risk
- Approval Required

统一注册。

高风险写操作执行链路是：

```text
Operator 创建审批
        ↓
Approver/Admin 审批
        ↓
Approval 绑定 Agent + Tool + Target
        ↓
执行时校验
        ↓
单次消费 consumed
        ↓
执行 allowlisted action
```

这样即使模型被 Prompt Injection，也不能绕过 Tool Policy 和 Approval。

---

## 2.4 Agent 出错以后必须可观测

每次请求会生成：

- Request ID
- Correlation ID

每次 Agent 执行形成 Run：

- Agent 类型
- Status
- Duration
- Trace
- Error Type
- Request ID
- Correlation ID

再聚合：

- Success Rate
- P50
- P95
- Error Types
- Eval Score
- Eval Pass Rate

并提供 Prometheus 文本出口。

---

# 3. 技术栈

## Backend

- Python 3.11
- FastAPI
- Pydantic
- SQLAlchemy
- SQLite
- PostgreSQL / Kingbase compatible datasource
- httpx

## AI / Agent

- OpenAI-compatible Chat Completions
- OpenAI-compatible Embeddings
- Multi-Agent orchestration
- RAG
- Deterministic Eval
- Fake LLM regression testing

## Platform

- RBAC
- Session Authentication
- Bearer Token compatibility
- Tool Policy
- Human Approval
- Run / Trace
- Request / Correlation ID
- Structured JSON Logging
- Prometheus Metrics
- Rate Limiting
- Health / Readiness

## Frontend

当前演示 Console 采用：

- HTML
- CSS
- Vanilla JavaScript
- SVG Icon System

没有为了“企业级”强行引入 React/Vue。

原因是当前页面规模和状态复杂度还没有达到必须引框架的程度，先把信息架构、产品对象和交互模型设计正确。

## Engineering

- Docker
- Docker Compose
- GitHub Actions
- pytest
- pip-audit
- compileall
- 标准库压测脚本
- Cloudflare / Tunnel 域名暴露演示环境

---

# 4. 核心模块

# 4.1 Data Agent

执行链路：

```text
Question
   ↓
Schema Inspection
   ↓
LLM Generate SQL
   ↓
SQL Guard
   ↓
Database Readonly Query
   ↓
Result
   ↓
LLM Summary
   ↓
Chart / Report
```

关键能力：

- 多数据源
- Schema 自动感知
- SELECT / CTE 只读保护
- 最大结果集
- SQL Timeout
- SQL 自动纠错
- Trace
- 数值结果轻量图表
- Markdown Report

---

# 4.2 Knowledge Agent

执行链路：

```text
Question
   ↓
Role Scope Filter
   ↓
Embedding
   ↓
Similarity Search
   ↓
Top K Chunks
   ↓
LLM Answer
   ↓
Sources / Citations
```

当前实现：

- txt / md / csv / json / PDF / DOCX
- 文档分块
- Embedding
- SQLite Vector Storage
- O(n) Cosine Similarity
- Tags
- Version
- Allowed Roles
- RAG
- Source 返回
- 删除走审批

---

# 4.3 Ops Agent

只读证据：

- CPU
- Memory
- Swap
- Load Average
- Disk
- Server-side allowlisted log files
- Prometheus
- Docker containers
- Kubernetes Pods

写操作目前只提供：

- allowlisted systemd service restart

并且必须经过 Approval。

这里刻意没有实现：

```text
execute_shell("rm -rf ...")
```

因为任意 Shell 对 Agent 平台来说是非常危险的设计。

---

# 4.4 Supervisor

Supervisor 的作用不是“再加一个更聪明的 Agent”，而是负责跨领域调查。

例如用户问：

> 为什么最近导入任务失败？

执行：

```text
Supervisor
│
├── Ops Agent
│   └── 查看当前资源、日志、Prometheus
│
├── Knowledge Agent
│   └── 检索导入服务运维手册
│
├── Data Agent
│   └── 查询历史 import_jobs
│
└── Synthesize
    └── 汇总事实、证据、推测和建议
```

Supervisor 不直接绕过子 Agent 调 Tool。

---

# 5. 企业级平台能力

# 5.1 Authentication

现在 Web Console 支持独立登录页。

默认 Demo：

```text
demo / demo
```

登录后服务器生成随机 Session Token，通过 HttpOnly Cookie 保存。

同时仍保留 Bearer Token API 模式。

这样：

- 浏览器不需要持有 admin Bearer Token；
- API Client 仍可以使用 Bearer Token；
- 现有 RBAC 不需要重写。

---

# 5.2 RBAC

角色：

- user
- operator
- approver
- admin

例如：

- 普通 Agent 只读能力可以开放给 user；
- operator 可以发起审批；
- approver 可以审批；
- admin 拥有完整权限。

非 admin 默认不能审批自己发起的审批。

---

# 5.3 Tool Policy

Tool Policy 与 RBAC 分开。

RBAC：

> 谁能做？

Tool Policy：

> 这个 Tool 本身属于哪个 Agent？是读还是写？风险多高？是否需要审批？

这样安全规则不会散落在 Prompt 里。

---

# 5.4 Human Approval

Approval 绑定：

```text
Agent
Tool
Target
Requester
Approver
Executor
Status
```

Approval 单次消费。

例如审批：

```text
ops
service_restart
service:nginx
```

不能拿同一个 Approval 去重启别的服务。

---

# 5.5 Run / Trace

一个 Run 记录完整执行元信息。

Trace 记录：

- Tool step
- LLM step
- Error
- Detail

但当前默认不保存完整用户 Prompt 原文，目的是减少敏感数据留存。

---

# 5.6 Eval

没有把所有评测都交给 LLM Judge。

当前核心流程主要使用确定性 Eval。

例如检查：

- Run 是否成功；
- Trace 是否存在 Error；
- 关键步骤是否出现；
- Data Agent 是否经过 SQL；
- Knowledge 是否有 retrieval；
- Supervisor 是否完成子 Agent 调度。

优点：

- 可重复；
- 稳定；
- 成本为 0；
- 适合 CI。

---

# 5.7 Regression

Regression Suite 使用：

- 临时 SQLite
- Fake LLM
- 固定业务样本

CI 不需要真实 LLM Key，也不会访问生产数据库。

---

# 5.8 Observability

HTTP：

```text
X-Request-ID
X-Correlation-ID
```

Agent Run：

```text
request_id
correlation_id
agent
status
duration
trace
error_type
```

Metrics：

```text
runs
success_rate
P50
P95
error_types
eval_score
eval_pass_rate
```

---

# 6. 前端为什么也算项目亮点

这个项目前端经历过一次很典型的演进。

第一版实际上就是：

```text
Card
Textarea
Button
JSON
Table
```

功能存在，但看起来像 API Demo。

后来重新梳理了产品对象：

- Agents
- Knowledge
- Data Sources
- Runs
- Evaluations
- Approvals
- Integrations
- Credentials
- Policies
- Settings

全局导航不再直接展示：

```text
Data Agent
Knowledge Agent
Ops Agent
Supervisor
```

而是：

```text
Agents
   ↓
Agent Directory
   ↓
Agent Detail
```

Agent Detail 使用统一模板：

```text
Agent
├── Playground
├── Runs
├── Evaluations
└── Configuration
```

Run 使用 Dense Table + Inspector。

Supervisor 使用 Canvas + Inspector。

Settings 不再做成 `.env` 表单，而是把：

- Credentials
- Data Sources
- Integrations

作为独立资源。

这个过程本质上是把：

> “后端接口映射出来的 Web 页面”

变成：

> “有产品对象模型的 SaaS Console”。

---

# 7. 简历写法

## 精简版

**Enterprise Agent Platform｜企业级 Multi-Agent 平台**

- 设计并实现 Data / Knowledge / Ops 三类业务 Agent 与 Supervisor 跨 Agent 编排，覆盖 NL2SQL、RAG、运维诊断和故障调查。
- 构建统一 Tool Policy、RBAC 与 Human-in-the-loop Approval，高风险 Tool 采用目标绑定、单次消费授权，禁止模型直接执行任意 SQL / Shell。
- 实现 Run / Trace、Request ID / Correlation ID、结构化日志、确定性 Eval、Regression Suite、P50/P95 和 Prometheus Metrics，支持从 HTTP 请求追踪到 Agent 执行步骤。
- Data Agent 支持 Schema 感知、多数据源、只读 SQL Guard、失败自动纠错、结果总结与报告；Knowledge Agent 支持文档分块、Embedding、角色级检索权限与来源引用。
- Ops Agent 集成系统快照、日志、Prometheus、Docker/Kubernetes 只读诊断，并支持审批后白名单 systemd Service Restart。
- 使用 FastAPI、SQLAlchemy、OpenAI-compatible API、Docker、GitHub Actions；构建 Enterprise Web Console、Session 登录和资源化配置中心。

---

# 8. 推荐现场 Demo

面试演示不要一上来讲代码。

建议顺序：

## Step 1：登录

打开：

```text
https://agent.majhoon.site
```

登录：

```text
demo / demo
```

先让面试官看到这是一个平台。

---

## Step 2：Home

讲：

- Attention
- Agent Health
- Activity
- Runtime Metrics

告诉面试官：

> 我希望首页首先回答“什么需要处理”，而不是单纯放四个 KPI。

---

## Step 3：Agents

展示：

- Agent Directory
- Data Agent
- Knowledge Agent
- Ops Agent
- Supervisor

强调 Agent 是平台资源，不是左侧四个写死 Tab。

---

## Step 4：Supervisor

这是最推荐的 Demo。

跑 Offline Demo：

```text
为什么最近导入任务失败？
```

展示：

```text
Incident
   ↓
Supervisor
   ↓
Ops / Knowledge / Data
   ↓
Synthesis
```

再打开 Trace。

---

## Step 5：Runs

展示：

- Run
- Request ID
- Correlation ID
- Duration
- Trace
- Eval

这里最容易体现“工程化”。

---

## Step 6：Approval

展示：

- pending
- approve
- consumed

解释：

> 高风险能力不是让模型决定要不要执行，而是平台强制审批。

---

# 9. 高频面试题与参考回答

---

## 第一组：项目整体设计

### Q1：为什么要做 Multi-Agent，而不是一个大 Agent？

因为 Data、Knowledge、Ops 的工具边界完全不同。

Data 需要数据库 Schema 和 SQL Guard；Knowledge 需要检索和文档权限；Ops 需要日志、Prometheus 和系统工具。

如果全部塞进一个 Agent：

- Prompt 会越来越大；
- Tool 数量过多；
- 安全边界不清晰；
- 权限难隔离；
- Eval 难定义；
- 故障难定位。

因此我按领域拆 Agent，再由 Supervisor 在真正跨领域的场景里编排。

---

### Q2：为什么还需要 Supervisor？

Supervisor 解决的是跨领域任务。

例如“导入为什么失败”，单看数据库、日志或者知识库都不够。

Supervisor 不复制子 Agent 能力，只负责：

- delegation；
- failure isolation；
- evidence synthesis。

---

### Q3：为什么 Supervisor 不直接调用所有 Tool？

因为那会破坏 Agent 边界。

如果 Supervisor 可以直接调 SQL、Shell、Knowledge Store，那么：

- 子 Agent 的 Tool Policy 被绕过；
- 权限逻辑重复；
- 审计边界变模糊。

所以 Supervisor 调 Agent，Agent 再调自己的 Tool。

---

### Q4：你这个项目和普通 Chatbot 最大区别是什么？

Chatbot 主要关注回答。

这个项目重点关注：

- 工具权限；
- 高风险动作；
- 审计；
- Trace；
- Eval；
- Regression；
- 多 Agent；
- Data/RAG/Ops 资源；
- 企业控制台。

核心不是“聊天”，而是 Agent Execution Platform。

---

### Q5：如果让你重新做一次，最先设计什么？

先设计：

1. 产品对象；
2. Agent 边界；
3. Tool 边界；
4. 权限模型；
5. Run / Trace 数据模型；

而不是先写 Prompt。

---

## 第二组：Agent / LLM

### Q6：LLM 在系统中到底负责什么？

LLM 主要负责不确定性高、规则难穷举的部分：

- 自然语言理解；
- SQL 候选生成；
- 查询结果总结；
- RAG 回答；
- 运维证据总结；
- 多 Agent 证据综合。

安全、权限、执行边界不交给 LLM。

---

### Q7：为什么说 Prompt 不是安全边界？

Prompt 可以被：

- Prompt Injection；
- 用户输入干扰；
- 模型幻觉；
- 上下文污染；

因此真正安全边界必须在程序层。

例如 SQL Guard、Tool Policy、RBAC、Approval、allowlist。

---

### Q8：模型调用失败怎么处理？

当前模型请求有 Timeout，Agent 失败会：

- Run 标记 error；
- Trace 保存失败阶段；
- error_type 入库；
- HTTP 返回统一错误；
- Metrics 会统计失败率和错误类型。

Data SQL 生成失败还有有限次数纠错重试。

---

### Q9：为什么支持 OpenAI-compatible API？

为了避免系统绑定单一模型厂商。

只要实现兼容：

- Chat Completions；
- Embeddings；

就能接云模型或兼容的本地模型服务。

---

### Q10：Chat Model 和 Embedding Model 为什么分开？

两者任务不同。

Chat 用于生成和推理。

Embedding 用于把文本映射到向量空间。

企业部署中经常会分别选择不同模型。

---

### Q11：为什么没有直接上 LangChain / LangGraph？

项目目前核心需求不需要它们。

我希望 Agent 的 Tool Boundary、Run、Trace、Approval 等机制都能直接看懂，不被框架抽象隐藏。

如果未来 Workflow 复杂到需要持久化状态机、暂停恢复、并行图调度，再考虑引入 LangGraph。

---

## 第三组：Data Agent

### Q12：如何防止模型执行 DROP / DELETE？

两层。

第一层：

SQL Guard 只接受 SELECT / CTE 只读查询。

第二层：

生产数据库使用真正只读账号。

应用层 Guard 不能替代数据库权限。

---

### Q13：SQL Guard 是不是绝对安全？

不是。

任何 SQL Parser/Guard 都不能替代数据库最小权限。

Guard 是减少风险和错误的一层。

真正最终边界应该是：

- read-only DB user；
- network isolation；
- statement timeout；
- row limit。

---

### Q14：模型生成错误 SQL 怎么办？

Data Agent 会把：

- SQL；
- SQL Guard Error；
- DB Execution Error；

反馈给模型，再生成修正版。

次数受 `agent_max_attempts` 限制，防止无限循环。

每次尝试进入 Trace。

---

### Q15：为什么需要 Schema Inspection？

没有 Schema，模型只能猜：

- 表名；
- 列名；
- 类型；
- 关系。

Schema Inspection 会提高 SQL 命中率，并减少幻觉。

---

### Q16：多数据库怎么支持？

Data Source 抽象使用 SQLAlchemy URL + Schema。

Agent 不直接绑定某个数据库。

目前重点支持：

- SQLite；
- PostgreSQL；
- Kingbase 兼容场景。

---

### Q17：怎么限制大查询？

目前主要通过：

- SQL 最大返回行数；
- Statement Timeout；
- 只读 SQL；
- 数据源只读权限。

生产还可以继续加：

- Query Cost；
- Resource Group；
- Warehouse 限额；
- API Gateway Timeout。

---

## 第四组：Knowledge / RAG

### Q18：RAG 基本流程是什么？

```text
Question
→ Embedding
→ Similarity Search
→ Top K
→ Context
→ LLM
→ Answer + Sources
```

---

### Q19：为什么现在不用向量数据库？

因为当前数据规模较小。

SQLite 保存 Embedding + 进程内 O(n) 余弦扫描：

- 简单；
- 易测试；
- 无额外依赖；
- 对 Demo 足够。

只有当数据量和 P95 真正成为问题，再迁 pgvector 或托管向量数据库。

---

### Q20：O(n) 搜索规模大了怎么办？

迁到：

- pgvector HNSW / IVFFlat；
- Vector DB；

接口层保持不变，只替换 Knowledge Store 实现。

---

### Q21：Knowledge 权限怎么做？

文档保存 `allowed_roles`。

检索前会按当前用户角色过滤。

不是先检索所有内容再在回答后删除，而是检索阶段就限制可见范围。

---

### Q22：如何避免 RAG 泄露用户无权访问文档？

关键是 ACL Filtering 必须发生在 retrieval 前。

生产多租户还要扩展：

- tenant_id；
- user_id；
- department_id；
- ACL predicate。

---

### Q23：为什么返回 Sources？

企业知识问答需要可验证。

用户应该能够知道：

- 答案根据什么；
- 来源是什么；
- 检索到哪些文档。

来源也是降低幻觉风险的一种手段。

---

## 第五组：Ops / 安全

### Q24：为什么 Ops Agent 不支持任意 Shell？

因为风险太高。

LLM 输出不可直接进入 shell。

当前只提供：

- fixed system snapshot；
- server-side configured logs；
- Prometheus；
- docker ps；
- kubectl get pods；
- allowlisted service restart。

---

### Q25：Docker / Kubernetes 为什么只读？

因为项目当前目标是诊断平台。

`docker ps` 和 `kubectl get pods` 可以提供证据，但不会改变运行环境。

真正写动作必须另外建 Tool 并进入 Approval。

---

### Q26：服务重启如何防止参数注入？

客户端只能传 service name。

服务器还会检查：

```text
OPS_ALLOWED_SERVICES
```

最终命令参数是结构化列表，不通过 shell 字符串拼接执行。

---

### Q27：为什么还需要 Approval？

Allowlist 只能说明这个动作“允许存在”。

Approval 解决的是：

> 这一次是否应该执行？

两者不是同一个问题。

---

## 第六组：Human Approval / Tool Policy

### Q28：Tool Policy 怎么设计？

每个 Tool 注册：

- name；
- agent；
- mode；
- risk；
- approval_required。

Agent 调用 Tool 前统一校验。

---

### Q29：Tool Policy 和 RBAC 有什么区别？

RBAC 是用户身份权限。

Tool Policy 是 Agent 能力边界。

例如：

```text
admin
```

权限很高，但 `service_restart` 仍然是 High Risk Tool。

它仍可以被平台要求审批。

---

### Q30：Approval 为什么绑定 Target？

为了防止授权扩大。

审批：

```text
document:7
```

不能用于删除：

```text
document:8
```

---

### Q31：为什么 Approval 只能用一次？

防止 Replay。

审批通过后执行一次，状态进入：

```text
consumed
```

再次使用会被拒绝。

---

### Q32：Prompt Injection 能不能让模型创建审批？

模型本身不能绕过 API 权限。

创建审批需要经过当前认证身份和 RBAC。

即使模型建议某动作，真正审批仍由平台和用户完成。

---

## 第七组：Supervisor / Multi-Agent

### Q33：三个 Agent 是串行还是并行？

当前 Supervisor 是串行。

这是刻意设计的。

原因是：

- 实现简单；
- Trace 顺序清晰；
- Demo 稳定；
- 当前延迟还没有证明并行化必要。

如果实际 P95 显示三个 Agent 的等待是主要瓶颈，再并行。

---

### Q34：某个子 Agent 失败怎么办？

Supervisor 保存失败 Finding 和 Error Trace。

只要还有可用证据，就继续综合。

只有全部子 Agent 失败时才整体失败。

---

### Q35：为什么不让一个 Agent 调另一个 Agent 的 Tool？

会导致安全边界混乱。

更合理的是：

```text
Supervisor
   ↓
Agent
   ↓
Agent-owned Tools
```

---

### Q36：如何防止 Supervisor 无限循环调用？

当前编排是固定有限流程，不存在模型自由递归。

如果未来做动态 Planner，需要：

- max steps；
- max depth；
- budget；
- timeout；
- loop detection。

---

## 第八组：Run / Trace / Observability

### Q37：Run 和 Trace 区别？

Run 是一次 Agent 执行的聚合对象。

Trace 是 Run 内部步骤。

例如：

```text
Run #123
├── schema
├── generate_sql
├── sql_guard
├── query
└── summarize
```

---

### Q38：Request ID 和 Correlation ID 区别？

Request ID：

每一个 HTTP 请求唯一。

Correlation ID：

用于关联多个请求或跨服务链路。

例如一次前端动作可能触发多个服务调用，Correlation ID 可以把它们串起来。

---

### Q39：为什么要把 Request ID 写进 Run？

这样用户反馈：

> 这个请求报错了，Request ID 是 xxx。

运维可以直接查到对应 Agent Run 和 Trace。

---

### Q40：为什么不保存所有 Prompt？

企业系统中 Prompt 可能包含：

- 业务数据；
- 用户隐私；
- 凭据；
- 敏感字段。

默认全量落库不是最佳选择。

当前只保留执行元信息。

生产可增加：

- retention；
- masking；
- configurable prompt logging。

---

### Q41：Prometheus 暴露哪些指标？

当前主要包括：

- runs_total；
- success_ratio；
- duration P50/P95；
- eval score；
- eval pass ratio；
- error type count。

---

## 第九组：Eval / Testing

### Q42：为什么不用 LLM Judge 作为唯一评测？

LLM Judge：

- 有成本；
- 有随机性；
- 自身也可能误判；
- CI 不够稳定。

核心流程更适合确定性 Eval。

---

### Q43：确定性 Eval 能测自然语言质量吗？

不能完全测。

它更适合测试：

- 关键步骤；
- Tool 调用；
- Trace Error；
- Run Status。

自然语言质量未来可以增加 LLM Judge 或人工评测。

---

### Q44：如何在没有 API Key 的 CI 中测试 Agent？

Fake LLM + 固定输入输出。

Regression 使用临时数据库和固定知识库。

所以 CI 完全离线。

---

### Q45：为什么测试里不用真实模型？

真实模型：

- 不稳定；
- 慢；
- 花钱；
- 输出变化；
- CI 可能没有网络。

单测应该验证程序逻辑，不应该依赖外部模型随机性。

---

## 第十组：Authentication / Backend

### Q46：现在 Web 登录怎么做？

登录接口校验 Console Username / Password。

成功后生成随机 Session Token。

Session Token 通过：

```text
HttpOnly Cookie
SameSite=Lax
```

保存。

浏览器不需要保存 admin Bearer Token。

---

### Q47：为什么仍保留 Bearer Token？

因为 API Client、脚本、自动化程序更适合 Bearer Token。

Web Console 和 API Client 是不同使用场景。

---

### Q48：Session 存在哪里？

当前是进程内。

这适合单实例 Demo。

多副本生产需要迁到：

- Redis；
- Database；
- 或直接采用 OIDC/JWT。

---

### Q49：生产还会用 demo/demo 吗？

不会。

这是演示环境默认账号。

生产应该：

- 修改或关闭 Console Demo Credential；
- 对接企业 IdP / OIDC；
- 开启更严格 Session 策略；
- 配合 Secret Manager。

---

### Q50：Rate Limit 怎么做？

当前是单进程、客户端 IP 级轻量限流。

适合单实例 Demo。

多副本环境应迁到：

- API Gateway；
- Redis；
- Cloudflare / Ingress。

---

## 第十一组：Frontend / 产品设计

### Q51：为什么没有直接用 React？

当前前端规模还没有证明需要 React。

如果只是为了“企业级”而引 React，会增加：

- build；
- dependency；
- deployment；
- bundle；
- state complexity。

当前先通过信息架构和统一页面模型解决产品问题。

---

### Q52：什么时候你会迁 React/Vue？

当出现：

- 大量复用组件；
- 复杂跨页面状态；
- 多人前端协作；
- 大量交互式图形；
- 实时更新；
- 页面数量继续显著增长；

再迁框架会更合理。

---

### Q53：为什么第一版 UI 看起来像 Demo？

因为第一版是按照 Backend Capability 映射页面：

```text
接口
→ 表单
→ Button
→ JSON
```

后来改成 Product Object：

```text
Agent
Run
Approval
Credential
Integration
Data Source
```

UI 才真正像平台。

---

### Q54：Home 为什么不用传统四个 KPI Card？

企业运行平台首页更重要的是：

> 什么需要我处理？

所以当前优先：

- Attention；
- Degraded Agent；
- Pending Approval；
- Missing Configuration；
- Recent Activity。

指标放后面。

---

### Q55：为什么 Agent 不直接放 Sidebar？

因为 Agent 数量是动态资源。

今天 4 个，未来可能 40 个。

应该是：

```text
Agents
  ↓
Directory
  ↓
Detail
```

而不是让 Sidebar 无限增长。

---

## 第十二组：Deployment / Production

### Q56：项目怎么部署？

本地：

```bash
docker compose up --build
```

线上 Demo 目前通过服务器运行 FastAPI，再由域名：

```text
https://agent.majhoon.site
```

对外提供访问。

---

### Q57：Health Check 怎么设计？

Liveness：

只证明进程活着。

Readiness：

检查：

- database；
- platform store；
- knowledge store。

依赖异常时 readiness 返回 503。

---

### Q58：为什么区分 Liveness 和 Readiness？

进程活着不代表能接请求。

例如数据库挂了：

- liveness 仍应该成功；
- readiness 应该失败；

这样容器编排不会因为外部依赖短暂异常疯狂重启进程。

---

### Q59：如果要真正上生产，第一步升级什么？

优先级：

1. OIDC / Enterprise IdP；
2. PostgreSQL 持久化 Run / Approval / Session；
3. Secret Manager；
4. Multi-tenant；
5. Redis / Gateway Rate Limit；
6. pgvector；
7. Alerting；
8. Trace Retention / Masking；
9. Worker Queue / Async Execution。

---

### Q60：最大的技术债是什么？

当前 Demo 主要技术债：

- Session 是进程内；
- Runs/Approvals 使用 SQLite；
- Embedding 搜索 O(n)；
- Supervisor 串行；
- UI 尚未组件框架化；
- 单机演示部署。

这些都是明确的规模升级点，而不是当前必须提前解决的问题。

---

# 10. 面试官可能继续追问的高级问题

### Q61：如果同时 1000 个 Agent Run 怎么办？

当前同步请求模式需要升级。

可以：

```text
API
 ↓
Task Queue
 ↓
Worker
 ↓
Agent Run State
 ↓
WebSocket/SSE
 ↓
Frontend
```

并将 Run 状态迁 PostgreSQL/Redis。

---

### Q62：Agent Run 如何实现 Cancel？

Run 需要有：

- cancellation token；
- task id；
- worker cooperative cancellation；
- tool timeout；
- external request cancellation。

当前同步 Demo 还没有实现完整 Cancel。

---

### Q63：多租户怎么做？

每个关键数据对象增加 tenant_id：

- Knowledge Document；
- Run；
- Approval；
- Credential；
- Data Source。

所有查询自动带 tenant scope。

数据库连接和 Credential 也不能跨 tenant。

---

### Q64：Prompt Injection 怎么系统防御？

分层：

1. 输入层：识别明显注入；
2. Context：区分系统指令和业务数据；
3. Tool Policy：真正安全边界；
4. RBAC；
5. Approval；
6. Output Validation；
7. Network / DB 最小权限；
8. Audit。

不能依赖“告诉模型不要听坏指令”。

---

### Q65：如何控制 Agent 成本？

可以按 Run 记录：

- prompt tokens；
- completion tokens；
- embedding tokens；
- model；
- tool calls；
- duration；
- cost。

再做：

- budget；
- per-user quota；
- per-agent quota；
- model routing；
- cache。

当前项目主要记录运行质量和时延，成本治理是下一阶段。

---

# 11. 面试时最值得强调的 5 个点

不要把重点放在：

> 我会调 OpenAI API。

应该强调：

## 1. 安全边界

```text
Prompt != Security Boundary
```

Tool Policy + DB Permission + Approval 才是。

## 2. Agent 工程化

```text
Run
Trace
Eval
Regression
Metrics
```

## 3. 多 Agent 不是为了多 Agent

只有存在真正跨领域任务时才引 Supervisor。

## 4. Human-in-the-loop

高风险操作必须由系统层控制，不让模型自己决定。

## 5. 产品化

从 API Demo 演进成：

```text
Agent Control Plane
```

不仅能跑，还能配置、审计、观察、审批、回归和演示。

---

# 12. 面试中容易踩的坑

## 不要说

> 这是一个完全生产级的平台。

更准确：

> 当前已经实现企业 Agent 平台的核心工程机制，并刻意保留了一些适合 Demo/单机阶段的简单实现，同时给出了明确生产升级路径。

---

## 不要说

> SQL Guard 能完全保证数据库安全。

应该说：

> SQL Guard 是应用层第二道防线，数据库只读账号才是最终权限边界。

---

## 不要说

> RAG 不会幻觉。

应该说：

> RAG 能提供更可靠的企业上下文和来源，但仍需要来源验证、权限过滤和必要的回答约束。

---

## 不要说

> Multi-Agent 一定比单 Agent 好。

应该说：

> 当 Tool、权限和领域边界明显不同，并且确实存在跨领域任务时，Multi-Agent 才有价值。

---

# 13. 项目不足与升级路线

当前版本刻意保持了一些简化：

| 当前方案 | 原因 | 生产升级 |
| --- | --- | --- |
| SQLite Run / Approval | 自包含 Demo | PostgreSQL |
| O(n) Vector Search | 小规模知识库 | pgvector |
| In-memory Session | 单实例 Demo | OIDC / Redis |
| Supervisor 串行 | 简单、可追踪 | 有指标后并行 |
| Static Allowlist | 安全简单 | Policy Service |
| Vanilla Frontend | 当前规模足够 | 复杂度上升后 React/Vue |
| 单机 Demo | 展示方便 | K8s / autoscaling |
| 单进程 Rate Limit | 简单 | Gateway / Redis |

---

# 14. 一句话总结

如果面试最后只让讲一句话：

> 我做的不是一个“会调用 LLM 的 Demo”，而是一套围绕 Agent 执行、安全、治理、可观测、评测和多 Agent 协作设计的企业级 Agent Control Plane；重点解决的是模型能力进入真实系统以后，如何安全、可控、可审计、可回归地运行。
