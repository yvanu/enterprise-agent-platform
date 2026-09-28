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

Local:

```bash
cp .env.example .env
docker compose up --build
```

Open:

```text
http://127.0.0.1:8000/
```

Online demo:

```text
https://agent.majhoon.site
```

Default demo credentials:

```text
demo / demo
```

The Web Console is organized as a resource-oriented Enterprise SaaS console:

```text
Home

BUILD
  Agents
  Knowledge
  Data sources

OPERATE
  Runs
  Evaluations
  Approvals

PLATFORM
  Integrations
  Credentials
  Policies

Settings
```

When `AUTH_ENABLED=false`, the application runs as `development/admin`.
For shared demo environments, enable auth and configure both API tokens and the
console login:

```env
AUTH_ENABLED=true
AUTH_TOKENS={"user-token":"alice:user","operator-token":"operator:operator","approver-token":"reviewer:approver","admin-token":"admin:admin"}

CONSOLE_USERNAME=demo
CONSOLE_PASSWORD=demo
CONSOLE_ROLE=admin
```

The Web Console uses an HttpOnly session cookie. API clients can continue using
Bearer tokens.

## 5-minute interview flow

### 1. Sign in and Home

Open the Web Console and sign in with `demo / demo`.

Show:

- Attention items
- Agent health
- Recent activity
- Runtime metrics

Emphasize that the home page answers "what needs attention?" rather than acting
as a generic KPI dashboard.

### 2. Agents

Open the Agents directory.

Explain that agents are first-class resources, not hard-coded global sidebar
tabs. Open Data Agent and show the common detail shell:

```text
Agent
├── Playground
├── Runs
├── Evaluations
└── Configuration
```

Ask Data Agent:

> 统计每类数据的数量，并指出数量最多的类别。

Show:

- Schema-aware SQL generation
- SQL Guard
- query result
- chart
- Markdown report
- execution trace

### 3. Knowledge

Open Knowledge and add a document with tags and allowed roles.

Then open Knowledge Agent and ask a question to show:

- role-scoped retrieval
- citations
- retrieval trace

For a deeper RBAC demo, call the API with user/operator/approver Bearer tokens.

### 4. Human Approval

As an operator/admin, create a document delete or service restart approval.

Show:

```text
pending
  ↓
approved
  ↓
consumed
```

Explain that the approval is bound to the exact `Agent + Tool + Target` and is
single-use.

### 5. Supervisor

Open Supervisor and run the offline incident demo or ask:

> 为什么最近导入任务失败？请结合当前运维状态、知识库手册和历史数据给出排查结论。

Show the execution graph:

```text
Incident
   ↓
Supervisor
   ↓
Ops / Knowledge / Data
   ↓
Synthesis
```

Then open the execution trace.

### 6. Runs

Open Runs and inspect the Supervisor run.

Show:

- status
- duration
- Request ID
- Correlation ID
- Trace
- Eval

This is the best place to explain the platform engineering layer.

### 7. Integrations / Credentials

Open:

- Credentials → model provider configuration
- Data sources → database resources
- Integrations → Prometheus / logs / Docker / Kubernetes / controlled services

Emphasize that the console models these as resources instead of exposing raw
`.env` JSON.

## What to emphasize

- LLM prompts are not the security boundary; Tools are.
- RBAC answers "who", Tool Policy answers "what capability", Approval answers
  "who authorized this risky target".
- Run/Trace/Eval make Agent behavior debuggable and regression-testable.
- The offline demo executes the actual Agent classes, not a mocked UI-only path.
- Supervisor only orchestrates child Agents and does not bypass their Tool
  boundaries.
- The product UI is resource-oriented: Agents, Runs, Approvals, Credentials,
  Data Sources, and Integrations are first-class objects.
- The platform intentionally keeps infrastructure small until measured scale
  requires more.
