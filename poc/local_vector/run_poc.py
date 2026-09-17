from __future__ import annotations

import argparse
import json
from pathlib import Path

from local_vector.io import ensure_output_dir, load_image
from local_vector.pipeline import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local-only vector reconstruction proof of concept")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-error-px", type=float, default=1.5)
    parser.add_argument("--hole-ratio", type=float, default=0.015)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    image = load_image(args.input)
    out = ensure_output_dir(args.out)
    results = run_pipeline(
        image,
        out,
        max_error_px=args.max_error_px,
        hole_ratio=args.hole_ratio,
    )
    summary = {name: metrics.to_dict() for name, metrics in results.items()}
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
