# Enterprise Agent Platform Development Roadmap

> This document defines the default direction for future development of `enterprise-agent-platform`.  
> The objective is not to keep adding preset agents. The objective is to evolve the project into a platform that can **define, version, publish, run, govern, observe, and evaluate agents**.

---

# 1. Current stage

> **Snapshot: 2026-10-08 · M2.5 core implementation completed · M3 Async Agent Runtime next · 73 tests passing.** See [Development progress](/en/PROGRESS) for verified scope and blockers.

The current platform already includes:

- Data Agent
- Knowledge Agent
- Ops Agent
- Supervisor
- Session Login and Bearer Token authentication
- RBAC
- Tool Policy
- Human Approval
- Run / Trace
- Deterministic Eval
- Regression
- Prometheus Metrics
- Structured Logging
- Enterprise Web Console
- Bilingual UI
- Live Demo
- Documentation site

M1 Dynamic Agents and M2 Tool Registry / versioned assignments are implemented. The initial M2.5 scope also adds allowlisted MCP Streamable HTTP and OpenAPI 3.x JSON tools, Generic Agent function calling, argument-bound approval, and single-use deterministic resumption.

**Remaining limitations:** synchronous execution; no persistent worker queue, SSE, cancel/retry, durable multi-step workflows, or credential vault. Automated remote integrations use mocked services; production end-to-end verification remains outstanding.

The roadmap therefore changes the development focus from:

```text
We implemented several agents
```

to:

```text
We implemented a platform that can host agents
```

---

# 2. Target architecture

```text
Enterprise Agent Platform v1.0

Organization / Workspace
        │
        ├── Agents
        │    ├── Definition
        │    ├── Version
        │    ├── Publish
        │    ├── Playground
        │    ├── Tools
        │    ├── Knowledge
        │    ├── Data Sources
        │    └── Guardrails
        │
        ├── Agent Runtime
        │    ├── Async Run
        │    ├── Queue / Worker
        │    ├── Streaming
        │    ├── Cancel / Retry
        │    └── Trace Span
        │
        ├── Tool Platform
        │    ├── Tool Registry
        │    ├── MCP
        │    ├── OpenAPI
        │    └── Policy
        │
        ├── Knowledge Platform
        │    ├── Knowledge Base
        │    ├── pgvector
        │    ├── Hybrid Search
        │    └── ACL
        │
        ├── Evaluation
        │    ├── Dataset
        │    ├── Evaluator
        │    ├── Experiment
        │    └── Regression Gate
        │
        ├── Governance
        │    ├── RBAC
        │    ├── Approval
        │    ├── Policy Engine
        │    ├── Audit Log
        │    └── OIDC
        │
        └── Observability
             ├── Trace
             ├── Token
             ├── Cost
             ├── Metrics
             └── Alerts
```

The key change is that built-in agents become templates hosted by the platform rather than the platform itself.

---

# 3. Development principles

1. Platform capabilities before additional preset agents.
2. Security enforcement in code, never in prompts alone.
3. Important concepts must become first-class resources.
4. Agent configuration must be versioned.
5. Every execution must produce a Run and traceable spans.
6. Risky tools must pass through Policy and Approval.
7. Infrastructure complexity must be justified by real requirements.
8. Frontend design remains resource-oriented instead of endpoint-oriented.
9. Every milestone must remain demonstrable and testable.
10. `main` must stay runnable and deployable.

---

# 4. Version plan

| Version | Goal |
| --- | --- |
| v0.1 | Current Multi-Agent + Governance + Console |
| v0.2 | Dynamic Agent Platform |
| v0.3 | Async Agent Runtime |
| v0.4 | Trace / Cost / Eval Platform |
| v0.5 | Knowledge / MCP / Credential Platform |
| v0.6 | Multi-Tenant / OIDC / Audit |
| v1.0 | Production Ready |

---

# 5. M0 — Freeze v0.1

**Status: ✅ Completed (2026-09-29)**

The v0.1 baseline is frozen and accepted. No new functionality should be added to M0; active development now moves to v0.2 / M1.

Recommended tag:

```text
v0.1.0
```

Deliverables:

