# Data Model Baseline

> v0.2 data model baseline. Dynamic Agent resources are now first-class SQLAlchemy entities with Alembic migrations. Compose uses PostgreSQL for Agent Definition / Version while legacy Runs / Approvals remain on the v0.1 store until the Async Runtime milestone.

## 1. Current persistence overview

| Domain | Current storage |
| --- | --- |
| Demo business data | SQLite or external SQLAlchemy datasource |
| Data Agent datasource | SQLAlchemy URL |
| Knowledge chunks / embeddings | SQLite |
| Agent Definition / Version | PostgreSQL in Compose; SQLite fallback for lightweight demo |
| Runs | SQLite legacy store |
| Approvals | SQLite legacy store |
| Web sessions | process memory |
| Platform configuration | environment / persisted configuration |

## 2. Run

Current `agent_runs` shape:

```text
id
agent
status
duration_ms
trace_json
error_type
request_id
correlation_id
agent_id
agent_version
created_at
```

Run is an execution record, not an audit record.

`agent_id` and `agent_version` are implemented in v0.2. Future fields include:

```text
workspace_id
total_tokens
estimated_cost
parent_run_id
retry_of
```

## 3. Approval

Current `approvals` shape:

```text
id
agent
tool
target
reason
status
requested_by
actor
consumed_by
created_at
decided_at
```

Important invariant:

```text
approved Agent + Tool + Target
must match
executed Agent + Tool + Target
```

Consumption is single-use.

## 4. Knowledge

Knowledge is currently chunk-oriented.

The store persists document metadata and chunk/embedding content in SQLite.

Current concerns include:

- document ID
- version
- tags
- allowed roles
- chunks
- embeddings

Future model introduces first-class `knowledge_bases` before moving search to pgvector.

## 5. Data Sources

Data Agent configuration supports a default datasource plus named data sources.

A datasource contains at least:

```text
name
url
schema
```

Query safety configuration includes:

```text
sql_max_rows
sql_timeout_seconds
```

v0.2+ should make Data Source a first-class resource rather than only a settings entry.

## 6. Identity

Current identities are configuration-backed:

```text
username
role
```

Roles:

```text
user
operator
approver
admin
```

Web session state is not persistent in v0.1.

## 7. Tool Policy

Tool Policy is currently code/configuration driven rather than persisted as a general Tool Registry.

Policy fields conceptually include:

```text
agent
name
risk
mode
approval_required
```

v0.2 will introduce first-class Tool resources and Agent ↔ Tool assignment.

## 8. v0.2 implemented Agent model

Implemented tables:

```text
agents
agent_versions
```

`agents` stores resource identity and lifecycle:

```text
id
name
slug
description
type
status
built_in
published_version
created_by
created_at
updated_at
```

`agent_versions` stores immutable configuration versions:

```text
id
agent_id
version
status

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
published_at
```

SQLAlchemy defines the runtime model and Alembic owns schema migration. Compose points `PLATFORM_DATABASE_URL` at PostgreSQL. The lightweight standalone demo may use SQLite.

The next milestone introduces Tool Registry and Agent ↔ Tool resources; Data Source promotion remains a later resource-model step rather than being pulled into M1.

## 9. Long-term target

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

These tables must be introduced milestone by milestone, not created speculatively.

## 10. Data modeling rule

Before introducing a table, answer:

1. Is this concept a first-class product resource?
2. Does it have its own lifecycle and permissions?
3. Does it need querying, history, audit, or references from other resources?

If not, prefer a simpler representation until requirements justify promotion to a resource.
