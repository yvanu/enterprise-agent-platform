# 开发进度与验收台账

> 最后核对：**2026-10-08** · 本地工作区 `main` · MCP/OpenAPI 功能提交：`bd5fe6f` · **73 项自动化测试通过、0 失败、1 条依赖弃用警告**。

此页记录 **代码实现状态**，不将模拟接口测试、仓库提交或本地构建等同于线上部署验收。

## 里程碑

| 阶段 | 状态 | 已实现的范围 |
| --- | --- | --- |
| M0 / v0.1 基础 Multi-Agent | ✅ 已完成 | Data / Knowledge / Ops / Supervisor、RBAC、审批、Run/Trace、控制台 |
| M1 / Dynamic Agent Platform | ✅ 已完成 | Agent CRUD、不可变 Version、Publish / Rollback、Built-in 迁移 |
| M2 / Tool Platform | ✅ 已完成 | Tool Registry、Agent Version Assignment、Policy、控制台 |
| M2.5 / MCP + OpenAPI | ✅ 基础代码完成 | MCP Streamable HTTP、OpenAPI 3.x JSON GET/POST、工具发现/导入、Generic Agent Function Calling、参数级审批/恢复 |
| M2.5 真实服务验收 | ◻ 待完成 | 真实 MCP Server、企业 REST、身份凭证、网络/超时和幂等验收 |
| M3 / Async Runtime | ◻ 未开始 | Durable Run、队列/Worker、SSE、取消/重试、异步审批恢复 |
| M4+ / 深度平台化 | ◻ 规划中 | Span/Token/Cost、评测平台、Knowledge/Credential、租户与 OIDC |

## 2026-10-08 本轮交付

- 管理员注册被服务端精确 URL allowlist 允许的 MCP Server，通过 `tools/list` 导入工具。
- 管理员上传 **OpenAPI 3.x JSON**，导入限定 GET/POST JSON 操作；只允许事先配置的 API base URL。
- 远程工具进入同一 Tool Registry，按 **Agent 已发布版本**绑定；工具默认高风险写操作，必须人工审批。
- Generic Agent 用 Function Calling 生成**具体 JSON 参数**的操作提案，Run 记录为 `waiting_approval`，此时**不会访问外部工具**。
- 审批绑定 `Agent ID + Version + Tool ID + 具体参数`；批准后使用冻结参数恢复执行。跨 Agent、版本变更、参数篡改及重放均拒绝。
- Web Console：MCP Server 管理、OpenAPI JSON 导入、Tool Assignment、审批参数查看及手动恢复。
- 引入 Alembic 迁移 `20261008_0003`、`20261008_0004`；已检查迁移链正确，但不代表已在生产数据库执行。
- 文档参考：[架构](/ARCHITECTURE)、[运行时](/agent-runtime)、[安全](/security)、[数据模型](/data-model)、[MCP 接入](/mcp-integration)、[OpenAPI 接入](/openapi-integration)。

## 验证证据

| 检查项 | 结果 |
| --- | --- |
| `.venv/bin/python -m pytest -q` | ✅ 73 passed |
| `node --check app/static/app.js` | ✅ 通过 |
| `.venv/bin/python -m compileall -q app` | ✅ 通过 |
| `.venv/bin/alembic history` | ✅ 识别 0003 → 0004 (head) |
| `git diff --check` | ✅ 通过 |
| MCP / REST 模拟联调 | ✅ `httpx.MockTransport` 测试通过 |
| 真实远端 MCP / REST 服务 | ⚪ 尚未验证 |
| 线上构建、数据库迁移及部署 | ⚪ 尚未验证 |

## 已知限制和上线门槛

1. **尚无真实异步任务运行时。** 当前同步请求方式会受到 HTTP 超时影响；`waiting_approval` 属于审批提案记录，不等于可恢复的持久化执行上下文。
2. **审批消费发生在远端请求之前**，以防重复执行；如果外部 API 已处理请求但响应超时，不能盲目重试，需要接入幂等键与人工对账机制。
3. **首版没有远端认证凭证管理。** MCP/OpenAPI 只能连接被信任、已允许的端点；生产需额外网络出口隔离和安全审计。
4. OpenAPI 目前仅支持有限 GET/POST JSON、简单 path/query 参数；不支持 OAuth、`$ref`、YAML、文件上传等。
5. 自动化通过不证明线上可用；需要真实服务联调、负载/异常测试、迁移演练以及部署验证。

## 下一步：M3 异步运行时

优先顺序：建立持续化 Run / Run Event 状态机 → 单 Worker 队列执行 → 任务状态查询 → SSE 事件推送 → 取消与超时 → 失败重试、幂等及审批暂停/恢复的持久化整合。保持小规模可验证后再决定是否引入 Redis/Celery。

**Git 说明：** 功能代码对应提交 `bd5fe6f`，路线图和进度台账由独立文档提交维护。原有未跟踪的 `deploy/` 目录不纳入本轮提交。推送代码不代表生产数据库迁移或线上部署成功。
