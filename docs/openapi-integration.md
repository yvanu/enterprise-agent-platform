# OpenAPI 工具接入（M2.5 第一阶段）

## 管理与接入

1. 在服务端配置 `OPENAPI_ALLOWED_BASE_URLS=https://api.company.example/v1`；可以用逗号设置多个**完整**的可信 API 基础 URL。生产环境仅允许 HTTPS。此项只能由运维在部署环境设置，不能由普通平台用户修改。
2. 执行 `alembic upgrade head` 更新数据库，再重启 API 服务。
3. 登录管理控制台 → **Tools → OpenAPI services**，输入服务名称、已批准的基础 URL，选择 OpenAPI 3.x **JSON** 文件并导入。服务端**不会**从远端自动下载规范；`servers`、operation-level 服务器地址不会用于发起调用。
4. 导入的 Operation 直接进入 Tool Registry，默认设为 **write/high risk/approval required**，包括 GET；然后进入 Agent 详情 → Configuration，在新的 Draft Version 中绑定工具并发布。
5. Generic Agent Playground 提出一次具体工具调用后返回 `waiting_approval`、Tool ID 和完整 JSON 参数，**尚未调用远端**。在 Approvals 页面人工批准 Tool ID + Agent ID + Version + 完整参数，随后恢复执行。审批一次性消费，不自动重试具有潜在副作用的请求。Run/Trace 记录执行结果。

## API（operator/admin）

管理员导入：

```http
POST /api/v1/openapi/services
Content-Type: application/json

{
  "name": "Inventory",
  "base_url": "https://api.company.example/v1",
  "document": {
    "openapi": "3.0.3",
    "info": {"title": "Inventory", "version": "1"},
    "paths": {
      "/items/{item_id}": {
        "get": {
          "operationId": "get_item",
          "parameters": [{
            "name": "item_id", "in": "path", "required": true,
            "schema": {"type": "string"}
          }]
        }
      }
    }
  }
}
```

查看服务：`GET /api/v1/openapi/services`；查看自动注册的工具：`GET /api/v1/tools`。

模型提出的调用参数示例：`{"path":{"item_id":"A17"}}`。审批 API：

```http
POST /api/v1/platform/approvals
Content-Type: application/json

{
  "agent": "openapi.<service-uuid>",
  "tool": "get_item",
  "target": "tool:<tool-uuid>",
  "agent_id": "<agent-uuid>",
  "agent_version": 2,
  "arguments": {"path": {"item_id": "A17"}}
}
```

审批通过后可用统一恢复接口：`POST /api/v1/agents/{agent_id}/approvals/{approval_id}/resume`，请求体 `{"input":"原始问题"}`；或直接调用 `POST /api/v1/openapi/agents/{agent_id}/tools/{tool_id}/invoke`，请求体 `{"arguments":{"path":{"item_id":"A17"}},"approval_id":123}`。后者同样验证参数与版本绑定。

## 安全限制

- 首版支持 OpenAPI 3.x、最多 256KB 的 **JSON** 文档、最多 30 个 **GET/POST** 操作、inline path/query 标量参数以及 JSON 对象请求体。不支持 `$ref`、YAML、复杂参数样式、非 JSON 请求体、文件上传、Header/Cookie 参数和任意 HTTP 方法。导入时明确拒绝不支持的结构，不会自行猜测。
- 操作 `operationId` 只能由字母数字/下划线组成，不能重复。所有请求路径必须来自导入后的固定定义，路径变量只接受安全的字母数字与 `_-`，不允许斜杠或路径穿越。查询参数禁止增加未声明的键；不接受模型提供的请求 Header 或自定义 URL。
- API 执行使用 `trust_env=False`，不继承运行环境代理、不跟随重定向；HTTP 响应最大 1MB；发起网络请求前会检查准确的服务器 allowlist、Agent 版本、Tool Assignment、策略和参数级审批。任何失败不会自动重试已批准的有副作用操作。
- 不支持直接传递 API Key、Bearer、OAuth 等凭证。请通过**可信 API 网关**接入需要授权的内部接口，避免把凭证写进 OpenAPI 文档。
- 精确 URL allowlist 不替代网络层出站限制；务必使用防火墙/网络策略限制应用可访问范围。线上生产联调、API 幂等性、完整持久化异步流程仍需要单独验收。