- Stable demo
- Passing tests
- Architecture documentation
- Security documentation
- Runtime documentation
- Data model documentation
- Roadmap

Acceptance:

- [x] All tests pass (58 passed)
- [x] Demo login works
- [x] Data / Knowledge / Ops / Supervisor run correctly
- [x] Approval flow works
- [x] Documentation site is reachable
- [x] Tag `v0.1.0`
- [x] `main` is deployable

### M0 acceptance evidence

- Demo: `https://agent.majhoon.site`
- Docs: `https://docs.agent.majhoon.site`
- Roadmap: `https://docs.agent.majhoon.site/en/roadmap`
- Current regression: `58 passed`
- Release tag: `v0.1.0`
- Supervisor offline demo returns Ops / Knowledge / Data findings and completes synthesis

M0 is closed. New capabilities belong to v0.2+ milestones rather than changing the v0.1 baseline.

---

# 6. M1 — Dynamic Agent Platform

**Status: ✅ Completed (2026-09-29)**

**Priority: P0**

Goal:

> Turn Agent into a real platform resource.

## Agent model

```text
agents

id
name
slug
description
type
status
built_in
created_by
created_at
updated_at
```

Statuses:

```text
draft
published
archived
```

## Agent Version

```text
agent_versions

id
agent_id
version

instructions

model_provider
model
temperature
max_tokens

max_steps
timeout_seconds

tool_config
knowledge_config
data_config
guardrail_config

created_by
created_at
```

Rules:

- Published versions are immutable.
- Editing creates a new draft version.
- Runs store `agent_id + agent_version`.
- Rollback republishes an older version.

## Agent lifecycle

```text
Draft
  ↓
Playground
  ↓
Evaluation
  ↓
Publish
```

## API

```text
POST /api/v1/agents
GET  /api/v1/agents
GET  /api/v1/agents/{id}

POST /api/v1/agents/{id}/versions
GET  /api/v1/agents/{id}/versions

POST /api/v1/agents/{id}/publish
POST /api/v1/agents/{id}/archive
```

## UI

```text
Agents                                      + New agent

Data Analyst
Published · v4
GPT-5.6
4 Tools · 2 Data Sources
```

Agent Detail:

```text
Overview
Playground
Runs
Evaluations
Versions
Configuration
```

## Built-in migration

Migrate Data, Knowledge, Ops and Supervisor into database-backed built-in agent definitions.

Acceptance:

- [x] Create Agent
- [x] Edit Agent
- [x] Draft Version
- [x] Version History
- [x] Publish
- [x] Archive
- [x] Playground
- [x] Run stores Agent Version
- [x] Built-in agents migrated
- [x] One custom agent can run end to end

### M1 acceptance evidence

- Added SQLAlchemy `agents` / `agent_versions` models.
- Alembic migration verified with a real SQLite upgrade and PostgreSQL offline DDL generation.
- Docker Compose uses PostgreSQL for the Dynamic Agent Store.
- Added `/api/v1/agents` resource APIs, version history, publish/rollback, archive, and run.
- Agents Directory is API-driven instead of hard-coded.
- Agent Detail supports Overview / Playground / Runs / Evaluations / Versions / Configuration.
- Runs persist `agent_id + agent_version`.
- Data / Knowledge / Ops / Supervisor seed as Built-in Agent Definitions.
- Custom Generic Agent lifecycle is covered end-to-end: Create → Publish → Run → New Version → Publish → Rollback → Archive.
- Current regression: `60 passed`.

M1 is closed. The next milestone is M2: Tool Platform.

---

# 7. M2 — Tool Platform

**Status: ✅ Completed (2026-09-29)**

**Priority: P0**

Goal:

> Turn Tool into a governed platform resource.

## Tool Registry

```text
tools

id
name
display_name
description

provider
type

input_schema
output_schema

mode
risk_level
approval_required

timeout_seconds

enabled
created_at
updated_at
```

Initial types:

```text
builtin
mcp
http
database
```

## Agent ↔ Tool

```text
agent_tools
```

Agent configuration:

```text
☑ database.schema
☑ database.query
☑ report.generate
□ prometheus.query
□ service.restart
```

