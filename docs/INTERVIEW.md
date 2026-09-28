# Enterprise Agent Platform：简历与面试说明

## 一句话项目介绍

面向企业数据分析、知识检索和运维诊断场景的 Multi-Agent 平台，包含 Data / Knowledge / Ops 三个业务 Agent 与一个只读 Supervisor，并统一实现 Auth/RBAC、Tool Policy、Human Approval、Run/Trace、Eval、Regression、Prometheus Metrics 和 CI/CD。

## 简历描述参考

**Enterprise Agent Platform — 企业级多 Agent 平台**

- 设计并实现 Data、Knowledge、Ops 三类业务 Agent：自然语言 SQL 分析、RAG 知识问答、系统/日志/Prometheus 运维诊断。
- 设计 Tool Policy 与 Human-in-the-loop：按 Tool 风险等级控制读写能力，高风险操作绑定审批目标并单次消费授权，禁止任意 Shell 和任意写 SQL。
- 实现 Bearer Token + RBAC，区分 user/operator/approver/admin，并记录审批申请人、审批人、执行人。
- 构建 Agent Run/Trace、确定性 Eval、离线 Regression Suite、P50/P95 和 Prometheus 指标，支持失败链路定位和质量回归。
- 实现真实 Supervisor 故障调查链路：Ops 获取运行证据、Knowledge 检索运维手册、Data 查询历史数据，最后综合结论，子 Agent 局部失败时支持降级。
- 使用 FastAPI、SQLAlchemy、SQLite/PostgreSQL/Kingbase、OpenAI-compatible API；提供 Docker Compose、GitHub Actions、pip-audit 和标准库压测脚本。

## 5 分钟演示路径

### 1. 离线 Multi-Agent Demo

不需要 LLM Key，也不会访问生产数据库：

```bash
python scripts/demo_incident.py
```

演示场景：

> 为什么最近导入任务失败？请结合当前运维状态、知识库手册和历史数据给出排查结论。

执行链路：

```text
Supervisor
├── Ops Agent       -> 发现上游请求 timeout 日志
├── Knowledge Agent -> 命中导入服务运维手册
├── Data Agent      -> 查询历史 import_jobs
└── Synthesize      -> 综合证据和下一步排查建议
```

### 2. Web/API Demo

```bash
cp .env.example .env
docker compose up --build
```

打开：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`

推荐依次演示：Data Agent → Knowledge 权限过滤 → Run/Trace/Eval → Human Approval → Supervisor。

## 核心设计取舍

### 为什么不让 LLM 直接执行 SQL？

LLM 只负责生成候选 SQL，所有查询必须经过 SQL Guard，并且生产数据库还应使用数据库层只读账号。应用层校验是第二道防线，不替代数据库权限。

### 为什么 Tool Policy 与 RBAC 分开？

RBAC 决定“谁能调用某类能力”；Tool Policy 决定“这个 Tool 自身允许什么、风险多高、是否需要审批”。两者解决的问题不同，组合后可以避免把安全逻辑散落在 Agent Prompt 里。

### 为什么审批授权只能用一次？

审批与具体 `Agent + Tool + Target` 绑定，并在执行时改为 `consumed`。这样批准删除 document:7 的审批不能拿去删除 document:8，也不能重复使用。

### 为什么 Knowledge Store 暂时不用向量数据库？

当前目标是可运行的面试项目和小规模知识库，SQLite + O(n) 余弦检索足够简单透明。只有数据量和延迟真正成为瓶颈时才替换 pgvector/Vectorize。

### 为什么 Supervisor 不是一开始就有？

先把三个业务 Agent 的边界、工具和安全机制做完整。只有出现真实跨 Agent 故障调查场景后才增加 Supervisor，避免提前设计一个没有业务价值的编排层。

### 为什么 Eval 不全部使用 LLM Judge？

关键流程使用确定性 Eval：检查 Run 状态、Trace 错误和关键步骤，结果稳定、零额外 token 成本。业务回归使用固定数据 + Fake LLM。需要评价自然语言质量时再补 LLM Judge。

## 常见面试问题

### 1. Agent 生成错误 SQL 怎么处理？

Data Agent 最多重试 `agent_max_attempts` 次。数据库或 SQL Guard 返回的错误会连同上一次 SQL 反馈给模型用于修复，每一次尝试都会进入 Trace。

### 2. 怎么防止提示注入让 Agent 执行危险命令？

Prompt 不是安全边界。真正边界在 Tool 层：Data 只有只读 SQL；Ops 只有固定参数的只读命令和白名单 systemd restart；高风险写 Tool 必须审批。

### 3. Supervisor 中一个子 Agent 失败怎么办？

保留失败 finding 和 Trace error，但只要至少一个子 Agent成功，就继续综合已有证据；全部失败才中止。这避免一个依赖不可用导致整条调查链路完全失效。

### 4. Knowledge 权限怎么实现？

文档块保存 `allowed_roles`，检索和文档目录在返回前根据当前认证角色过滤。它适合当前 RBAC 模型；更复杂企业场景可升级为 tenant/user/ACL 条件。

### 5. Agent 怎么做可观测性？

每次 Agent 调用生成 Run，记录 status、duration、trace、error_type；平台再聚合成功率、平均耗时、P50/P95、Eval 分和错误类型，并提供 Prometheus 文本出口。

### 6. 为什么 Run 不存用户问题原文？

当前版本刻意减少敏感信息留存，只保存执行元信息与 Trace。若企业需要完整审计，可增加可配置脱敏和保留策略，而不是默认把 Prompt 全量落库。

### 7. 如何扩展到更多数据库？

Data Source 由服务端配置 URL/schema，Database 层基于 SQLAlchemy。新增兼容 SQLAlchemy 的数据库通常不需要改 Agent，只需补驱动和特定方言限制测试。

### 8. 下一步如何上生产？

优先把静态 Bearer Token 换成企业 IdP/OIDC，把 SQLite 平台状态迁移 PostgreSQL，把知识检索迁移 pgvector，并加租户隔离、Secret 管理、限流和正式告警。
