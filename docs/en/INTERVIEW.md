# Enterprise Agent Platform: Interview Guide

> Repository: `yvanu/enterprise-agent-platform`
>
> Live demo: `https://agent.majhoon.site`
>
> Demo credentials: `demo / demo`

---

# 1. Project pitch

## 30-second version

Enterprise Agent Platform is a **Multi-Agent Control Plane for enterprise use cases**.

It contains three domain agents:

- **Data Agent** for NL2SQL, schema awareness, read-only SQL guarding, correction, summarization and reports;
- **Knowledge Agent** for enterprise RAG, chunking, embeddings, role-scoped retrieval and citations;
- **Ops Agent** for system snapshots, logs, Prometheus, Docker/Kubernetes read-only diagnosis and approval-gated service restarts;

and a **Supervisor** that combines Ops, Knowledge and Data evidence for cross-agent incident investigation.

The platform layer provides authentication, RBAC, Tool Policy, Human Approval, Run/Trace, Request/Correlation IDs, deterministic Eval, Regression, Prometheus metrics, structured logs and an enterprise Web Console.

## 1-minute version

This project is not a set of prompts wrapped by APIs. It is a small **enterprise Agent platform**.

I split it into two layers.

The domain layer contains Data, Knowledge and Ops Agents plus Supervisor orchestration.

The platform layer provides the controls that enterprise Agent systems usually need: authentication, RBAC, Tool Policy, approval-gated risky actions, Run/Trace, request correlation, evaluation, regression and observability.

My main focus was not whether the model can produce an answer. It was how the system behaves when the model is wrong: how it is constrained, audited, traced, evaluated and allowed to act safely.

## 3-5 minute version

The project started as a Data Agent that could inspect a database schema, generate SQL from natural language, run a query and summarize the result.

That quickly exposed broader engineering questions:

- What if the LLM generates dangerous SQL?
- How do we correct invalid SQL without infinite retries?
- Who is allowed to call which tool?
- Should a model be allowed to restart a service directly?
- How do we explain why a run failed?
- How do we correlate an HTTP request with a specific Agent execution?
- How do we evaluate Agent quality in CI?
- How do multiple domain Agents cooperate without breaking security boundaries?
- How do we make the product look and behave like a platform rather than an API demo?

That led to the current architecture:

```text
Web Console / API
        │
        ▼
Authentication / RBAC
        │
        ├──────── Data Agent
        ├──────── Knowledge Agent
        ├──────── Ops Agent
        └──────── Supervisor
                     │
                     ├── Ops
                     ├── Knowledge
                     └── Data

All Agents share:

Tool Policy
Human Approval
Run / Trace
Eval
Metrics
Structured Logs
```

The Data Agent relies on SQL Guard and database permissions rather than prompt instructions. The Knowledge Agent filters documents by role before retrieval. The Ops Agent does not expose arbitrary shell execution. High-risk write actions require target-bound, single-use approval. Supervisor orchestrates child Agents without bypassing their tool boundaries.

---

# 2. Resume version

**Enterprise Agent Platform | Enterprise Multi-Agent Control Plane**

- Designed and implemented Data, Knowledge and Ops domain Agents plus a Supervisor for cross-agent incident investigation, covering NL2SQL, RAG and infrastructure diagnosis.
- Built shared RBAC, Tool Policy and Human-in-the-loop Approval; risky tools use target-bound, single-use authorization and models never directly execute arbitrary SQL or shell commands.
- Implemented Run/Trace, Request ID/Correlation ID, structured logs, deterministic Eval, regression suites, P50/P95 metrics and Prometheus output for end-to-end observability.
- Data Agent supports schema inspection, multi-source SQL, read-only guarding, SQL correction, result summarization and reports; Knowledge Agent supports chunking, embeddings, role-scoped retrieval and citations.
- Ops Agent integrates system snapshot, logs, Prometheus, Docker/Kubernetes read-only inspection and approval-gated allowlisted service restart.
- Built an enterprise Web Console with session authentication and resource-oriented management for Agents, Runs, Approvals, Credentials, Data Sources and Integrations.

---

# 3. Recommended interview demo