## Policy

```text
Agent
 ↓
Tool Request
 ↓
Policy Evaluation
 ↓
ALLOW
DENY
APPROVAL_REQUIRED
```

Inputs include identity, workspace, agent, tool, target and environment.

Do not introduce a heavyweight policy engine yet. Keep the first implementation explicit and testable.

Acceptance:

- [x] Tool Registry
- [x] Built-in tools registered
- [x] Version-scoped Agent tool assignment
- [x] Risk classification
- [x] Approval requirements
- [x] Unified policy evaluation
- [x] Published Version assignments are immutable
- [x] Draft Versions inherit the previous Tool set
- [x] Dedicated built-in workspaces enforce the same Tool policy

Evidence:

- Added SQLAlchemy `tools` / `agent_tools` resources and Alembic migration.
- Built-in capabilities seed into the registry.
- Added Tool Registry and Agent Version Tool APIs.
- Tool metadata includes input/output schema, timeout, mode, risk, and approval requirements.
- Managed Agent runs and dedicated built-in workspaces enforce versioned assignments.
- Supervisor delegation enters each child Agent's Tool context.
- Agent Configuration now exposes Tool Assignment.
- At M2 completion: `63 passed` (historical acceptance baseline).

M2 closed on 2026-09-29; initial M2.5 implementation followed on 2026-10-08. The next active development milestone is **M3**.

---

# 8. M2.5 — MCP and OpenAPI tools

**Status: ✅ Initial implementation complete (2026-10-08); live integration and production acceptance outstanding.**

**Priority: P0/P1**

Add MCP Servers as resources.

```text
id
name
transport
url
credential_id
status
created_at
updated_at
```

Flow:

```text
Add MCP Server
      ↓
Connect
      ↓
tools/list
      ↓
Discover Tools
      ↓
Tool Registry
      ↓
Policy Review
      ↓
Assign to Agent
```

Security rule:

```text
MCP
 ↓
Tool Registry
 ↓
Policy
 ↓
Approval
 ↓
Agent Runtime
```

Never expose discovered MCP tools directly to the model without platform policy.

Implemented and verified:

- [x] Allowlisted MCP Server registration and tool discovery
- [x] MCP tool import into Tool Registry and Agent Version assignments
- [x] Governed Generic Agent function-calling, argument-level approval and single-use deterministic resume
- [x] Allowlisted OpenAPI 3.x JSON GET/POST import into the same Registry / approval flow
- [x] Console registration, tool assignment, and approval parameter review
- [x] 73 automated tests passing (2026-10-08)
- [ ] Real external MCP / enterprise REST end-to-end integration
- [ ] Credential management, production idempotency, and durable multi-step runs

See [Development Progress](/en/PROGRESS), [MCP integration](/mcp-integration) and [OpenAPI integration](/openapi-integration). Next active milestone: **M3 Async Agent Runtime**.

---

# 9. M3 — Async Agent Runtime

**Priority: P0**

Move from synchronous request execution to a persistent runtime.

```text
HTTP API
   ↓
Create Run
   ↓
Queue
   ↓
Worker
   ↓
Agent Runtime
   ↓
Tool
   ↓
Run Store
```

Recommended stack:

- PostgreSQL
- Redis
- Celery

## Run states

```text
queued
running
waiting_approval
cancelling
cancelled
completed
failed
timeout
```

## API

```text
POST /api/v1/runs
GET  /api/v1/runs
GET  /api/v1/runs/{id}

POST /api/v1/runs/{id}/cancel
POST /api/v1/runs/{id}/retry

GET  /api/v1/runs/{id}/events
```

## SSE

Use Server-Sent Events first.

Events:

```text
run.created
run.started
step.started
step.completed
tool.started
tool.completed
approval.required
answer.delta
run.completed
run.failed
```

## Cancel / Retry

Introduce cancellation tokens and preserve retry lineage with:

```text
parent_run_id
retry_of
```

Acceptance:

- [ ] PostgreSQL platform store
- [ ] Redis
- [ ] Worker
- [ ] Run queue
- [ ] Run state machine
- [ ] SSE streaming
- [ ] Cancel
- [ ] Retry
- [ ] Timeout
- [ ] Waiting Approval
- [ ] Worker failure recovery

