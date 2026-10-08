# MCP / OpenAPI Mock 与真实服务联调

> 2026-10-08 · 低负载验收。**此页的 Mock 联调不等于真实第三方服务联调**：模拟服务使用本机回环 HTTP，LLM 使用固定答复，所有远程操作都由测试代码控制。

## 1. 已完成的真实 HTTP Mock 联调

代码：`tests/test_wire_mock_integration.py`。使用 Python 标准库 `ThreadingHTTPServer`，监听 `127.0.0.1:0` 自动分配的临时端口，并通过 **原生 HTTPX Client / TCP** 而不是 `httpx.MockTransport` 访问。测试结束自动关闭监听端口。

| 项目 | 验收点 |
| --- | --- |
| MCP 握手 | `initialize`、Session ID、`notifications/initialized` |
| MCP 工具发现 | `tools/list` 返回真实 `text/event-stream` / SSE；工具进入 Registry |
| MCP 调用 | Agent 发布版本绑定 → LLM 固定提案 → 参数级审批 → `tools/call`；仅批准后发包 |
| OpenAPI 导入 | 上传 OpenAPI 3.x JSON；GET Path / Query 与 POST JSON 分别发起真实 TCP 请求 |
| 授权与审计 | `waiting_approval` → 人工批准 → `ok`；审批前不执行、审批只消费一次 |
| 负面安全场景 | 服务端 HTTP 302 重定向不跟随；失败后的审批无法重放 |

Mock 的关键约束：本次测试 `APP_ENV=development`（仅测试进程，允许本机 HTTP）；临时 SQLite 保存 Agent、Tools、Approvals 和 Run；`mcp_allowed_urls`、`openapi_allowed_base_urls` 只包含临时的 `127.0.0.1` 端点；没有外部 AI 调用，没有真实第三方工具，也没有写入实际生产业务 API。

### 运行方式（推荐低负载）

```bash
# 在项目目录；仅一次单进程运行，最多 25 秒。
nice -n 15 timeout 25s .venv/bin/python -m pytest -q \
  tests/test_wire_mock_integration.py --disable-warnings
```

2026-10-08 实测：**3 passed**，峰值 RSS 约 111 MB，耗时约 3.7 秒。原有测试继续保留 `httpx.MockTransport` 以高效覆盖边界错误。Mock HTTP 服务不是长期运行的后台服务。

## 2. 对接真实外部 MCP 的联调步骤

1. **先确认目标：** 获取真实服务提供的 MCP Streamable HTTP URL、认证方案和工具列表说明；尽量使用带只读演示工具的测试实例，不要一开始直接连接生产写操作。
2. 运维核验域名及 TLS 证书，并把**完整 HTTPS URL** 加入服务器的 `MCP_ALLOWED_URLS` 白名单。禁止从用户上传的 URL 自动扩大白名单；服务端网络出口仍需访问控制。
3. 在 Tools → MCP Servers 管理页注册并点击 Discover，检查握手 `initialize`、SSE/JSON 响应、会话、工具名称/Schema 是否符合真实服务要求。发现工具必须先进入 Registry。
4. 创建 Agent Draft Version，明确分配一项低风险业务场景的远程工具并发布。当前实现仍将所有导入工具按**高风险写操作、必须审批**处理。
5. Playground 生成 `pending_tools` 提案，人工核对 Tool ID、Agent Version 和具体参数，批准后使用 Resume。检查外部服务返回值、Run/Trace、审批被消费，以及重复调用被拒绝。
6. 再测试真实环境的认证失败（401/403）、超时、SSE 分块、协议版本差异、错误响应、断网和幂等。当前未集成 OAuth / Credential Vault，需要先通过可信网关处理鉴权。

## 3. 对接真实 REST/OpenAPI 的联调步骤

1. 使用**测试环境**的 OpenAPI 3.x JSON（目前不支持 YAML、`$ref`、复杂 Header/Cookie 参数、文件上传、OAuth）。只导入一个 GET 或无副作用的测试 POST Operation。
2. 由运维核实域名/IP、HTTPS、测试账号和网络隔离；将实际可信根 URL 加入 `OPENAPI_ALLOWED_BASE_URLS`，不是直接信任规范中的 `servers` 字段。
3. 管理员在 Tools → OpenAPI Services 上传 JSON，检查 Tool Registry 的 Schema、路径变量、查询参数及工具权限。
4. 分配工具到 Agent Draft Version 后发布，使用 Playground 完成提案、人工审批和确定性恢复；对照 REST 服务器的请求日志验证只发起**一次**目标请求。
5. 使用测试环境验证 2xx、4xx、5xx、重定向、超时和限速边界。**写接口必须支持幂等请求或有可靠对账**：当前审批在发包前已消费，网络超时并不意味着远端未执行。

## 4. 本轮结论及生产限制

**已通过：** 在本机真实 TCP/HTTP Mock 服务上的 MCP 协议握手/SSE、OpenAPI GET/POST、Agent 提案、审批、恢复、Run/Trace 与不跟随重定向。

**未覆盖：** 第三方环境的真实 TLS/网络链路、真实认证凭证、真实 LLM 策略、真实高危操作及长时稳定性。只有在拿到可信测试端点并经批准后，才做真实远程联调。

参见：[MCP 接入](/mcp-integration)、[OpenAPI 接入](/openapi-integration)、[安全发布与验收](/deployment)、[开发进度](/PROGRESS)。