1. Sign in with `demo / demo`.
2. Show Home: attention, agent health, activity and runtime metrics.
3. Open Agents and explain that Agents are resources, not hard-coded sidebar tabs.
4. Run Data Agent once and show SQL Guard + Trace.
5. Run Supervisor and show Ops / Knowledge / Data evidence.
6. Open Runs and inspect Request ID, Correlation ID, Trace and Eval.
7. Open Approvals and explain target-bound, single-use authorization.
8. Show Credentials, Data Sources and Integrations as resource objects.

---

# 4. High-frequency questions

## System design

### Q1. Why Multi-Agent instead of one large Agent?

The domains have different tools and security boundaries. Data needs schema and SQL controls, Knowledge needs retrieval and ACL filtering, and Ops needs infrastructure evidence and stricter action controls. Splitting them keeps prompts smaller, policies clearer, evaluation easier and failures easier to isolate.

### Q2. Why is Supervisor needed?

Supervisor handles tasks that genuinely require evidence from multiple domains. It delegates work and synthesizes findings instead of duplicating the child Agents' capabilities.

### Q3. Why does Supervisor not call every tool directly?

That would bypass child-Agent policy boundaries and duplicate authorization logic. The safer model is Supervisor → Agent → Agent-owned tools.

### Q4. How is this different from a chatbot?

A chatbot mainly optimizes response quality. This platform also manages tool permissions, risky actions, auditability, traces, evaluation, regression and operational resources.

### Q5. What would you design first if you restarted the project?

First-class objects, Agent boundaries, tool boundaries, permission model and Run/Trace data model. Prompts come later.

## Agent / LLM

### Q6. What is the LLM responsible for?

Language understanding, SQL candidate generation, summarization, RAG answering, operations evidence summarization and final synthesis. It is not responsible for authorization or execution safety.

### Q7. Why is a prompt not a security boundary?

Prompts can be influenced by user input, injection, hallucination and context contamination. Security must be enforced by code-level policy, permissions, guards and allowlists.

### Q8. How do you handle model failures?

Model calls have timeouts. Failures mark the Run as error, add trace/error metadata and appear in metrics. Data SQL generation also has bounded correction retries.

### Q9. Why support OpenAI-compatible APIs?

It avoids locking the platform to a single vendor and lets the same runtime work with cloud or compatible self-hosted endpoints.

### Q10. Why separate chat and embedding models?

They serve different workloads. Chat models handle generation and reasoning; embedding models map text into vector space for retrieval.

### Q11. Why did you not use LangChain or LangGraph?

The current control plane is simple enough that explicit code keeps tool boundaries, approvals and traces easier to understand. A graph framework becomes more attractive when workflows require persistence, pause/resume, dynamic graph planning or complex parallel state.

## Data Agent

### Q12. How do you prevent DROP or DELETE?

Application-level SQL Guard only accepts read-only SELECT/CTE patterns, and production should also use a read-only database account. The database permission is the final boundary.

### Q13. Is SQL Guard perfectly safe?

No. It reduces risk, but cannot replace least-privilege database credentials, network boundaries, timeouts and query limits.

### Q14. What happens when generated SQL is invalid?

The error and previous SQL are fed back into a bounded correction loop. Each attempt is recorded in the trace, and retries stop at `agent_max_attempts`.

### Q15. Why inspect schema first?

Without schema context the model guesses table and column names. Schema inspection improves correctness and reduces hallucination.

### Q16. How do you support multiple databases?

Data Sources are represented through SQLAlchemy URLs plus optional schema. The Agent does not bind itself to one database implementation.

### Q17. How do you control expensive queries?

Read-only permissions, statement timeout, row limit and controlled data sources. Production systems can add cost policies, workload groups or warehouse quotas.

## Knowledge / RAG

### Q18. What is the basic RAG flow?

Question → embedding → role-filtered similarity search → top-K chunks → LLM context → answer + sources.

### Q19. Why not use a vector database yet?

The current corpus is small. SQLite storage plus O(n) cosine scan is simple, deterministic and dependency-light. Migration should happen when measured scale or latency justifies it.

### Q20. What happens when O(n) search becomes too slow?

Replace the store implementation with pgvector/HNSW, IVFFlat or a managed vector database while keeping the higher-level retrieval interface stable.

### Q21. How is knowledge authorization enforced?

Documents have `allowed_roles`, and filtering happens before retrieval.

### Q22. Why must ACL filtering happen before retrieval?

Filtering after retrieval risks exposing unauthorized content to the model context. The model should never see content the user is not allowed to access.

