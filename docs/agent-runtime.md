# Agent Runtime Baseline

> v0.2 runtime baseline. This document records the current synchronous, versioned Agent/Tool execution model and the target direction for v0.3.

## 1. Current runtime

The current request path is synchronous:

```text
HTTP Request
    ↓
Authentication / RBAC
    ↓
Agent
    ↓
Tool / LLM calls
    ↓
Run record
    ↓
HTTP Response
```

This keeps the v0.1 demo small and deterministic.

## 2. Current Agents

Built-in runtime entry points:

- Data Agent
- Knowledge Agent
- Ops Agent
- Supervisor

Supervisor delegates to Ops, Knowledge and Data in a fixed finite sequence and then synthesizes the findings.

Managed execution establishes a Tool Context for the exact Agent Version. Data / Knowledge / Ops dedicated workspaces resolve the current Built-in Published Version into the same Tool Context. Supervisor switches context for each delegated child Agent.

## 3. Current Run model

A Run currently records:

```text
id
agent
status
duration_ms
trace
error_type
request_id
correlation_id
agent_id
agent_version
created_at
```

Current statuses:

```text
ok
error
waiting_approval
```

`waiting_approval` is a **recorded tool proposal**, not a fully persisted Agent execution context. The operator can approve exact arguments and resume that **single tool action**, but multi-step reasoning state is not restored.

The Run Store uses SQLite in v0.1.

## 4. Current Trace

Trace is represented as ordered `TraceStep` records.

Typical Data Agent flow:

```text
schema
generate_sql
sql_guard
query
summarize
```

Typical Supervisor flow:

```text
delegate_ops
delegate_knowledge
delegate_data
synthesize
```

Trace does not yet provide full parent/child span timing.

## 5. Request correlation

HTTP middleware provides:

```text
X-Request-ID
X-Correlation-ID
```

These values are propagated into Agent Run records.

The purpose is to support:

```text
HTTP request
   ↓
Agent Run
   ↓
Trace
   ↓
Failure point
```

## 6. Failure behavior

Data Agent:

- bounded SQL correction attempts
- SQL Guard failures are surfaced
- database errors are visible to the correction path

Supervisor:

- preserves successful child findings if one child fails
- records failed findings
- fails the whole investigation only when all child Agents fail

Ops optional integrations:

- optional evidence failures are represented in Trace rather than silently hidden

## 7. Current evaluation

Run records can be evaluated using deterministic checks.

Examples:

- expected Trace steps exist
- no critical error step exists
- Data Agent used SQL path
- Knowledge Agent used retrieval path
- Supervisor delegated to expected child Agents

Regression uses fixed fixtures and a Fake LLM so CI does not require external model access.

## 8. Current limitations

The current runtime does not yet support:

- persistent queue
- worker pool
- asynchronous Run creation
- streaming answer events
- Run cancellation
- Run retry lineage
- durable waiting-for-approval **Run continuation** (the lightweight `waiting_approval` proposal status already exists)
- span tree
- token and cost accounting

## 9. Current governed MCP / OpenAPI path

Generic Agent uses OpenAI-compatible Function Calling to propose one of the MCP/OpenAPI tools assigned to its **published Version**. Before remote execution the platform requires a single-use approval frozen to Agent ID, Version, Tool ID and exact JSON arguments. An unapproved proposal creates a `waiting_approval` Run; a separately approved resume action executes the saved arguments without asking the LLM to reselect the operation. The output is summarized and a new Run / Trace is recorded.

Currently remote calls are synchronous, and both the approval store and Run store use the legacy SQLite backend. No durable multi-step LLM context or async worker exists yet. Production timeout/idempotency semantics and live remote integration remain unverified.

## 10. Target async runtime

Planned v0.3 direction:

```text
HTTP API
   ↓
Create Run
   ↓
PostgreSQL
   ↓
Redis Queue
   ↓
Celery Worker
   ↓
Agent Runtime
   ↓
Tool / LLM
   ↓
Run Events / Span Store
```

Planned Run states:

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

Streaming should use SSE first because the primary event direction is server → browser.

## 11. Runtime design rule

Do not add queue, worker, cancellation, or distributed runtime complexity before the Agent resource model is stable.

The planned order is:

```text
Dynamic Agent Definition
        ↓
Tool Registry
        ↓
Async Runtime
        ↓
Trace 2.0
```
