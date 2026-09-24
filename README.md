# Enterprise Agent Platform

面向企业场景的多 Agent 平台。三个业务 Agent 共用同一套 LLM Runtime、配置和 API 服务。

## 三个 Agent

### Data Agent
自然语言 → Schema 感知 → SQL 生成 → 安全校验 → 自动纠错 → 数据结论。

已实现：
- PostgreSQL / Kingbase / SQLite
- Schema 自动感知
- SELECT/CTE 只读 SQL 安全网关
- 最大结果集限制
- SQL 执行失败反馈给模型并自动纠错
- 查询结果总结
- 数值结果自动生成轻量图表
- 自动生成可下载 Markdown 分析报告

### Knowledge Agent
企业知识检索 → RAG → 带来源回答。

已实现第一版：
- 文本直接写入以及 txt / md / csv / json / PDF / DOCX 文件上传
- PDF / DOCX 文本提取与文档自动分块
- OpenAI-compatible Embedding
- SQLite 存储向量
- 余弦相似度检索
- 检索结果作为上下文回答
- 返回原始来源

当前采用进程内 O(n) 向量扫描，适合项目演示和小规模知识库。数据量真正变大时再替换 pgvector / Vectorize，不提前引入向量数据库。

### Ops Agent
系统运行状态 → LLM 诊断。

已实现第一版：
- CPU 数量
- Load Average
- 内存 / Swap
- 磁盘使用情况
- 只读系统快照
- 基于快照的故障分析

已支持通过配置的只读日志文件和 Prometheus API 参与诊断；日志路径只能由服务端配置，不能由请求指定。当前仍没有重启、Shell 写操作或自动修复能力。Docker/Kubernetes 写操作后续再增加 Tool 权限和人工审批。

## 架构

```text
app/
├── agents/
│   ├── data/
│   ├── knowledge/
│   └── ops/
├── platform/
│   └── llm.py          # Chat + Embedding，共享 Runtime
├── api/
│   ├── data.py
│   ├── knowledge.py
│   └── ops.py
├── db/
│   ├── engine.py
│   ├── introspection.py
│   └── sql_guard.py
├── core/
│   └── config.py
└── main.py
```

暂不增加 Supervisor。出现真实跨 Agent 协同需求时再加。

## 快速启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

打开：

- `http://127.0.0.1:8000/`：当前 Data Agent 演示界面
- `http://127.0.0.1:8000/docs`：完整 API

自然语言能力需要配置：

```env
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=
LLM_MODEL=
EMBEDDING_MODEL=
```

兼容 OpenAI Chat Completions / Embeddings API 的本地服务可以不配置 API Key。

## API

### Data
- `GET /api/v1/data/schema`
- `POST /api/v1/data/sql`
- `POST /api/v1/data/ask`

### Knowledge
- `POST /api/v1/knowledge/documents`
- `POST /api/v1/knowledge/documents/upload`
- `POST /api/v1/knowledge/ask`

### Ops
- `GET /api/v1/ops/snapshot`
- `GET /api/v1/ops/logs?lines=80`
- `POST /api/v1/ops/prometheus/query`
- `POST /api/v1/ops/diagnose`

## 安全边界

模型不能直接执行任意 SQL。Data Agent 查询必须经过 SQL 安全网关；生产数据库仍应使用独立只读账号。

Ops Agent 当前只暴露只读系统信息、服务端白名单日志和只读 Prometheus 查询，不提供危险执行工具。需要写操作时再引入明确的 Tool 风险等级和 Human-in-the-loop。
