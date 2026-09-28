# Enterprise Agent Platform

面向企业场景的多 Agent 平台。三个业务 Agent 共用同一套 LLM Runtime、配置、Tool Policy、运行审计、确定性 Eval、Regression Suite 和 API 服务；Agent/接口执行 Tool 前会经过统一权限校验。

## 三个 Agent

### Data Agent
自然语言 → Schema 感知 → SQL 生成 → 安全校验 → 自动纠错 → 数据结论。

已实现：
- PostgreSQL / Kingbase / SQLite
- 多数据源配置与按请求切换数据源
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
- 知识文档目录查询

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

已支持通过配置的只读日志文件和 Prometheus API 参与诊断；日志路径只能由服务端配置，不能由请求指定。还可显式启用固定只读命令的 Docker 容器列表与 Kubernetes Pod 列表。当前仍没有重启、Shell 写操作或自动修复能力。

## 架构

```text
app/
├── agents/
│   ├── data/
│   ├── knowledge/
│   └── ops/
├── platform/
│   ├── llm.py          # Chat + Embedding，共享 Runtime
│   ├── policy.py       # Tool 风险与权限清单
│   ├── runs.py         # Agent Run 审计与耗时记录
│   ├── evals.py        # 基于 Trace 的确定性 Eval
│   └── regression.py   # 固定业务样本回归测试
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

## CI / Regression

GitHub Actions 会在 `main` push 和 Pull Request 时使用 Python 3.11 执行完整 `pytest`。其中包含离线 Regression Suite，因此 CI 不依赖外部 LLM Key，也不会访问生产数据库。

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

可选多数据源配置：

```env
DATA_SOURCES={"analytics":{"url":"postgresql+psycopg://readonly:password@db-host/analytics","schema":"public"}}
```

额外数据源只在服务端配置，API 只暴露数据源名称和 schema，不返回连接串。

自然语言能力需要配置：

```env
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=
LLM_MODEL=
EMBEDDING_MODEL=
```

兼容 OpenAI Chat Completions / Embeddings API 的本地服务可以不配置 API Key。

## API

### Platform
- `GET /api/v1/platform/tools`：统一 Tool Policy 清单
- `GET /api/v1/platform/runs`：Agent 运行记录，可按 Agent 过滤
- `GET /api/v1/platform/evals`：对 Run Trace 做确定性评估，可按 Agent 过滤
- `GET /api/v1/platform/metrics`：按 Agent 汇总运行次数、成功率、平均耗时和 Eval 指标
- `POST /api/v1/platform/regression/run`：运行隔离的固定业务样本回归测试

### Data
- `GET /api/v1/data/sources`
- `GET /api/v1/data/schema?source=default`
- `POST /api/v1/data/sql`：请求体可指定 `source`
- `POST /api/v1/data/ask`：请求体可指定 `source`

### Knowledge
- `GET /api/v1/knowledge/documents`
- `POST /api/v1/knowledge/documents`
- `POST /api/v1/knowledge/documents/upload`
- `POST /api/v1/knowledge/ask`

### Ops
- `GET /api/v1/ops/snapshot`
- `GET /api/v1/ops/logs?lines=80`
- `POST /api/v1/ops/prometheus/query`
- `GET /api/v1/ops/docker`
- `GET /api/v1/ops/kubernetes`
- `POST /api/v1/ops/diagnose`

## 安全边界

模型不能直接执行任意 SQL。Data Agent 查询必须经过 SQL 安全网关；生产数据库仍应使用独立只读账号。

平台维护并强制执行统一 Tool Policy，校验所属 Agent、风险等级、读写模式和审批状态；未注册 Tool、模式不匹配或待审批 Tool 会被拒绝。平台指标会基于最近的 Run 聚合各 Agent 的运行次数、成功率、平均耗时、平均 Eval 分和 Eval 通过率。Agent Run 只持久化 Agent 类型、状态、耗时、Trace 和异常类型，不持久化用户问题原文。Eval 直接检查 Run 状态、Trace 错误和关键步骤是否齐全，不额外调用 LLM，结果可重复、成本为零。Regression Suite 使用临时 SQLite 数据库和确定性 Fake LLM，验证 Data Agent 的分类聚合与失败任务统计，以及 Knowledge Agent 的雷达/海洋资料 Top-1 检索，不触碰生产数据。Ops Agent 当前只暴露只读系统信息、服务端白名单日志、只读 Prometheus 查询，以及显式启用后的固定 `docker ps` / `kubectl get pods` 查询；不接受任意 Shell 命令。真正增加高风险写操作时再接 Human-in-the-loop 审批流。
