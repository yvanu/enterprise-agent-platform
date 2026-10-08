# Development progress and verification

> Snapshot: **2026-10-08** · local `main` · MCP/OpenAPI feature commit `bd5fe6f` · **73 tests passed, 0 failed, 1 dependency deprecation warning**.

This page distinguishes **implemented code** from production deployment and real-service acceptance.

## Milestones

| Milestone | Status | Delivered scope |
| --- | --- | --- |
| M0 / v0.1 Multi-Agent baseline | ✅ Completed | Data, Knowledge, Ops, Supervisor; RBAC, approval, Run/Trace, console |
| M1 / Dynamic Agent Platform | ✅ Completed | Agent CRUD, immutable versions, publish/rollback, built-ins |
| M2 / Tool Platform | ✅ Completed | Registry, versioned assignment, policy and console |
| M2.5 / MCP and OpenAPI | ✅ Initial code complete | MCP Streamable HTTP, OpenAPI 3.x JSON GET/POST, discovery/import, Generic Agent Function Calling, argument-bound approval and resume |
| M2.5 live integration acceptance | ◻ Outstanding | External MCP, enterprise REST, credentials, network/timeouts/idempotency |
| M3 / Async Runtime | ◻ Not started | Durable Run, queue/worker, SSE, cancellation/retry and durable approval continuation |
| M4+ / Platform hardening | ◻ Planned | Spans, token/cost, evaluation, knowledge/credentials, tenants and OIDC |

## 2026-10-08 delivery

- Allowlisted MCP Server registration and discovery into the shared Tool Registry.
- Admin-uploaded OpenAPI 3.x JSON with allowlisted REST base URLs and a restricted GET/POST import.
- Tools assigned to published Agent versions; imported remote tools default to high risk and require approval.
- Generic Agent proposes **exact JSON arguments**, records a `waiting_approval` Run, and does **not** call the remote endpoint before authorization.
- Single-use approval is tied to **Agent ID, published Version, Tool ID and full JSON arguments**. Changed arguments, cross-agent reuse, version drift, and replay are blocked.
- Console support for MCP servers, OpenAPI imports, tool assignment, approval review and deterministic resumption.
- Alembic revisions `20261008_0003` / `20261008_0004` added. The migration chain was inspected; production migrations have **not** been verified.

## Verification

| Check | Result |
| --- | --- |
| `.venv/bin/python -m pytest -q` | ✅ 73 passed |
| JavaScript syntax / Python compile checks | ✅ Passed |
| Alembic revision history / diff checks | ✅ Passed |
| MCP and REST mocked integration (`httpx.MockTransport`) | ✅ Passed |
| Live external integrations | ◻ Not verified |
| Production deployment and schema upgrade | ◻ Not verified |

## Known limits and next milestone

The current agent runtime is synchronous. An approval proposal is durable in the Approval Store, but the original multi-step execution state is **not** durable. A previously consumed approval is not retried automatically: external operations may have succeeded even if the HTTP response was lost. Production deployment requires real integration tests, idempotency design, credential handling, outbound network isolation, schema migration rehearsal, and audit checks.

**M3 next:** durable Run state and events, a worker queue, Run queries, SSE streaming, cancellation and timeout handling, controlled retries, and stateful human-approval continuation.

See [Architecture](/en/ARCHITECTURE), [Roadmap](/en/roadmap), [MCP integration](/mcp-integration), and [OpenAPI integration](/openapi-integration).