---

# 10. M4 — Trace 2.0 / Token / Cost

**Priority: P1**

Upgrade Trace Step into Span.

```text
trace_id
span_id
parent_span_id
run_id
type
name
start_time
end_time
duration_ms
status
input
output
error
```

Span types:

```text
agent
llm
tool
retrieval
database
approval
```

Trace UI:

```text
Trace Tree        Span Detail        Run Info
```

LLM spans record:

```text
provider
model
prompt_tokens
completion_tokens
total_tokens
```

Run aggregates:

```text
total_tokens
estimated_cost
```

Acceptance:

- [ ] Parent/child spans
- [ ] Agent spans
- [ ] Tool spans
- [ ] LLM spans
- [ ] Retrieval spans
- [ ] Token usage
- [ ] Estimated cost
- [ ] Trace Tree UI
- [ ] Cost metrics

---

# 11. M5 — Evaluation Platform

**Priority: P1**

Create first-class evaluation resources.

## Dataset

```text
eval_datasets
eval_cases
```

Cases may contain:

```text
input
expected_output
expected_tool
expected_sql
expected_trace
metadata
```

## Evaluators

Support:

```text
deterministic
regex
json
sql
trace
llm_judge
human
```

Prefer deterministic checks first.

## Experiment

Compare Agent versions and models:

| Metric | v12 | v13 |
| --- | ---: | ---: |
| Success | 91% | 96% |
| Eval | 87 | 92 |
| P95 | 3.1s | 2.8s |
| Cost | $0.06 | $0.05 |

## Regression Gate

```text
Draft
 ↓
Evaluate
 ↓
Regression Gate
 ↓
Publish
```

Example rules:

```text
success_rate >= 95%
eval_score >= 90
critical_failures == 0
```

Acceptance:

- [ ] Dataset
- [ ] Cases
- [ ] Evaluators
- [ ] Experiment
- [ ] Version comparison
- [ ] Regression
- [ ] Publish gate

---

# 12. M6 — Knowledge / Data / Credentials

**Priority: P1**

## Knowledge Base

Replace document-only management with Knowledge Bases.

```text
Operations KB
Product KB
Radar KB
Technical KB
```

Configuration:

```text
embedding_model
chunk_strategy
chunk_size
chunk_overlap
retrieval_top_k
reranker
acl
```

## pgvector

Move from SQLite scanning when corpus size or retrieval latency justifies it.

## Hybrid Search

```text
Vector Search
      +
BM25
      ↓
Merge
      ↓
Reranker
      ↓
Top K
```

## Data Source 2.0

Support PostgreSQL, Kingbase, MySQL and SQLite with a Schema Explorer.

## Credential Vault

Credentials become encrypted resources referenced by ID.

Never return plaintext secrets through the API.

Acceptance:

- [ ] Knowledge Base
- [ ] Agent ↔ Knowledge Base
- [ ] pgvector
- [ ] Hybrid Search
- [ ] Data Source Detail
- [ ] Schema Explorer
- [ ] Credential Vault
- [ ] Secret encryption
- [ ] Connection tests

---

# 13. M7 — Enterprise Governance

**Priority: P2**

Add:

```text
Organization
   ↓
Workspace
   ↓
Resources
```

All critical resources gain:

```text
organization_id
workspace_id
```

RBAC 2.0:

```text
Organization Admin
Workspace Admin
Developer
Operator
Approver
Viewer
```

OIDC:

- Keycloak
- Microsoft Entra ID
- Generic OIDC

Audit Log records:

```text
actor
action
resource_type
resource_id
before
after
ip
request_id
created_at
```

Acceptance:

- [ ] Organizations
- [ ] Workspaces
- [ ] Tenant isolation
- [ ] Cross-tenant security tests
- [ ] RBAC 2.0
- [ ] OIDC
- [ ] Audit Log

---

# 14. M8 — Developer Platform / Ecosystem

Add only after the platform core is stable.

## API Keys

Scoped machine access:

```text
agents:run
runs:read
```

## Webhooks

Events:

