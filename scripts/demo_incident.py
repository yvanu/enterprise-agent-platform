import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.demo.incident import QUESTION, run_demo


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the offline multi-agent incident demo without external LLMs."
    )
    parser.add_argument("--question", default=QUESTION)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run_demo(args.question)
    if args.json:
        print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
        return 0

    print(f"QUESTION\n{result.question}\n")
    for finding in result.findings:
        print(f"[{finding.agent.upper()}] {finding.status}\n{finding.summary}\n")
    print(f"SUPERVISOR\n{result.answer}\n")
    print("TRACE")
    for step in result.trace:
        print(f"- {step.name}: {step.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
