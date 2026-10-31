#!/bin/sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BUILD_DIR="$SCRIPT_DIR/build"
mkdir -p "$BUILD_DIR/classes" "$BUILD_DIR/fake-classes"
javac --release 17 -encoding UTF-8 -d "$BUILD_DIR/classes" "$SCRIPT_DIR/src/ExpeditionBootstrap.java"
javac --release 17 -encoding UTF-8 -d "$BUILD_DIR/fake-classes" "$SCRIPT_DIR/tests/FakeServer.java"
python3 "$SCRIPT_DIR/package.py" "$BUILD_DIR"
printf '%s\n' "$BUILD_DIR/server-bootstrap.jar"
