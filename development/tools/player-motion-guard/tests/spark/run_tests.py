#!/usr/bin/env python3
"""Compile production SparkArchive with test-only game boundaries and real Gson."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess

BASE = Path(__file__).resolve().parent
PROJECT = BASE.parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--gson', type=Path)
    parser.add_argument('--java', default=shutil.which('java') or 'java')
    parser.add_argument('--javac', default=shutil.which('javac') or 'javac')
    args = parser.parse_args()
    gson = args.gson or PROJECT / 'servers/cmi-expedition/instance/libraries/com/google/code/gson/gson/2.10/gson-2.10.jar'
    gson = gson.resolve()
    if not gson.is_file():
        parser.error('Provide --gson pointing to a Gson 2.10 JAR')
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=False)
    classes = output / 'classes'; classes.mkdir()
    source = PROJECT / 'tools/player-motion-guard/src/expedition/motionguard/diagnostics/SparkArchive.java'
    files = [source, BASE / 'SparkArchiveProbe.java', *sorted((BASE/'stubs').rglob('*.java'))]
    compiled = subprocess.run([args.javac, '--release', '17', '-proc:none', '-cp', str(gson), '-d', str(classes), *map(str, files)], capture_output=True, text=True)
    (output/'compile.log').write_text(compiled.stdout+compiled.stderr)
    if compiled.returncode:
        raise SystemExit(compiled.stderr)
    results = []
    for scenario in ['source-bytes', 'source-entries', 'ambiguous', 'oversize', 'archive-failure', 'healthy-history']:
        runtime = output/scenario; runtime.mkdir()
        result = subprocess.run([args.java, '-Xmx128M', '-XX:ActiveProcessorCount=2', '-cp', os.pathsep.join([str(classes),str(gson)]), 'expedition.motionguard.tests.SparkArchiveProbe', scenario], cwd=runtime, capture_output=True, text=True, timeout=20)
        (runtime/'console.log').write_text(result.stdout+result.stderr)
        if result.returncode:
            raise SystemExit(result.stdout+result.stderr)
        results.append(json.loads(result.stdout.strip().splitlines()[-1]))
    report = {'passed':all(row['passed'] for row in results),'minecraftStarted':False,'jfrStarted':False,'results':results}
    (output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':report['passed'],'scenarios':[row['scenario'] for row in results]}))


if __name__ == '__main__':
    main()
