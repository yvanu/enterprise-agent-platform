import json
import os
import platform
import shutil

from app.agents.ops.models import OpsAnswer, OpsSnapshot
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
    def __init__(self, llm: OpenAICompatibleLLM):
        self.llm = llm

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

    def diagnose(self, question: str) -> OpsAnswer:
        snapshot = self.snapshot()
        trace = [TraceStep(kind="tool", name="system_snapshot")]
        answer = self.llm.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "你是企业运维 Agent。根据提供的只读系统快照分析问题。"
                        "明确区分已观察事实和推测；信息不足时说明下一步需要检查什么。"
                        "不要声称已经执行任何修改、重启或修复操作。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"问题：{question}\n\n"
                        f"系统快照：{json.dumps(snapshot.model_dump(), ensure_ascii=False)}"
                    ),
                },
            ]
        )
        trace.append(TraceStep(kind="llm", name="diagnose"))
        return OpsAnswer(question=question, answer=answer, snapshot=snapshot, trace=trace)
