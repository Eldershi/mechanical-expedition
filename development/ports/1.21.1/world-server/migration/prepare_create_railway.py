#!/usr/bin/env python3
"""Convert Create's saved curve, station, observer and signal coordinates for 1.21.1."""

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path

import nbtlib


AXES = {"X", "Y", "Z"}


def position(value):
    return nbtlib.IntArray([int(value[axis]) for axis in "XYZ"])


def convert_curve(connection):
    positions = connection.get("Positions", ())
    if len(positions) != 2 or not all(isinstance(point, nbtlib.Compound) and set(point) == AXES
                                      for point in positions):
        return False
    connection["Positions"] = nbtlib.List[nbtlib.Compound](
        nbtlib.Compound({"Pos": position(point)}) for point in positions
    )
    return True


def convert_single_block_points(points):
    for kind in ("create:station", "create:observer"):
        for point in points.get(kind, ()):
            old = point.get("TilePos")
            if not isinstance(old, nbtlib.Compound) or set(old) != AXES or "BlockEntityPos" in point:
                continue
            point["BlockEntityPos"] = position(point.pop("TilePos"))
            if "TileDimension" in point and "BlockEntityDimension" not in point:
                point["BlockEntityDimension"] = point.pop("TileDimension")
            yield kind


def convert_signal_tiles(points):
    for signal in points.get("create:signal", ()):
        for side in ("Tiles1", "Tiles2"):
            for tile in signal.get(side, ()):
                if "Pos" not in tile and AXES.issubset(tile):
                    tile["Pos"] = position(tile)
                    for axis in AXES:
                        del tile[axis]
                    yield "signal_tiles"


def convert_graphs(saved):
    changes = Counter()
    for graph in saved["data"]["RailGraphs"]:
        for node in graph["Nodes"]:
            for connection in node["Connections"]:
                edge = connection["EdgeData"]
                if "Starts" in edge and convert_curve(edge):
                    changes["curve_connections"] += 1
        points = graph["Points"]
        changes.update(convert_single_block_points(points))
        changes.update(convert_signal_tiles(points))
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    options = parser.parse_args()
    saved = nbtlib.load(options.source)
    changes = convert_graphs(saved)
    with options.output.open("xb") as raw, gzip.GzipFile(fileobj=raw, filename="", mode="wb") as out:
        saved.write(out)
    print(json.dumps(changes, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