```text
run.started
run.completed
run.failed
approval.requested
approval.approved
agent.published
```

## Notifications

Potential channels:

- Web
- Webhook
- Slack
- WeCom
- DingTalk

## OpenAPI Tool Import

```text
OpenAPI Spec
      ↓
Operation Discovery
      ↓
Tool Registry
      ↓
Policy
      ↓
Agent
```

## SDK / CLI

Start with a Python SDK and CLI.

---

# 15. Production hardening

Before v1.0:

- PostgreSQL + Alembic
- Redis shared state
- Idempotency keys
- Retry/backoff/jitter
- Explicit timeout hierarchy
- Liveness/readiness
- Secret Manager
- Backup strategy
- Dependency/security scanning
- Load/performance testing

Timeout hierarchy:

```text
HTTP Timeout
LLM Timeout
Tool Timeout
Agent Timeout
Run Timeout
Worker Timeout
```

---

# 16. CI/CD

Target pipeline:

```text
Lint
 ↓
Unit Test
 ↓
Integration Test
 ↓
Security Scan
 ↓
Agent Regression
 ↓
Docs Build
 ↓
Container Build
 ↓
Deploy
```

Security tools can include:

- pip-audit
- Bandit
- Trivy
- Semgrep when justified

---

# 17. Testing strategy

Five layers:

```text
Unit
Integration
Agent Regression
Security
E2E
```

Security scenarios must cover:

- Prompt Injection
- SQL Injection
- Shell Injection
- Cross-tenant access
- Approval replay
- Unauthorized tools
- Credential leakage

Use Playwright for E2E once frontend complexity warrants it.

---

# 18. Long-term core data model

Expected v1.0 resources:

```text
organizations
workspaces
users
memberships

agents
agent_versions

tools
agent_tools

credentials

data_sources

knowledge_bases
documents
chunks

runs
spans

approvals

eval_datasets
eval_cases
experiments

audit_logs

api_keys
webhooks
```

Do not create all tables in advance. Add them milestone by milestone.

---

# 19. Repository architecture direction

Long-term shape:

```text
app/
  api/
  core/

  modules/
    agents/
    tools/
    runtime/
    runs/
    knowledge/
    data_sources/
    approvals/
    policies/
    evaluations/
    credentials/
    organizations/
    workspaces/
    audit/

  infrastructure/
    database/
    redis/
    llm/
    mcp/

  worker/
  platform/
```

Avoid a big-bang refactor. Move code only as each module is implemented.

---

# 20. Frontend direction

Keep the current information architecture:

