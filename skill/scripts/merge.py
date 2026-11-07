#!/usr/bin/env python3
"""Merge CoT-generated batch files back into one JSONL, with validation.

Usage:
    python merge.py batches/ output/dataset_with_cot.jsonl --check

Each batch file must be named batch_NNN.jsonl. The manifest.json in the batches
directory describes the original order. This script concatenates the batches in
order and validates:
  - Every record has <think>...</think> in the last assistant message
  - The text after </think> is non-empty
  - No duplicate or missing records (by comparing to the input if provided)
"""
import argparse
import json
import os
import re
import sys


THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batches", help="Directory with batch_NNN.jsonl files")
    ap.add_argument("output", help="Output JSONL file")
    ap.add_argument("--check", action="store_true", help="Validate output")
    ap.add_argument("--input", help="Original input JSONL for comparison")
    args = ap.parse_args()

    # Find batch files
    batch_files = sorted([
        f for f in os.listdir(args.batches)
        if re.match(r"batch_\d+\.jsonl$", f)
    ])
    if not batch_files:
        print(f"Error: no batch files found in {args.batches}", file=sys.stderr)
        sys.exit(1)

    # Load and concatenate
    records = []
    per_batch = {}
    for bf in batch_files:
        path = os.path.join(args.batches, bf)
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))
                count += 1
        per_batch[bf] = count
        print(f"Loaded {bf}: {count} records")

    print(f"\nTotal records: {len(records)}")

    # Validate
    errors = []
    if args.check:
        for i, rec in enumerate(records):
            msgs = rec.get("messages", [])
            if len(msgs) < 3:
                errors.append(f"Record {i}: fewer than 3 messages")
                continue
            asst = msgs[-1]
            if asst.get("role") != "assistant":
                errors.append(f"Record {i}: last message is not assistant")
                continue
            content = asst.get("content", "")
            m = THINK_RE.search(content)
            if not m:
                errors.append(f"Record {i}: no <think>...</think> in assistant content")
                continue
            after = content[m.end():]
            # Strip leading newlines
            after_stripped = after.lstrip("\n")
            if len(after_stripped) < 100:
                errors.append(f"Record {i}: content after </think> is too short ({len(after_stripped)} chars)")

        # Compare to input
        if args.input:
            orig = []
            with open(args.input, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        orig.append(json.loads(line))
            if len(orig) != len(records):
                errors.append(f"Record count mismatch: input={len(orig)} output={len(records)}")
            else:
                # Verify text after </think> matches original assistant content
                mismatch = 0
                for i, (o, r) in enumerate(zip(orig, records)):
                    o_asst = o["messages"][-1]["content"]
                    r_asst = r["messages"][-1]["content"]
                    m = THINK_RE.search(r_asst)
                    if m:
                        r_after = r_asst[m.end():].lstrip("\n")
                        if r_after != o_asst:
                            mismatch += 1
                            if mismatch <= 5:
                                errors.append(f"Record {i}: text after </think> differs from original")
                if mismatch:
                    print(f"WARNING: {mismatch} records have text after </think> differing from original")

        if errors:
            print(f"\nValidation errors ({len(errors)}):")
            for e in errors[:20]:
                print(f"  - {e}")
            if len(errors) > 20:
                print(f"  ... and {len(errors)-20} more")
            sys.exit(1)
        else:
            print("Validation passed: all records have CoT and intact text")

    # Write output
    outdir = os.path.dirname(args.output)
    if outdir:
        os.makedirs(outdir, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
