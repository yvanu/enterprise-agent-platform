# Architecture

## System overview

```mermaid
flowchart TB
  CLIENT[Web UI / API Client] --> HTTP[Request ID / Correlation ID / Error Model]
  HTTP --> AUTH[Bearer Auth + RBAC]

  AUTH --> DATA[Data Agent]
  AUTH --> KNOW[Knowledge Agent]
  AUTH --> OPS[Ops Agent]
  AUTH --> SUP[Supervisor]

  SUP --> DATA
  SUP --> KNOW
  SUP --> OPS

  DATA --> SQL[SQL Guard + Read-only Database]
  KNOW --> KS[Knowledge Store]
  OPS --> OT[Read-only Ops Tools]

  DATA --> POLICY[Tool Policy]
  KNOW --> POLICY
  OPS --> POLICY

  POLICY --> APPROVAL[Human Approval]
  APPROVAL --> ACTION[Allowlisted Write Action]

  DATA --> RUNS[Run / Trace]
  KNOW --> RUNS
  OPS --> RUNS
  SUP --> RUNS

  HTTP --> LOGS[Structured JSON Logs]
  RUNS --> EVAL[Deterministic Eval]
  EVAL --> METRICS[Quality Metrics / Prometheus]
```

## Cross-agent incident investigation

```mermaid
sequenceDiagram
  participant U as Operator
  participant S as Supervisor
  participant O as Ops Agent
  participant K as Knowledge Agent
  participant D as Data Agent
  participant L as Shared LLM Runtime

  U->>S: investigate(question)
  S->>O: diagnose(question)
  O->>O: snapshot/logs/prometheus
  O->>L: summarize evidence
  L-->>O: ops finding

  S->>K: ask(question, role)
  K->>K: role-filtered retrieval
  K->>L: answer with sources
  L-->>K: knowledge finding

  S->>D: ask(question)
  D->>D: schema -> SQL Guard -> query
  D->>L: summarize result
  L-->>D: data finding

  S->>L: synthesize all findings
  L-->>S: final incident conclusion
  S-->>U: conclusion + findings + trace
```

The Supervisor currently delegates sequentially. This keeps the execution model simple and deterministic for the demo. Parallel delegation is only worth adding when real latency measurements justify the extra concurrency behavior.

## High-risk write flow

```mermaid
sequenceDiagram
  participant OP as Operator
  participant API as Platform API
  participant AP as Approval Store
  participant RV as Approver
  participant TOOL as Tool

  OP->>API: create approval(agent, tool, target)
  API->>AP: pending(requested_by)
  RV->>API: approve
  API->>AP: approved(actor)
  OP->>API: execute(target, approval_id)
  API->>AP: consume(agent + tool + target)
  AP-->>API: consumed
  API->>TOOL: execute fixed allowlisted action
  TOOL-->>OP: result
```

Approval IDs are single-use and bound to the exact `Agent + Tool + Target`. The model cannot create a new arbitrary shell command from an approved fixed action.

## Security boundaries

| Boundary | Enforcement |
| --- | --- |
| User identity | Bearer token authentication |
| API permissions | RBAC: user / operator / approver / admin |
| Agent capability | Tool Policy registry |
| SQL execution | SQL Guard + database read-only account recommendation |
| Knowledge visibility | role-filtered document scope |
| Risky writes | Human Approval + single-use target-bound approval |
| Ops commands | fixed arguments / server-side allowlists |
| Request tracing | X-Request-ID + X-Correlation-ID propagated into Agent Run |
| API errors | shared error envelope with stable code and request context |
| Audit | Run/Trace + approval actor/requester/executor |
| Prompt data retention | raw user question is not stored in Run history |

## Persistence

| Data | Current storage | Upgrade path |
| --- | --- | --- |
| Demo business data | SQLite / external SQLAlchemy database | PostgreSQL / Kingbase |
| Knowledge chunks + embeddings | SQLite | pgvector / managed vector DB |
| Runs / approvals | SQLite | PostgreSQL |
| Auth identities | config token map | OIDC / enterprise IdP |

The current SQLite choices are deliberate for a self-contained demo. The platform interfaces keep the migration path visible without introducing infrastructure before it is needed.

## Failure model

- Data Agent retries invalid/generated SQL up to `agent_max_attempts`.
- Supervisor records a failed child finding and continues when other agents succeed.
- Supervisor fails only when every child Agent fails.
- Ops diagnosis treats optional Prometheus/Docker/Kubernetes failures as trace errors rather than hiding them.
- Eval flags missing critical steps and trace errors.
- CI runs compile, tests, dependency consistency, and vulnerability audit.

## Scale-up path

1. Replace static bearer tokens with OIDC/JWT validation.
2. Move platform state and knowledge metadata to PostgreSQL.
3. Replace O(n) embedding scan with pgvector when measured corpus size/latency requires it.
4. Add tenant/user ACL predicates in addition to role scope.
5. Parallelize Supervisor delegation if real incident latency becomes material.
6. Add rate limiting, secrets management, alert routing, and production retention policies.
