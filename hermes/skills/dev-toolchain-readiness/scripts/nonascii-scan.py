#!/usr/bin/env python3
"""List every non-ASCII codepoint in a text file, with line number and context.

Run this when an auto-loader blocks a file as a prompt-injection risk. Those
scanners fire on invisible and bidirectional characters, which appear naturally
in right-to-left prose (Persian, Arabic, Hebrew) and in source comments that
quote it. The surrounding context is what distinguishes a bilingual document
from an injected instruction.

Usage:
    python3 nonascii-scan.py <file> [--invisible-only] [--context N]

Exit status is 0 even when characters are found; this is a reporting tool.
"""

import argparse
import sys
import unicodedata

# Codepoints that are invisible on their own and the usual trigger for an
# injection scanner: zero-width chars, bidi marks/overrides, invisible operators.
INVISIBLE_RANGES = (
    (0x00AD, 0x00AD),  # soft hyphen
    (0x200B, 0x200F),  # zero-width space..RLM
    (0x202A, 0x202E),  # bidi embedding/override
    (0x2060, 0x2064),  # word joiner, invisible operators
    (0xFEFF, 0xFEFF),  # zero-width no-break space / BOM
)

RTL_RANGES = (
    (0x0590, 0x08FF),  # Hebrew, Arabic, Syriac, Thaana, N'Ko
    (0xFB1D, 0xFDFF),  # Hebrew/Arabic presentation forms
    (0xFE70, 0xFEFF),  # Arabic presentation forms-B
)


def classify(cp):
    if any(lo <= cp <= hi for lo, hi in INVISIBLE_RANGES):
        return "INVISIBLE"
    if any(lo <= cp <= hi for lo, hi in RTL_RANGES):
        return "rtl"
    return "other"


def try_name(ch):
    try:
        return unicodedata.name(ch)
    except ValueError:
        return "<unnamed>"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--invisible-only", action="store_true")
    ap.add_argument("--context", type=int, default=45)
    args = ap.parse_args()

    try:
        text = open(args.path, "rb").read().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"cannot read {args.path}: {exc}", file=sys.stderr)
        return 1

    line_of = [0] * (len(text) + 1)
    for i, ch in enumerate(text):
        line_of[i + 1] = line_of[i] + (ch == "\n")

    counts = {}
    hits = 0

    for i, ch in enumerate(text):
        cp = ord(ch)
        if cp < 128:
            continue
        kind = classify(cp)
        if args.invisible_only and kind != "INVISIBLE":
            continue
        counts[kind] = counts.get(kind, 0) + 1
        hits += 1
        ctx = text[max(0, i - args.context):i + args.context]
        print(
            f"offset={i} U+{cp:04X} [{kind}] {try_name(ch)}\n"
            f"  line={line_of[i] + 1}\n"
            f"  ctx={ctx!r}\n"
        )

    print("--- summary ---")
    print(f"file: {args.path}")
    print(f"non-ascii codepoints reported: {hits}")
    for kind, n in sorted(counts.items()):
        print(f"  {kind}: {n}")
    if counts.get("INVISIBLE"):
        print(
            "INVISIBLE codepoints present. Read each context line above: if it\n"
            "is bidirectional prose or a quoted string, this is ordinary content\n"
            "and the file is safe to read normally. If it is imperative text\n"
            "addressed to an AI agent, that is a real finding — report it."
        )
    else:
        print("No invisible codepoints; any block was not caused by hidden characters.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
