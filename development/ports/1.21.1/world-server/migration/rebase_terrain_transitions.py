#!/usr/bin/env python3
"""Apply reviewed terrain edits to the latest stopped-world region files."""

import argparse
import io
import json
from pathlib import Path

from measure_chunk_edges import read_chunk
from splice_overworld_island import Writer


def content(chunk):
    stream = io.BytesIO()
    chunk.write(stream)
    return stream.getvalue()


def rebase(baseline, reviewed, stopped, output):
    report = json.loads((reviewed / "report.json").read_text())
    changed = sorted((tuple(pair) for pair in report["changed_chunks"]),
                     key=lambda pair: (pair[0] // 32, pair[1] // 32, *pair))
    writer = Writer(stopped, output)
    for x, z in changed:
        original = read_chunk(baseline, x, z)
        current = read_chunk(stopped, x, z)
        repaired = read_chunk(reviewed, x, z)
        if original is None or current is None or repaired is None:
            raise ValueError(f"Missing full chunk ({x}, {z})")
        for stamp in ("InhabitedTime", "LastUpdate"):
            original.pop(stamp, None)
            final_time = current.pop(stamp, None)
            if final_time is not None:
                repaired[stamp] = final_time
        if content(original) != content(current):
            raise ValueError(f"Chunk ({x}, {z}) changed since review; regenerate the local repair")
        writer.write(x, z, repaired)
    writer.flush()
    return len(changed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "reviewed", "stopped", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    count = rebase(args.baseline, args.reviewed, args.stopped, args.output)
    print(f"Applied {count} reviewed chunks. Other chunk data came from the stopped world.")


if __name__ == "__main__":
    main()