```text
Home

BUILD
  Agents
  Knowledge
  Data Sources

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

Add capability inside those resource areas instead of redesigning global navigation repeatedly.

---

# 21. Explicit non-goals for now

Do not prioritize:

- More preset business agents
- Kubernetes
- Microservices
- Kafka
- Complex workflow designer
- Full frontend framework rewrite
- Dozens of connectors
- Heavyweight policy engines

These should be introduced only when real complexity justifies them.

---

# 22. Sprint plan

## Sprint 1 — Platform Store + Agent Definition

- PostgreSQL
- Alembic
- Agent model
- Agent Version
- Agent API
- Agent Directory
- Create / Edit / Publish UI

## Sprint 2 — Tool Registry

- Tool model
- Agent Tools
- Policy
- Risk
- Approval binding

## Sprint 3 — MCP

- MCP Server
- Connect
- Discovery
- Registry import
- Agent assignment

## Sprint 4 — Async Runtime

- Redis
- Celery
- Run Queue
- State Machine
- Cancel
- Retry
- Timeout

## Sprint 5 — Streaming + Trace

- SSE
- Run events
- Spans
- Run Detail UI

## Sprint 6 — Token / Cost

- Token tracking
- Model pricing
- Cost estimates
- Dashboard metrics

## Sprint 7 — Eval Platform

- Dataset
- Cases
- Evaluators
- Experiment
- Regression Gate

## Sprint 8 — Knowledge / Credentials

- Knowledge Base
- pgvector
- Hybrid Search
- Credential Vault
- Data Source Detail

## Sprint 9 — Enterprise Governance

- Organization
- Workspace
- Tenant isolation
- RBAC 2.0
- OIDC
- Audit

## Sprint 10 — Production Hardening

- API Keys
- Webhooks
- Security tests
- E2E
- Deployment hardening

---

# 23. Definition of Done

A feature is complete only when all applicable areas are complete.

## Backend

- API
- Data model
- Migration
- Permission checks
- Stable error model

## Frontend

- Usable UI
- Loading state
- Empty state
- Error state
- Disabled state
- Permission state

## Tests

- Unit tests
- Key integration tests
- Security boundary tests

## Observability

Important execution must appear in Run, Trace, Audit or Metrics as appropriate.

## Documentation

Update relevant:

- README
- Architecture
- Roadmap
- Demo/API documentation

## Deployment

- Public smoke test
- No regression

---

# 24. Mandatory pre-commit checks

At minimum:

```bash
python -m compileall -q app tests scripts
python -m pytest -q
git diff --check
```

Frontend:

```bash
node --check app/static/app.js
node --check app/static/i18n.js
```

Docs:

```bash
npm run docs:build
```

---

# 25. Git / release discipline

`main` must always stay runnable and deployable.

Feature branches may follow:

```text
feature/agent-definition
feature/tool-registry
feature/mcp
feature/async-runtime
feature/eval-platform
```

Release tags:

```text
v0.1.0
v0.2.0
v0.3.0
...
```

Create a tag before major architecture changes.

---

# 26. Technology trigger conditions

## SQLite → PostgreSQL

Do this when Dynamic Agent Definition begins.

## Redis / Celery

Introduce when Async Run begins.

## pgvector

Introduce after Knowledge Base abstraction is stable and measured search latency/corpus size requires it.

## React / Vue

Re-evaluate only when multiple conditions appear:

- complex shared frontend state
- many reusable components
- larger frontend team
- substantial real-time behavior
- workflow/graph editors

## Kubernetes

Consider only when multi-replica orchestration, worker autoscaling and multi-environment deployment become real operational problems.

---

# 27. Priority for the next 2–3 months

## P0

1. PostgreSQL Platform Store
2. Dynamic Agent Definition
3. Agent Version
4. Agent Publish
5. Tool Registry
6. Agent Tool Assignment
7. MCP
8. Async Agent Runtime

## P1

9. SSE
10. Cancel / Retry
11. Trace Span
12. Token / Cost
13. Eval Dataset
14. Experiment
15. Regression Gate
16. Credential Vault
17. Knowledge Base

## P2

18. pgvector / Hybrid Search
19. Workspace
20. Multi-Tenant
21. OIDC
22. Audit
23. API Keys
24. Webhooks

---

# 28. Product positioning evolution

Current:

> Enterprise Multi-Agent Platform

After M1–M3:

> **Enterprise Agent Runtime & Control Plane**

After M4–M7:

> **Multi-tenant Enterprise AgentOps Platform**

The name should only change when the underlying capabilities justify it.

---

# 29. Immediate next milestone

The next milestone is fixed as:

# v0.2 — Dynamic Agent Platform

Execution order:

```text
1. Freeze v0.1.0

2. PostgreSQL Platform Store
3. Alembic

4. Agent Definition
5. Agent Version
6. Agent Publish

7. Agent Repository
8. Agent Service
9. Agent API

10. Agent Directory UI
11. Create Agent UI
12. Configuration UI
13. Versions UI

14. Built-in Agent Migration
15. Custom Agent Runtime Adapter

16. Tests
17. Docs
18. Demo
19. Tag v0.2.0
```

Until v0.2 is complete:

- Do not add new business agents.
- Do not introduce Kubernetes.
- Do not split into microservices.
- Do not build a workflow designer.
- Do not rewrite the frontend framework.

---

# 30. Final decision rule

Before adding a feature, ask:

1. Does this make Agents more platform-managed and configurable?
2. Does this improve safety, governance, observability, or evaluation?
3. Has real complexity proven that additional infrastructure is necessary?

The roadmap should optimize for:

> **Clearer platform boundaries, more configurable Agents, safer execution, easier diagnosis, and measurable quality—not simply more features.**
