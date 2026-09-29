from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BuiltinToolDefinition:
    key: str
    name: str
    display_name: str
    description: str
    namespace: str
    mode: str
    risk: str
    approval_required: bool = False
    provider: str = "builtin"
    type: str = "builtin"
    input_schema: dict | None = None
    output_schema: dict | None = None
    timeout_seconds: int = 30


BUILTIN_TOOLS = [
    BuiltinToolDefinition("data.schema", "schema", "Schema", "Inspect database schema metadata.", "data", "read", "low"),
    BuiltinToolDefinition("data.readonly_sql", "readonly_sql", "Read-only SQL", "Execute guarded SELECT/CTE queries.", "data", "read", "low"),
    BuiltinToolDefinition("data.report", "report", "Report", "Build chart and Markdown report output.", "data", "read", "low"),
    BuiltinToolDefinition("knowledge.document_ingest", "document_ingest", "Document ingest", "Create or update knowledge documents.", "knowledge", "write", "medium"),
    BuiltinToolDefinition("knowledge.document_catalog", "document_catalog", "Document catalog", "List role-scoped knowledge documents.", "knowledge", "read", "low"),
    BuiltinToolDefinition("knowledge.document_delete", "document_delete", "Document delete", "Delete a knowledge document.", "knowledge", "write", "medium", True),
    BuiltinToolDefinition("knowledge.vector_search", "vector_search", "Vector search", "Retrieve role-scoped knowledge chunks.", "knowledge", "read", "low"),
    BuiltinToolDefinition("ops.snapshot", "snapshot", "System snapshot", "Read CPU, memory, load and disk evidence.", "ops", "read", "low"),
    BuiltinToolDefinition("ops.log_tail", "log_tail", "Log tail", "Read configured diagnostic log files.", "ops", "read", "low"),
    BuiltinToolDefinition("ops.prometheus", "prometheus", "Prometheus query", "Query the configured Prometheus endpoint.", "ops", "read", "low"),
    BuiltinToolDefinition("ops.docker_ps", "docker_ps", "Docker inventory", "Read running container inventory.", "ops", "read", "low"),
    BuiltinToolDefinition("ops.kubernetes_pods", "kubernetes_pods", "Kubernetes pods", "Read Kubernetes pod inventory.", "ops", "read", "low"),
    BuiltinToolDefinition("ops.service_restart", "service_restart", "Service restart", "Restart an allowlisted systemd service.", "ops", "write", "high", True),
]

BUILTIN_AGENT_TOOL_KEYS = {
    "data": ["data.schema", "data.readonly_sql", "data.report"],
    "knowledge": [
        "knowledge.document_ingest",
        "knowledge.document_catalog",
        "knowledge.document_delete",
        "knowledge.vector_search",
    ],
    "ops": [
        "ops.snapshot",
        "ops.log_tail",
        "ops.prometheus",
        "ops.docker_ps",
        "ops.kubernetes_pods",
        "ops.service_restart",
    ],
    "supervisor": [],
}
