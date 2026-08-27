#!/usr/bin/env python3
"""Estimate prompt tokens for routing decisions without a host tokenizer.

Counts CJK characters (Han, kana, hangul) near one token each and remaining
text near four characters per token. Use for the fast-lane/orchestrated-lane
routing gate and rough budget checks; treat results as planning guidance,
not billing truth.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

CJK_PATTERN = re.compile(r"[\u2e80-\u9fff\u3040-\u30ff\uac00-\ud7af\uf900-\ufaff]")


def approximate_tokens(value: Any) -> int:
    if value is None:
        return 0
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if not value:
        return 0
    cjk = len(CJK_PATTERN.findall(value))
    return max(1, math.ceil(cjk + (len(value) - cjk) / 4))


def estimate_path(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"not a file: {path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    return {
        "path": str(path),
        "characters": len(text),
        "lines": lines,
        "estimated_tokens": approximate_tokens(text),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="files to estimate; with no paths, read text from stdin",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print a machine-readable report",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass

    reports: list[dict[str, Any]] = []
    try:
        if args.paths:
            for path in args.paths:
                reports.append(estimate_path(path))
        else:
            text = sys.stdin.read()
            reports.append(
                {
                    "path": "<stdin>",
                    "characters": len(text),
                    "lines": text.count("\n"),
                    "estimated_tokens": approximate_tokens(text),
                }
            )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    total = sum(report["estimated_tokens"] for report in reports)
    if args.json:
        print(json.dumps({"files": reports, "estimated_tokens_total": total}, indent=2, ensure_ascii=False))
    else:
        for report in reports:
            print(
                f"{report['path']}: {report['estimated_tokens']} tokens "
                f"({report['lines']} lines, {report['characters']} chars)"
            )
        print(f"Total: {total} tokens across {len(reports)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
