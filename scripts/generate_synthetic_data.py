"""Exports the synthetic dataset to CSV, optionally with poisoned rows for the Art. 15 demo.

Usage:
    python scripts/generate_synthetic_data.py --output data/raw/synthetic.csv
    python scripts/generate_synthetic_data.py --output data/raw/poisoned.csv --inject-invalid 150
"""

import argparse
from pathlib import Path

from techhire.data.synthetic_generator import generate_synthetic_dataset, inject_invalid_rows


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rows", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--inject-invalid", type=int, default=0, help="Number of out-of-range poisoned rows.")
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    frame = generate_synthetic_dataset(arguments.rows, arguments.seed)
    if arguments.inject_invalid:
        frame = inject_invalid_rows(frame, arguments.inject_invalid)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(arguments.output, index=False)
    print(f"Wrote {len(frame)} rows to {arguments.output}")


if __name__ == "__main__":
    main()
