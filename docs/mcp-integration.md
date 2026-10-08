# MCP 工具接入（M2.5 第一阶段）

本阶段支持 MCP Streamable HTTP 服务器的工具发现、受控调用，以及 **Generic Agent 使用 OpenAI-compatible function calling 自主选择已分配的 MCP 工具**。暂不支持 stdio、OAuth、持久会话恢复（OpenAPI 工具通过独立接口导入，详见 [OpenAPI 文档](openapi-integration.md)）及内置 Data/Knowledge/Ops Agent 的通用动态工具循环。

## 管理员配置

1. 在服务端环境变量 `MCP_ALLOWED_URLS` 中以逗号分隔设置批准的 MCP 端点完整 URL，例如 `https://trusted.example.com/mcp`。默认为空，即禁止新增远端端点；生产环境只允许 HTTPS。务必只批准可信任、受运维控制的服务，切勿将此值交给普通用户修改。
2. 运行 `alembic upgrade head` 创建 `mcp_servers` 表，重启服务。
3. 管理员调用 `POST /api/v1/mcp/servers`，JSON 为 `{"name":"Trusted","url":"https://trusted.example.com/mcp"}`。
4. 管理员调用 `POST /api/v1/mcp/servers/{server_id}/discover` 将工具注册到 Tool Registry。所有新发现的 MCP 工具默认视为高风险写操作，必须获得人工审批。远端 `readOnlyHint` 不会降低风险等级。重新发现时，远端已移除的工具将被停用。
5. 在 Agent 的 **Draft Version** 上通过 `PUT /api/v1/agents/{agent_id}/versions/{version}/tools` 分配工具，然后发布该版本；已发布版本不能直接修改绑定。
6. 在 Web Console 的 Tools 页面管理 MCP Server；Agent 详情的 Configuration 中绑定工具并发布。Generic Agent Playground 首次运行会由模型提出**一个未执行的具体工具操作**，返回 `pending_tools`，同时将 Run 记录为 `waiting_approval`。
7. 在 Playground 审核提案的完整 JSON 参数，点击 Request approval。等 Approvals 页面审查员确认参数和 Agent 后批准，返回 Playground 点击 Resume。恢复接口 `POST /api/v1/agents/{agent_id}/approvals/{approval_id}/resume` 接收 `{"input":"原始问题"}`，使用已批准且**冻结的参数**调用 MCP，不会重新让模型选择执行参数；执行结果返回前端，Run/Trace 记录会持久化；审批表保存冻结参数。页面重新加载后仍能找回最近的待批准/已批准记录。
8. API 调用方也可使用 `POST /api/v1/platform/approvals`，提交 `{"agent":"mcp.<server_uuid>","tool":"lookup","target":"tool:<tool_uuid>","arguments":{"q":"hello"},"agent_id":"<agent_uuid>","agent_version":2}`。只有已分配到该发布版本的工具才能创建审批。批准后可直接调用 `POST /api/v1/agents/{agent_id}/tools/{tool_id}/invoke`，JSON 为 `{"arguments":{"q":"hello"},"approval_id":1}`。任意参数差异、Agent ID/Version 差异及审批重放都被拒绝。
9. 通用 Agent 仍可通过 `/api/v1/agents/{agent_id}/run` 和 `approval_ids` 实现带审批的工具循环，但更推荐“提案 → 人审 → 确定性恢复”路径。每次模型返回最多一个待执行 MCP Tool 操作，多操作应拆成多次提案。

发现与调用都会检查精确 URL 允许列表；跨地址重定向不会被跟随。Tool Assignment / Tool Policy / Approval 全部由后端校验，调用结果形成平台 Run / Trace。

## 限制和上线前事项

- 只能连接可信服务器，不能将外部用户提交的地址自动加入 `MCP_ALLOWED_URLS`。网络安全组仍应限制容器的出站访问，精确 URL allowlist 并不等于网络隔离。
- 当前不支持 MCP 认证凭证管理；需要鉴权的 MCP Server 应先通过可信的网关对接，后续再增加集中式 Credential Vault。
- 远端工具定义、响应内容都视为不可信，不能以 MCP 注解作为审批豁免依据。
- Generic Agent 可以自动选择 MCP Tool，但仍是同步调用，且必须由 operator/admin 提供一次性审批编号。内置 Agent 还未接入此工具循环。
- MCP 审批已同时绑定 Tool ID、完整 JSON 参数、Agent ID 和 Agent Version；恢复执行以已审批的参数为唯一执行依据。审批仍是一次性使用，远端操作**成功与否**都消耗审批，以防超时重试造成重复副作用。
- 当前只有 **单步 MCP 提案/恢复**，尚不支持跨多个工具调用的持久化工作流，也不支持持久化完整 LLM 上下文。恢复后用用户问题和工具结果进行总结；对复杂工作流需要后续异步状态机。
- 不要将高危工具连接到不可信服务；真实生产联调、审计与超时恢复策略仍待验证。
- 建议在测试环境执行真实 MCP Server 的连接、断线、超时与审批重放验收，当前自动化测试通过 `httpx.MockTransport` 模拟远端。
