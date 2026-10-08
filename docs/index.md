---
layout: home

hero:
  name: "Enterprise Agent Platform"
  text: "安全、可观测、可治理的多 Agent 控制平面"
  tagline: Data · Knowledge · Ops · Supervisor —— 内置 RBAC、Tool Policy、Human Approval、Run/Trace、Eval 与企业级运维能力。
  actions:
    - theme: brand
      text: 打开在线 Demo
      link: https://agent.majhoon.site
    - theme: alt
      text: 面试手册
      link: /INTERVIEW
    - theme: alt
      text: GitHub
      link: https://github.com/yvanu/enterprise-agent-platform

features:
  - title: 按领域拆分 Multi-Agent
    details: Data、Knowledge、Ops 各自保持工具与安全边界，只有真正需要跨领域调查时才由 Supervisor 编排。
  - title: 安全边界不依赖 Prompt
    details: RBAC、Tool Policy、SQL Guard、Allowlist 与绑定 Target 的单次审批共同约束能力，不把模型输出当成权限。
  - title: 全链路可观测
    details: Request ID、Correlation ID、Run、Trace、结构化日志、P50/P95 指标与 Prometheus 支持端到端故障定位。
  - title: 可回归验证
    details: 确定性 Eval 与隔离的 Fake LLM Regression 可以在 CI 中运行，不依赖真实模型 Key 和生产数据库。
  - title: 资源化企业 Console
    details: Agents、Knowledge、Data Sources、Runs、Approvals、Integrations、Credentials 都作为一等平台资源管理。
  - title: 克制的基础设施
    details: 当前使用 SQLite 与进程内组件保持 Demo 自包含，同时预留 PostgreSQL、pgvector、OIDC 与共享状态的升级路径。
---

## 最新开发进度

截至 **2026-10-08**：M1 Dynamic Agent、M2 Tool Platform、M2.5 MCP/OpenAPI 首版代码已完成，**73 项测试通过**。当前处于 **M3 异步 Runtime 开发准备阶段**；真实远端服务联调与线上部署尚未验收。

查看 [开发进度](/PROGRESS)、[MCP 接入](/mcp-integration) 和 [OpenAPI 接入](/openapi-integration)。

## 这个项目展示什么

Enterprise Agent Platform 重点不是“再做一个聊天机器人”，而是围绕 LLM 能力补齐真正进入企业系统所需要的工程层：

**Agent 如何被约束、审计、观测、评测，以及如何安全地获得执行权限。**

<div class="doc-quick-grid">
  <a class="doc-quick" href="/getting-started">
    <span>01</span>
    <strong>快速开始</strong>
    <p>本地运行平台，并完成最快的 Multi-Agent 演示。</p>
  </a>
  <a class="doc-quick" href="/ARCHITECTURE">
    <span>02</span>
    <strong>系统架构</strong>
    <p>了解平台边界、多 Agent 调用链和 Human Approval 模型。</p>
  </a>
  <a class="doc-quick" href="/DEMO">
    <span>03</span>
    <strong>演示指南</strong>
    <p>按照推荐路径从登录、Agent、Supervisor 一路演示到 Run Trace。</p>
  </a>
  <a class="doc-quick" href="/INTERVIEW">
    <span>04</span>
    <strong>面试手册</strong>
    <p>项目介绍、技术取舍以及 65 道高频面试题与参考回答。</p>
  </a>
</div>

## 核心执行模型

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

所有 Agent 统一经过：

Tool Policy → Human Approval → Run / Trace → Eval → Metrics
```

## 在线 Demo

打开 **[agent.majhoon.site](https://agent.majhoon.site)**，默认演示账号：

```text
demo / demo
```

准备面试时建议从 [面试手册](/INTERVIEW) 开始。
