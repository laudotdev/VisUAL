"""Subprocess entry point for VisUAL's controlled interpreter."""
import json
import sys

from visual.interpreter import ControlledInterpreter


def main() -> int:
    source = sys.stdin.read()
    result = ControlledInterpreter(max_steps=5000, max_snapshots=5000).run(source)
    payload = {
        "status": result.status,
        "snapshots": result.snapshots,
        "output": result.output,
        "error": result.error,
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.flush()
    return 0 if result.status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
