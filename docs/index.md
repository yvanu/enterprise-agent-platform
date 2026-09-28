---
layout: home

hero:
  name: "Enterprise Agent Platform"
  text: "Safe, observable, governable Multi-Agent Control Plane"
  tagline: Data · Knowledge · Ops · Supervisor — with RBAC, Tool Policy, Human Approval, Run/Trace, Eval and enterprise operations built in.
  actions:
    - theme: brand
      text: Open Live Demo
      link: https://agent.majhoon.site
    - theme: alt
      text: Interview Guide
      link: /INTERVIEW
    - theme: alt
      text: GitHub
      link: https://github.com/yvanu/enterprise-agent-platform

features:
  - title: Multi-Agent by domain
    details: Data, Knowledge and Ops keep their own tool and security boundaries. Supervisor orchestrates only when a real cross-domain investigation needs it.
  - title: Security outside the prompt
    details: RBAC, Tool Policy, SQL Guard, allowlists and target-bound single-use approvals enforce capabilities independently from model output.
  - title: Observable execution
    details: Request ID, Correlation ID, Run, Trace, structured logs, P50/P95 metrics and Prometheus make failures diagnosable end to end.
  - title: Regression-ready
    details: Deterministic evals and isolated Fake-LLM regression cases run in CI without external model keys or production databases.
  - title: Resource-oriented console
    details: Agents, Knowledge, Data Sources, Runs, Approvals, Integrations and Credentials are modeled as first-class platform resources.
  - title: Deliberately simple infrastructure
    details: SQLite and in-process components keep the demo self-contained, while interfaces keep PostgreSQL, pgvector, OIDC and shared state as clear upgrade paths.
---

## What this project demonstrates

Enterprise Agent Platform focuses on the engineering layer around LLM capabilities: **how agents are constrained, audited, observed, evaluated and safely allowed to act**.

<div class="doc-quick-grid">
  <a class="doc-quick" href="/getting-started">
    <span>01</span>
    <strong>Get started</strong>
    <p>Run the platform locally and understand the fastest demo path.</p>
  </a>
  <a class="doc-quick" href="/ARCHITECTURE">
    <span>02</span>
    <strong>Architecture</strong>
    <p>See the platform boundaries, multi-agent flow and approval model.</p>
  </a>
  <a class="doc-quick" href="/DEMO">
    <span>03</span>
    <strong>Demo guide</strong>
    <p>Use the recommended interview walkthrough from login to trace.</p>
  </a>
  <a class="doc-quick" href="/INTERVIEW">
    <span>04</span>
    <strong>Interview handbook</strong>
    <p>Project pitch, design trade-offs and 65 high-frequency questions.</p>
  </a>
</div>

## Core execution model

```text
Web Console / API
        │
        ▼
Authentication + RBAC
        │
        ├──────── Data Agent
        ├──────── Knowledge Agent
        ├──────── Ops Agent
        └──────── Supervisor
                     │
                     ├── Ops evidence
                     ├── Knowledge evidence
                     └── Data evidence

All execution is governed by:

Tool Policy → Human Approval → Run / Trace → Eval → Metrics
```

## Live demo

Open **[agent.majhoon.site](https://agent.majhoon.site)** and use the demo credentials:

```text
demo / demo
```

For interview preparation, start with the [Interview Guide](/INTERVIEW).
