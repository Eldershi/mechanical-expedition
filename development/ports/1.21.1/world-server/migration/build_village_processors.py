#!/usr/bin/env python3
"""Package the CTOV processors still referenced by saved mountain village pieces."""

import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


RETAINED_PROCESSORS = ("village/mountain/roads", "farm/mountain")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-ctov", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    options = parser.parse_args()
    with ZipFile(options.legacy_ctov) as source, ZipFile(options.output, "x", compression=ZIP_DEFLATED) as out:
        pack = {"pack": {"pack_format": 48, "description": "Legacy CTOV village processors"}}
        out.writestr(ZipInfo("pack.mcmeta"), json.dumps(pack) + "\n", compress_type=ZIP_DEFLATED)
        for processor in RETAINED_PROCESSORS:
            path = f"data/ctov/worldgen/processor_list/{processor}.json"
            out.writestr(ZipInfo(path), source.read(path), compress_type=ZIP_DEFLATED)


if __name__ == "__main__":
    main()