### Q23. Why return sources?

Enterprise users need verifiability. Sources help users inspect where an answer came from and reduce blind trust in model output.

## Ops / Security

### Q24. Why does Ops Agent not support arbitrary shell commands?

Arbitrary shell creates an unacceptable blast radius. The platform exposes narrow read-only capabilities and separately governed write actions.

### Q25. Why are Docker and Kubernetes operations read-only?

The current platform focuses on diagnosis. Inventory can provide evidence without mutating infrastructure. Any write action should be a separate policy-controlled tool.

### Q26. How do you prevent service-name injection?

The client submits only a service name. The server checks a configured allowlist and executes structured arguments rather than shell-concatenated strings.

### Q27. Why is Approval needed if there is already an allowlist?

The allowlist defines what actions may exist. Approval decides whether this specific action should be executed now.

## Human Approval / Tool Policy

### Q28. What does Tool Policy contain?

Tool name, owning Agent, read/write mode, risk level and whether approval is required.

### Q29. What is the difference between RBAC and Tool Policy?

RBAC answers who the caller is allowed to be. Tool Policy defines the capability and risk characteristics of the tool itself.

### Q30. Why bind Approval to Target?

To prevent authorization expansion. Approval for `document:7` must not authorize deletion of `document:8`.

### Q31. Why is Approval single-use?

To prevent replay. Once consumed, the same approval cannot authorize another execution.

### Q32. Can prompt injection make the model create approvals?

Not by itself. Approval creation and decision still pass through authenticated APIs and RBAC; model text has no authority outside those controls.

## Supervisor / Multi-Agent

### Q33. Are the three child Agents sequential or parallel?

Sequential today. It keeps the trace deterministic and implementation simple. Parallelization should be driven by measured latency, not architecture fashion.

### Q34. What if one child Agent fails?

Supervisor records a failed finding and continues if other evidence is available. It fails the whole investigation only when every child Agent fails.

### Q35. Why not let one Agent call another Agent's tools?

That would blur ownership and policy boundaries. Each Agent should own its own tools.

### Q36. How do you prevent an infinite Supervisor loop?

The current workflow is fixed and finite. A future dynamic planner would require max steps, depth limits, time budgets and loop detection.

## Run / Trace / Observability

### Q37. What is the difference between Run and Trace?

A Run is the aggregate execution object. Trace is the ordered set of internal steps within that Run.

### Q38. Request ID vs Correlation ID?

Request ID uniquely identifies one HTTP request. Correlation ID can connect multiple requests or service hops that belong to one broader operation.

### Q39. Why write Request ID into Run?

A user-reported request ID can then be mapped directly to the relevant Agent execution and trace.

### Q40. Why not persist all prompts by default?

Prompts may contain business data, secrets or personal information. Raw prompt storage should be an explicit retention and masking policy, not a default.

### Q41. Which Prometheus metrics are useful?

Run count, success ratio, duration P50/P95, eval score, eval pass ratio and error-type counts.

## Eval / Testing

### Q42. Why not use LLM-as-a-Judge for everything?

It costs money, introduces nondeterminism and is harder to trust in CI. Core execution invariants are better covered by deterministic checks.

### Q43. Can deterministic Eval measure natural-language quality?

Not completely. It is good for required steps, tool usage, trace errors and run status. Semantic answer quality can be added through human review or LLM judges.

### Q44. How can CI test Agents without an API key?

Use a Fake LLM plus fixed inputs and temporary databases/knowledge stores.

### Q45. Why not run real models in unit tests?

Real models are slow, costly, network-dependent and nondeterministic. Unit tests should verify program logic.

## Authentication / Backend

### Q46. How does Web login work?

The login endpoint validates configured credentials, creates a random server-side Session Token and stores it in an HttpOnly, SameSite=Lax cookie.

### Q47. Why keep Bearer Token support?

Scripts, API clients and automation are better served by Bearer tokens, while browser users benefit from session-based login.

### Q48. Where are sessions stored?

In process memory in the current single-instance demo. Production multi-replica deployment should use Redis, a database session store, OIDC or signed tokens.

### Q49. Would production use demo/demo?

No. Those are demo-only credentials. Production should use strong secret management and preferably enterprise OIDC/IdP.

### Q50. How is rate limiting implemented?

