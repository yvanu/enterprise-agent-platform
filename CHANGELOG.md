# Changelog

## Unreleased

- Added Web/API one-click isolated incident demo backed by the actual Data, Knowledge, Ops, and Supervisor code paths.
- Offline demo now records a Supervisor Run/Trace while keeping temporary demo data isolated.
- Added per-request Request ID / Correlation ID propagation into Agent Run records.
- Added unified API error envelopes and JSON structured HTTP/Agent Run logs.

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
