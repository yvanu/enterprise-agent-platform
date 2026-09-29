# Security Baseline

> v0.1 security baseline. This document records what the platform currently enforces and what remains a production upgrade item.

## 1. Security model

The platform does not treat LLM prompts as a security boundary.

The effective execution path is:

```text
Identity
   ↓
RBAC
   ↓
Agent-owned Tool
   ↓
Tool Policy
   ↓
Human Approval (when required)
   ↓
Allowlisted / guarded execution
```

## 2. Authentication

Current modes:

- Web Console: server-side session token stored in an HttpOnly cookie.
- API clients: Bearer Token.
- Development mode: when authentication is disabled, requests run as `development/admin`.

Current roles:

```text
user
operator
approver
admin
```

The current Web Session store is in process memory and is intended for the single-instance demo.

Production upgrade:

- OIDC / enterprise IdP
- shared session store or signed token
- stronger login rate limiting and lockout policy

## 3. RBAC

RBAC answers:

> Who is allowed to perform this platform operation?

Sensitive API routes use role dependencies rather than trusting client-provided role fields.

Approval actors are derived from the authenticated identity.

## 4. Tool Policy

Tool Policy describes:

- owning Agent
- tool name
- read/write mode
- risk
- whether approval is required

RBAC and Tool Policy are intentionally separate:

- RBAC constrains the caller.
- Tool Policy constrains the capability.

## 5. Human Approval

Approval records are bound to:

```text
Agent
Tool
Target
Requester
Approver
Executor
Status
```

An approval must match the exact `Agent + Tool + Target`.

Approved records are consumed once and cannot be replayed.

Current lifecycle:

```text
pending
  ↓
approved / rejected
  ↓
consumed
```

## 6. Data Agent

The Data Agent uses application-level SQL Guarding for read-only execution.

Production security must also rely on database-level least privilege:

- dedicated read-only database account
- statement timeout
- maximum rows
- network restrictions

SQL Guard is a defense layer, not the final authority.

## 7. Knowledge Agent

Knowledge retrieval applies role scope before content is supplied to the model.

The model should not receive documents the current role is not allowed to retrieve.

Future multi-tenant scope should extend this to:

```text
organization
workspace
tenant
user
department
ACL
```

## 8. Ops Agent

The Ops Agent does not expose arbitrary shell execution.

Current capabilities use:

- fixed system evidence collection
- configured log paths
- optional read-only Prometheus / Docker / Kubernetes evidence
- server-side service allowlists

Write actions such as service restart require approval.

## 9. Secrets

Current baseline:

- `.env` is ignored by Git.
- LLM API key and console password use secret-aware configuration types.
- API responses do not intentionally return configured API key plaintext.
- browser session authentication avoids exposing the admin Bearer Token in UI flows.

Production upgrade:

- Vault / managed Secret Store
- credential rotation
- audit of secret use
- tenant-scoped credentials

## 10. Trace and sensitive data

Run history stores execution metadata such as:

- Agent
- status
- duration
- Trace
- error type
- Request ID
- Correlation ID

Raw user questions are not stored in the Run model by default.

Future trace persistence must introduce explicit retention and masking policies before storing full prompts, tool inputs, or outputs.

## 11. v0.1 security limitations

Known limitations:

- sessions are process-local
- static token map is configuration-based
- no OIDC yet
- no multi-tenant isolation yet
- no dedicated credential vault yet
- no full audit log yet
- rate limiting is single-process

These are planned upgrades, not hidden assumptions.
