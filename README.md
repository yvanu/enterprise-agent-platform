# Enterprise Agent Platform

面向企业场景的 Agent 平台。第一阶段实现 **智能数据分析 Agent**：自然语言理解、Schema 感知、SQL 生成、安全校验、执行纠错和结果总结。

## 当前里程碑

- FastAPI API 服务
- PostgreSQL / Kingbase / SQLite 可复用数据库层
- 数据库 Schema 自动感知
- SQL 只读安全网关
- SELECT/CTE 白名单、危险关键字拦截、最大返回行数
- OpenAI-compatible LLM 客户端
- Data Agent 多轮 SQL 生成/执行/纠错
- SQLite 演示数据，开箱即用
- 单元测试

## 快速启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

打开 `http://127.0.0.1:8000/` 使用演示界面，`/docs` 查看 API 文档。

没有配置 LLM 时仍可启动、查看 Schema、测试 SQL 安全执行；自然语言 Agent 只需要配置 `LLM_MODEL`，远程 API 再配置 `LLM_API_KEY`。兼容无需鉴权的本地 OpenAI-compatible 服务。

## API

- `GET /health`
- `GET /api/v1/data/schema`
- `POST /api/v1/data/sql`：安全执行只读 SQL
- `POST /api/v1/data/ask`：自然语言数据分析

## 设计目标

这不是单纯 Text-to-SQL。Agent 会根据数据库返回的错误自动把执行结果反馈给模型，重新生成 SQL；所有 SQL 必须先经过独立安全网关，模型本身不能绕过权限边界。

生产数据库请使用独立只读账号；SQL 解析器是第二道防线，不替代数据库权限。
