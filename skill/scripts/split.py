#!/usr/bin/env python3
"""Split a JSONL dataset into batches for parallel CoT generation.

Usage:
    python split.py input.jsonl batches/ --size 30

Outputs batch_000.jsonl, batch_001.jsonl, ... into the batches directory.
Each output file is a JSONL file with the same records as the input.
Also writes batches/manifest.json describing the batches.
"""
import argparse
import json
import os
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="Input JSONL file")
    ap.add_argument("outdir", help="Output directory for batches")
    ap.add_argument("--size", type=int, default=30, help="Records per batch")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.outdir, exist_ok=True)

    records = []
    with open(args.input, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Error: line {i+1} is not valid JSON: {e}", file=sys.stderr)
                sys.exit(1)

    total = len(records)
    batch_size = args.size
    n_batches = (total + batch_size - 1) // batch_size

    manifest = {"total": total, "batch_size": batch_size, "n_batches": n_batches, "batches": []}

    for b in range(n_batches):
        start = b * batch_size
        end = min(start + batch_size, total)
        batch = records[start:end]
        fname = f"batch_{b:03d}.jsonl"
        fpath = os.path.join(args.outdir, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            for rec in batch:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        manifest["batches"].append({
            "file": fname,
            "start": start,
            "end": end,
            "count": end - start,
        })
        print(f"Wrote {fname}: records {start}-{end} ({end-start} records)")

    mpath = os.path.join(args.outdir, "manifest.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\nTotal: {total} records -> {n_batches} batches")
    print(f"Manifest: {mpath}")


if __name__ == "__main__":
    main()
