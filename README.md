# Enterprise Agent Platform

面向企业场景的多 Agent 平台。项目包含三个业务 Agent，共享同一套 LLM Runtime、配置、数据库能力和 API 服务。

## Agent

- **Data Agent**：自然语言 → Schema 感知 → SQL 生成 → 安全校验 → 自动纠错 → 数据结论。已实现第一版。
- **Knowledge Agent**：企业知识检索、RAG、文档引用、业务流程工具调用。下一阶段实现。
- **Ops Agent**：日志、指标、数据库和运行环境联合诊断，高风险操作人工确认。后续实现。

## 架构

```text
app/
├── agents/
│   ├── data/          # Data Agent
│   ├── knowledge/     # Knowledge Agent
│   └── ops/           # Ops Agent
├── platform/
│   └── llm.py         # 三个 Agent 共用的 LLM Runtime
├── api/
│   └── data.py        # 按业务 Agent 拆分 API
├── db/
│   ├── engine.py      # 数据库访问
│   ├── introspection.py
│   └── sql_guard.py   # SQL 安全边界
├── core/
│   └── config.py
└── main.py
```

当前没有提前增加 Supervisor。只有真正出现跨 Agent 协同需求时再增加调度层。

## 当前 Data Agent 能力

- FastAPI API 服务
- PostgreSQL / Kingbase / SQLite 可复用数据库层
- 数据库 Schema 自动感知
- SQL 只读安全网关
- SELECT/CTE 白名单、危险关键字拦截、最大返回行数
- OpenAI-compatible LLM 客户端
- SQL 生成、执行失败反馈和自动纠错
- 查询结果总结
- SQLite 演示数据
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
- `POST /api/v1/data/sql`
- `POST /api/v1/data/ask`

## 安全边界

模型不能直接执行任意 SQL。查询必须经过 SQL 安全网关；生产数据库仍应使用独立只读账号，解析器只作为第二道防线。
