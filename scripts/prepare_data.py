"""CLI script for preparing the emotion dataset."""

from __future__ import annotations

import argparse

from lyubava.data.prepare import prepare_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare Lyubava emotion dataset.")

    parser.add_argument(
        "--config",
        type=str,
        default="configs/data.yaml",
        help="Path to data preparation config.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prepare_dataset(args.config)


if __name__ == "__main__":
    main()