"""CLI entrypoint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from medicineai.orchestrator import run_case
from medicineai.schemas import PatientCase


def _load_case(path: Path) -> PatientCase:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return PatientCase.model_validate(raw)


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        _load_case(Path(args.case_file))
    except ValidationError as e:
        print("Validation failed:", file=sys.stderr)
        print(e, file=sys.stderr)
        return 1
    except OSError as e:
        print(e, file=sys.stderr)
        return 1
    print("OK: patient case JSON is valid.")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    try:
        case = _load_case(Path(args.case_file))
    except ValidationError as e:
        print("Invalid input file:", file=sys.stderr)
        print(e, file=sys.stderr)
        return 1
    except OSError as e:
        print(e, file=sys.stderr)
        return 1

    log_path = Path(args.log).resolve() if args.log else None
    try:
        run_case(case, log_path=log_path)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MedicineAI — clinical decision-support multi-agent CLI (not for clinical use).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run the workflow on a patient case JSON file.")
    p_run.add_argument("case_file", type=str, help="Path to patient case JSON")
    p_run.add_argument(
        "--log",
        type=str,
        default=None,
        help="Optional path to write JSON session log (audit trail).",
    )
    p_run.set_defaults(func=cmd_run)

    p_val = sub.add_parser("validate", help="Validate patient case JSON without calling APIs.")
    p_val.add_argument("case_file", type=str)
    p_val.set_defaults(func=cmd_validate)

    args = parser.parse_args()
    code = args.func(args)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
