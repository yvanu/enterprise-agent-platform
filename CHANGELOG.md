# Changelog

## v0.2.0

Dynamic Agent Platform milestone.

### Agent resources

- Added persistent Agent Definition and immutable Agent Version models.
- Added Draft / Published / Archived lifecycle and Published Version rollback.
- Added Agent CRUD, Version history, Publish, Archive, and Run APIs.
- Runs now store `agent_id` and `agent_version` for execution provenance.
- Migrated Data, Knowledge, Ops, and Supervisor into database-backed Built-in Agent definitions.
- Added a Generic Custom Agent runtime using the published instructions/model configuration.

### Web Console

- Agents Directory is now API/resource driven instead of hard-coded.
- Added New Agent flow.
- Added managed Agent Detail with Overview, Playground, Runs, Evaluations, Versions, and Configuration.
- Added publish/version controls and admin-only archive action.
- Added Agent Version and Agent ID to Run Inspector.
- Added Chinese/English copy for the new Agent management surfaces.

### Persistence / Engineering

- Added SQLAlchemy Agent resource store.
- Added Alembic and initial `agents` / `agent_versions` migration.
- Added PostgreSQL-backed Agent Store to Docker Compose.
- Docker startup applies Alembic migrations before starting FastAPI.
- Kept legacy Run / Approval persistence unchanged for compatibility; those move with the Async Runtime milestone.
- Expanded automated coverage to 60 tests.

## Unreleased

### OpenAPI Tool Platform (M2.5 second stage)

- Added admin-only OpenAPI 3.x JSON inline import of allowlisted GET/POST REST operations with fixed server-controlled base URL.
- Imported operations enter the Tool Registry and published Agent Tool assignments, with mandatory parameter-bound approval and one-time consumption.
- Generic Agent proposal/resume now supports both MCP and OpenAPI providers, sharing trace, approval and policy enforcement.
- Tools console supports importing OpenAPI JSON files; added security regression tests for untrusted paths, query keys, parameter tampering and replay.

### MCP Tool Runtime (M2.5 first stage)

- Added allowlisted MCP Streamable HTTP discovery, Tool Registry import, one-time approval-gated calls and MCP Server management UI.
- Generic Agent now exposes only enabled, published-version-assigned MCP tools through OpenAI-compatible Function Calling.
- Unapproved or unassigned remote calls fail closed; tool outputs enter the model context and execution trace.
- Agent Playground now proposes exact MCP arguments for human review and offers deterministic resume after approval.
- Bound approvals to Agent ID, published Agent Version, Tool ID and canonical JSON arguments; reject tampering, cross-agent use, version drift and replay.
- Pending tool proposals have an explicit `waiting_approval` Run status; paused operations survive page reload via approval records.

### Tool Platform

- Added persistent Tool Registry and version-scoped Agent Tool assignments.
- Built-in Data, Knowledge, and Ops capabilities now seed into the registry.
- Tool resources include canonical key, provider/type, input/output schema, timeout, read/write mode, risk, and approval requirement.
- Published Agent Versions keep immutable Tool assignments; new Draft Versions inherit the previous Tool set.
- Existing Tool Policy and Approval flows now resolve policy metadata through the registry.
- Managed Agent runs enforce Tool assignments at execution time.
- Built-in dedicated workspaces use the same published-version Tool context, preventing UI/API bypass.
- Supervisor delegation switches into each child Agent's Tool context.
- Added Tool Registry and Agent Version Tool APIs plus Tool configuration UI.
- Added Alembic migration `20260929_0002_tool_platform`.
- Expanded automated coverage to 63 tests.

- Added Web/API one-click isolated incident demo backed by the actual Data, Knowledge, Ops, and Supervisor code paths.
- Offline demo now records a Supervisor Run/Trace while keeping temporary demo data isolated.
- Added per-request Request ID / Correlation ID propagation into Agent Run records.
- Added unified API error envelopes and JSON structured HTTP/Agent Run logs.
- Added per-process API rate limiting with unified 429 responses.
- Added `/health/live` and dependency-aware `/health/ready` endpoints plus Docker healthcheck.
- Added production startup config validation and secret-safe Settings representation.

## v0.1.0

First portfolio-ready release of Enterprise Agent Platform.

### Agents

- Data Agent: schema-aware NL-to-SQL, SQL Guard, retry/repair, result summary, chart and Markdown report.
- Knowledge Agent: document ingestion, PDF/DOCX parsing, chunking, embeddings, role-scoped retrieval, citations, tags and document versions.
- Ops Agent: system snapshot, configured logs, Prometheus, Docker/Kubernetes read-only inventory, and allowlisted service restart.
- Supervisor: read-only cross-agent incident investigation across Ops, Knowledge and Data with partial-failure degradation.

### Platform

- Bearer authentication and RBAC for user/operator/approver/admin.
- Tool Policy registry with read/write mode, risk level, and approval requirements.
- Human-in-the-loop approval records bound to Agent + Tool + Target with single-use consumption.
- Run history, Trace detail, deterministic Eval, offline Regression Suite, quality metrics, P50/P95, and Prometheus export.
- Offline incident demo that requires no external LLM key or production data.

### Engineering

- FastAPI + SQLAlchemy + OpenAI-compatible runtime.
- SQLite demo storage with PostgreSQL/Kingbase support path.
- Docker Compose and non-root container.
- GitHub Actions with compile check, tests, dependency consistency, and vulnerability audit.
- 44 automated tests at release time.
- Architecture, demo, and interview documentation.