A lightweight per-process client-IP limiter is enough for the demo. Multi-replica environments should move enforcement to a gateway or shared store.

## Frontend / Product Design

### Q51. Why not use React immediately?

Enterprise quality does not come from a framework. The current scale can be handled without adding build/runtime complexity, so the project first fixed information architecture and product modeling.

### Q52. When would you migrate to React or Vue?

When the UI gains substantial shared state, many reusable components, real-time behavior, complex interactive graphs or a larger frontend team.

### Q53. Why did the first UI feel like a demo?

It mapped backend endpoints directly into cards, forms, buttons and JSON. The redesign instead modeled product resources such as Agent, Run, Approval, Credential, Integration and Data Source.

### Q54. Why is Home attention-first instead of KPI-first?

Operational users need to know what is wrong, pending or degraded before they need aggregate vanity metrics.

### Q55. Why are Agents not global sidebar items?

Agents are dynamic resources. A resource directory scales; a sidebar full of instances does not.

## Deployment / Production

### Q56. How is the project deployed?

The API runs as a FastAPI service. The live demo is exposed through `https://agent.majhoon.site`. Documentation is built with VitePress and served from Cloudflare Workers Static Assets.

### Q57. How do health checks work?

Liveness proves the process is alive. Readiness verifies required stores such as the database, platform store and knowledge store.

### Q58. Why separate liveness and readiness?

An external dependency can fail while the process itself is healthy. Readiness should fail without forcing the orchestrator to restart a healthy process unnecessarily.

### Q59. What would you upgrade first for production?

OIDC/enterprise IdP, PostgreSQL platform state, shared sessions, Secret Manager, tenant isolation, shared rate limiting, pgvector, alerting and stronger retention policies.

### Q60. What are the main current technical debts?

In-memory sessions, SQLite platform state, O(n) vector search, sequential Supervisor orchestration, single-host demo deployment and a deliberately lightweight frontend stack.

## Advanced follow-ups

### Q61. What if 1,000 Agent Runs execute concurrently?

Move Agent execution behind a task queue and worker pool, persist Run state in PostgreSQL/Redis and stream status through SSE/WebSocket.

### Q62. How would you implement Run cancellation?

Use task IDs, cancellation tokens, cooperative cancellation inside workers, tool-level timeouts and cancellation of external requests where supported.

### Q63. How would you implement multi-tenancy?

Add `tenant_id` to all critical resources—documents, Runs, Approvals, Credentials and Data Sources—and enforce tenant scope in every query and resource lookup.

### Q64. How do you defend against prompt injection systemically?

Layer defenses: input handling, clear system/data separation, Tool Policy, RBAC, Approval, output validation, least-privilege infrastructure and auditing. Never rely on "tell the model not to do bad things."

### Q65. How would you control Agent cost?

Record model, prompt/completion tokens, embedding usage, tool calls, duration and estimated cost per Run. Then add budgets, quotas, model routing and caching.

---

# 5. What to emphasize in interviews

1. **Prompt is not the security boundary.**
2. **Agent engineering means Run, Trace, Eval, Regression and Metrics.**
3. **Multi-Agent is used only where domain boundaries justify it.**
4. **Human Approval belongs in the platform layer.**
5. **Productization matters: configuration, audit, observability and governance are first-class capabilities.**

---

# 6. Honest limitations

Do not claim the current demo is fully production-ready.

A better statement is:

> The project implements the core engineering mechanisms of an enterprise Agent platform while intentionally keeping several single-instance components simple. Each simplification has a clear production upgrade path.

Current simplifications:

| Current | Why | Upgrade |
| --- | --- | --- |
| SQLite Run / Approval store | self-contained demo | PostgreSQL |
| O(n) vector search | small corpus | pgvector |
| in-memory session | single instance | OIDC / Redis |
| sequential Supervisor | deterministic trace | parallelize after measurement |
| static allowlist | simple and safe | policy service |
| lightweight frontend | current scale | React/Vue when complexity requires it |
| single-host demo | easy showcase | Kubernetes / autoscaling |
| per-process rate limit | simple | Gateway / Redis |

---

# 7. One-sentence summary

> I built an enterprise Multi-Agent Control Plane around execution safety, governance, observability, evaluation and cross-agent collaboration—not just an LLM demo—so models can operate inside real systems in a controlled, auditable and regression-testable way.
