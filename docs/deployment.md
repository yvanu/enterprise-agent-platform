# 低资源生产发布和验收

> 更新于 2026-10-08。目标机器约 1.6GB 内存。**禁止在该机器运行 npm/VitePress build、Docker image build、并行 pytest 或并行后端实例。**

## 1. 发布通道

| 目标 | 构建位置 | 发布方式 | 默认动作 |
| --- | --- | --- | --- |
| 文档站 `docs.agent.majhoon.site` | GitHub-hosted Runner | `.github/workflows/docs.yml` 使用 Cloudflare Wrangler | 主分支 docs 变更触发；凭证缺失时失败而不是假装已上线 |
| Agent API `agent.majhoon.site` | 不需要重新构建，运行代码位于 Git checkout | `.github/workflows/api-release.yml` SSH 调用 `scripts/release_api.sh` | 只能手动触发，默认 `check`，绝不自动重启 |
| 数据库迁移 | 不在自动发布流程执行 | 单独演练、备份、审批 | 仅核对既有 SQLite 表，不自动 `alembic upgrade` |

**已有线上服务**：`eap-demo.service`，WorkingDirectory 为 `/root/gpt/enterprise-agent-platform`，监听 `127.0.0.1:18080`，由 Cloudflare Tunnel 代理。不要操作未启用的 `enterprise-agent-platform.service`：它带有自动 Alembic 升级步骤，且会争用同一端口。

## 2. Cloudflare 文档发布凭证

在 GitHub 仓库 **Settings → Secrets and variables → Actions** 增加：

- `CLOUDFLARE_API_TOKEN`：限制到需要维护的 Worker / 静态资源的 Cloudflare API Token；不要保存到 Git。
- `CLOUDFLARE_ACCOUNT_ID`：对应 Cloudflare Account ID。

Docs 工作流在 GitHub Runner 上 `npm ci` + `npm run docs:build`，将构建产物作为 GitHub artifact 交给另一个 Job，使用 `cloudflare/wrangler-action@v4` 执行 `wrangler deploy --config wrangler.docs.jsonc`，完成后轻量检查新增页面 HTTP 200。

若 GitHub Actions 凭证缺失，Workflow 会明确发出 Warning 并**跳过自动发布**；Build 成功不表示已发布。第一次上线前应核对 Worker 名称 `enterprise-agent-docs-worker` 和 Custom Domain `docs.agent.majhoon.site` 的归属，确保不覆盖其他 Worker。

## 3. API 手动发布通道

在 GitHub Actions Secrets 中增加：

- `EAP_DEPLOY_HOST`：允许 GitHub Runner SSH 访问的受控目标机器域名/IP。
- `EAP_DEPLOY_USER`：可读取项目并经受控提权操作 `eap-demo.service` 的部署用户；现有脚本要求有备份目录和 systemctl 权限。
- `EAP_DEPLOY_SSH_KEY`：专用部署私钥，仅限该机器、该部署用途。
- `EAP_DEPLOY_SSH_KNOWN_HOSTS`：**通过独立可信渠道核实**的目标 SSH Host Key 行。禁止使用 `StrictHostKeyChecking=no` 或盲目信任 SSH keyscan。

前往 **GitHub → Actions → API release (guarded) → Run workflow**：

1. `mode=check`：仅执行只读预检。要求目标 Git checkout SHA 等于此工作流对应的提交、Tracked 工作树干净、服务当前 active、可用内存至少约 342MiB、1 分钟 load 小于 1、磁盘剩余至少 1GiB；检查现有系统 Python 的 MCP/OpenAPI 模块能导入、平台 SQLite 表齐全。
2. 上述通过后，人工核对当前线上健康并选择 `mode=deploy`，`confirmation=DEPLOY_EAP_PRODUCTION`；GitHub 连接目标机器进行同一预检、序列化发布、**SQLite 在线备份**，最后只重启单个 `eap-demo.service`（不启动额外 Worker）。
3. GitHub Job 会检查 `/health/ready` 及新增 MCP/OpenAPI 路由是否可访问。失败时保留备份并输出错误，**不自动重复重启**，以免反复冲击小内存机器。

### 重要数据库限制

当前既有 SQLite 数据库可能**已存在表而无 `alembic_version` 记录**。执行 `alembic upgrade head` 将可能尝试重建原有表，不能盲目运行。本次保守方案仅在已存在全部需要的表时允许重启；**不会修复 Alembic 版本标记**。迁移版本规范化和 PostgreSQL 环境必须另做备份/结构校验及独立迁移演练。

### 发布边界

本方案没有完整蓝绿发布和自动回滚。单实例重启会造成短暂中断，真实 MCP/REST 接入仍缺少可信凭证仓库和幂等能力。生产变更必须由有权限的操作者明确选择 `deploy`，不能把只读检查结果当成已上线。

## 4. 2026-10-08 已执行的低负载人工发布

现场核对了本机已有的 `CLOUDFLARE_API_TOKEN` 和 `CF_ACCOUNT_ID` 环境变量、Cloudflare 账号下目标 Worker 与 `docs.agent.majhoon.site` 域名绑定，**没有把凭证写入仓库**。使用 GitHub-hosted Runner 已构建的静态 artifact（84 个文件）在服务器上通过已有缓存 Wrangler 低优先级上传，**不重新进行 VitePress 构建**；文档已上线。

后端在 `scripts/release_api.sh check` 通过后执行 `deploy`：先备份现有三个 SQLite 数据库，再只重启 `eap-demo.service`。更新后的 API 健康、MCP/OpenAPI 路由及 docs 进度、MCP、OpenAPI 和 deployment 页面均通过 HTTP 200 的轻量检查。机器没有出现内存耗尽，Swap 未使用。

**目前尚未配置 GitHub Runner Cloudflare/SSH Secrets，所以这套后续自动发布链路尚未具备无人值守能力。** 请注意人工发布只解决上线阻塞，真实远端 MCP/企业 REST 操作及生产幂等/迁移审查仍需另行验收。完整证据见 [开发进度](/PROGRESS)。

## 5. 轻量验收 URL

在新版本发布后逐项复测：

- API `https://agent.majhoon.site/health/live` 和 `/health/ready`：HTTP 200
- API `https://agent.majhoon.site/api/v1/mcp/servers`：不再返回 404（鉴权策略可能导致 401/403）
- API `https://agent.majhoon.site/api/v1/openapi/services`：不再返回 404
- Docs `https://docs.agent.majhoon.site/PROGRESS` 和 `/en/PROGRESS`：HTTP 200
- Docs `https://docs.agent.majhoon.site/mcp-integration` 和 `/openapi-integration`：HTTP 200

检查只使用有限次数的 GET 请求，不进行并发压力测试、不自动建立真实外部工具调用。
