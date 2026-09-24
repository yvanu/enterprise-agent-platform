import json
import os
import platform
import shutil
from pathlib import Path

import httpx

from app.agents.ops.models import LogTail, OpsAnswer, OpsSnapshot, PrometheusResult
from app.platform.llm import OpenAICompatibleLLM
from app.platform.models import TraceStep


def _memory() -> dict[str, int]:
    values: dict[str, int] = {}
    try:
        with open("/proc/meminfo", encoding="utf-8") as file:
            for line in file:
                key, raw = line.split(":", 1)
                if key in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
                    values[key] = int(raw.strip().split()[0]) * 1024
    except OSError:
        pass
    return values


class OpsAgent:
    def __init__(
        self,
        llm: OpenAICompatibleLLM,
        *,
        log_files: str = "",
        prometheus_url: str = "",
        http_timeout_seconds: int = 5,
    ):
        self.llm = llm
        self.log_files = [Path(p.strip()).resolve() for p in log_files.split(",") if p.strip()]
        self.prometheus_url = prometheus_url.rstrip("/")
        self.http_timeout_seconds = http_timeout_seconds

    def snapshot(self) -> OpsSnapshot:
        disk = shutil.disk_usage("/")
        try:
            load = tuple(float(x) for x in os.getloadavg())
        except (AttributeError, OSError):
            load = None

        return OpsSnapshot(
            hostname=platform.node(),
            cpu_count=os.cpu_count(),
            load_average=load,
            memory=_memory(),
            disk={"total": disk.total, "used": disk.used, "free": disk.free},
        )

    def logs(self, lines: int = 80) -> list[LogTail]:
        lines = max(1, min(lines, 500))
        tails: list[LogTail] = []
        for path in self.log_files:
            try:
                content = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            tails.append(LogTail(path=str(path), lines=content[-lines:]))
        return tails

    def prometheus(self, query: str) -> PrometheusResult:
        if not self.prometheus_url:
            raise ValueError("PROMETHEUS_URL 未配置")

        response = httpx.get(
            f"{self.prometheus_url}/api/v1/query",
            params={"query": query},
            timeout=self.http_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "success":
            raise RuntimeError(data.get("error") or "Prometheus 查询失败")
        result = data.get("data", {}).get("result", [])
        return PrometheusResult(query=query, result=result)

    def diagnose(self, question: str) -> OpsAnswer:
        snapshot = self.snapshot()
        trace = [TraceStep(kind="tool", name="system_snapshot")]

        logs = self.logs()
        if logs:
            trace.append(
                TraceStep(kind="tool", name="log_tail", detail=f"{len(logs)} files")
            )

        prometheus = None
        if self.prometheus_url:
            try:
                prometheus = self.prometheus("up")
                trace.append(
                    TraceStep(
                        kind="tool",
                        name="prometheus_query",
                        detail=f"{len(prometheus.result)} series",
                    )
                )
            except Exception as exc:
                trace.append(
                    TraceStep(
                        kind="tool",
                        name="prometheus_query",
                        status="error",
                        detail=str(exc),
                    )
                )

        context = {
            "snapshot": snapshot.model_dump(),
            "logs": [item.model_dump() for item in logs],
            "prometheus": prometheus.model_dump() if prometheus else None,
        }
        answer = self.llm.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "你是企业运维 Agent。根据提供的只读系统快照、日志和监控数据分析问题。"
                        "明确区分已观察事实和推测；信息不足时说明下一步需要检查什么。"
                        "不要声称已经执行任何修改、重启或修复操作。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"问题：{question}\n\n"
                        f"运维上下文：{json.dumps(context, ensure_ascii=False)}"
                    ),
                },
            ]
        )
        trace.append(TraceStep(kind="llm", name="diagnose"))
        return OpsAnswer(
            question=question,
            answer=answer,
            snapshot=snapshot,
            logs=logs,
            prometheus=prometheus,
            trace=trace,
        )
