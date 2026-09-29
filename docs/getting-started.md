# 快速开始

平台可以完全在本地运行，其中隔离的 Multi-Agent 故障调查 Demo **不需要外部 LLM API Key**。

## 最快启动方式

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

打开：

- Web Console：`http://127.0.0.1:8000/`
- API 文档：`http://127.0.0.1:8000/docs`

## Docker

```bash
cp .env.example .env
docker compose up --build
```

Compose 配置包含 Readiness Health Check 和持久化数据卷。

## 离线 Multi-Agent Demo

执行：

```bash
python scripts/demo_incident.py
```

这个场景会调查“最近导入任务为什么失败”，并真正执行 Data、Knowledge、Ops、Supervisor 的代码路径，只是使用隔离的数据和确定性的 Fake LLM。

需要机器可读输出时：

```bash
python scripts/demo_incident.py --json
```

## 模型运行时

自然语言相关能力使用 OpenAI-compatible Endpoint：

```text
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=
LLM_MODEL=
EMBEDDING_MODEL=
```

如果本地兼容服务不要求鉴权，`LLM_API_KEY` 可以留空。

## 身份认证

共享 Demo 环境可以开启：

```text
AUTH_ENABLED=true
AUTH_TOKENS={"user-token":"alice:user","operator-token":"operator:operator","approver-token":"reviewer:approver","admin-token":"admin:admin"}

CONSOLE_USERNAME=demo
CONSOLE_PASSWORD=demo
CONSOLE_ROLE=admin
SESSION_MAX_AGE_SECONDS=43200
```

Web Console 使用 HttpOnly Session Cookie；脚本和 API Client 仍然可以使用 Bearer Token。

## 下一步

- [系统架构](/ARCHITECTURE)
- [演示指南](/DEMO)
- [面试手册](/INTERVIEW)
