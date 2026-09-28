# Demo Guide

## Fastest demo: no external LLM

After installing the project:

```bash
python scripts/demo_incident.py
```

Expected story:

1. Ops Agent reads a simulated import-service timeout log.
2. Knowledge Agent retrieves the import operations manual.
3. Data Agent queries historical `import_jobs`.
4. Supervisor combines the three evidence sources.
5. The final answer explicitly says no repair action was executed.

For JSON output:

```bash
python scripts/demo_incident.py --json
```

## Web demo

```bash
cp .env.example .env
docker compose up --build
```

Open `http://127.0.0.1:8000/`.

In the Supervisor tab, **一键离线 Demo** runs the same isolated scenario through `POST /api/v1/platform/demo/incident`; it works even when no external LLM is configured and records the Supervisor Run/Trace for inspection.

When `AUTH_ENABLED=false`, the demo runs as `development/admin`.

For an RBAC demo, set:

```env
AUTH_ENABLED=true
AUTH_TOKENS={"user-token":"alice:user","operator-token":"operator:operator","approver-token":"reviewer:approver","admin-token":"admin:admin"}
```

Enter one of the token keys in the Web UI token field.

## 5-minute interview flow

### 1. Data Agent

Ask:

> 统计每类数据的数量，并指出数量最多的类别。

Show the generated SQL, query result, chart, Markdown report, and Run Trace.

### 2. Knowledge Agent

As `operator`, add a document with tags and restricted roles. Switch to a user token to demonstrate role-filtered retrieval.

### 3. Human Approval

As `operator`, request deletion of a knowledge document.

Switch to `approver-token`, approve it.

Switch back to `operator-token`, execute the approved delete.

Show that the approval becomes `consumed` and cannot be reused.

### 4. Ops safety

Show Tool Policy entries and explain that arbitrary shell is not registered. If you configure `OPS_ALLOWED_SERVICES`, demonstrate that service restart requires a target-bound approval.

### 5. Supervisor

Ask:

> 为什么最近导入任务失败？请结合当前运维状态、知识库手册和历史数据给出排查结论。

Show the three child findings, Supervisor Trace, Run detail, and Eval result.

## What to emphasize

- LLM prompts are not the security boundary; Tools are.
- RBAC answers "who", Tool Policy answers "what capability", Approval answers "who authorized this risky target".
- Run/Trace/Eval make Agent behavior debuggable and regression-testable.
- The offline demo executes the actual Agent classes, not a mocked UI-only path.
- The platform intentionally keeps the infrastructure small until measured scale requires more.
