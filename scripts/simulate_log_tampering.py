"""Demo of an insider rewriting an audit record, to show that the hash chain detects it.

A backup is written next to the log before any change and can be restored with --restore.

Usage:
    python scripts/simulate_log_tampering.py              # flips the HR decision of the first record
    python scripts/simulate_log_tampering.py --restore    # puts the original log back
"""

import argparse
import json
import shutil
from pathlib import Path

from techhire.config import load_settings
from techhire.domain.models import HrDecision


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log", type=Path, default=load_settings().audit_log_path)
    parser.add_argument("--line", type=int, default=1, help="1-based line number of the record to alter.")
    parser.add_argument("--restore", action="store_true")
    return parser.parse_args()


def tamper(log_path: Path, line_number: int) -> None:
    lines = log_path.read_text(encoding="utf-8").splitlines()
    if not 1 <= line_number <= len(lines):
        raise SystemExit(f"The log has {len(lines)} records; line {line_number} does not exist.")

    backup_path = log_path.with_suffix(log_path.suffix + ".bak")
    shutil.copyfile(log_path, backup_path)

    record = json.loads(lines[line_number - 1])
    flipped = {
        HrDecision.INVITE_TO_INTERVIEW.value: HrDecision.DO_NOT_PROCEED.value,
        HrDecision.DO_NOT_PROCEED.value: HrDecision.INVITE_TO_INTERVIEW.value,
    }
    record["hr_decision"] = flipped[record["hr_decision"]]
    record["justification"] = record["justification"] + " (edited)"
    lines[line_number - 1] = json.dumps(record, ensure_ascii=False)
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Altered record on line {line_number}. Backup saved to {backup_path}.")


def restore(log_path: Path) -> None:
    backup_path = log_path.with_suffix(log_path.suffix + ".bak")
    if not backup_path.exists():
        raise SystemExit(f"No backup found at {backup_path}.")
    shutil.move(backup_path, log_path)
    print(f"Restored {log_path} from backup.")


def main() -> None:
    arguments = parse_arguments()
    if arguments.restore:
        restore(arguments.log)
    else:
        tamper(arguments.log, arguments.line)


if __name__ == "__main__":
    main()
