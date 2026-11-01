#!/usr/bin/env python3
"""Verify a forced completed JFR remains readable after SIGKILL, without exit hooks."""
from pathlib import Path
import argparse
import json
import os
import queue
import signal
import subprocess
import threading
import time

TOOL = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New disposable output directory')
    parser.add_argument('--java', default='java')
    parser.add_argument('--javac', default='javac')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    classes = output/'classes'
    classes.mkdir()
    persistent = output/'persistent'
    persistent.mkdir()
    # Sparse placeholders exercise retention without allocating gigabytes of disk blocks.
    for number in range(9):
        with (persistent/f'diag-retention-{number:03d}-periodic.jfr').open('wb') as archive:
            archive.seek(180*1024*1024-1)
            archive.write(b'\0')
    (persistent/'unowned.keep').write_text('Retention must leave unrelated files untouched.\n')
    subprocess.run([args.javac, '--release', '17', '-d', str(classes),
        str(TOOL/'src/expedition/motionguard/diagnostics/JfrRecorder.java'),
        str(Path(__file__).with_name('JfrDurabilityProbe.java'))], check=True)
    process = subprocess.Popen([args.java, '-Xmx256m', '-cp', str(classes),
        'JfrDurabilityProbe', 'record', str(output/'persistent')],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    lines = queue.Queue()
    transcript = []
    def read():
        for line in process.stdout:
            transcript.append(line)
            lines.put(line)
    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    acknowledged = None
    deadline = time.monotonic()+25
    while time.monotonic() < deadline and process.poll() is None:
        try:
            line = lines.get(timeout=1)
        except queue.Empty:
            continue
        if 'JFR_DURABILITY_ACK ' in line:
            acknowledged = line.split('JFR_DURABILITY_ACK ', 1)[1].strip()
            os.kill(process.pid, signal.SIGKILL)
            break
    if process.poll() is None:
        process.kill()
    process.wait(timeout=10)
    reader.join(timeout=3)
    (output/'child.log').write_text(''.join(transcript))
    if not acknowledged:
        raise AssertionError('JFR did not acknowledge a forced snapshot: '+''.join(transcript))
    receipt = json.loads((output/'persistent/last-completed.json').read_text())
    if receipt['file'] != acknowledged:
        raise AssertionError('Receipt does not match acknowledged file')
    snapshot = output/'persistent'/acknowledged
    if snapshot.stat().st_size != receipt['bytes']:
        raise AssertionError('Snapshot size changed after SIGKILL')
    result = subprocess.run([args.java, '-Xmx256m', '-cp', str(classes),
        'JfrDurabilityProbe', 'inspect', str(snapshot)], capture_output=True, text=True)
    (output/'validation.log').write_text(result.stdout+result.stderr)
    failure_result = subprocess.run([args.java, '-Xmx256m', '-cp', str(classes),
        'JfrDurabilityProbe', 'failures', str(output/'failure-paths')],capture_output=True,text=True,timeout=35)
    (output/'failure-paths.log').write_text(failure_result.stdout+failure_result.stderr)
    archives = list(persistent.glob('diag-*.jfr'))+list(persistent.glob('diag-*.jfr.partial'))
    archive_bytes = sum(path.stat().st_size for path in archives)
    bounded = len(archives) <= 8 and archive_bytes <= 768*1024*1024
    unrelated_preserved = (persistent/'unowned.keep').read_text() == 'Retention must leave unrelated files untouched.\n'
    report = {'passed': result.returncode == 0 and failure_result.returncode == 0 and process.returncode == -signal.SIGKILL and bounded and unrelated_preserved,
              'exitCode': process.returncode, 'acknowledgedFileSurvived': snapshot.exists(),
              'readableAfterSigkill': result.returncode == 0, 'snapshotBytes': receipt['bytes'],
              'usesShutdownHooks': False, 'validation': result.stdout.strip(),
              'seededRetentionPlaceholders': 9, 'archiveFiles': len(archives), 'archiveBytes': archive_bytes,
              'retentionBoundsPassed': bounded, 'unrelatedFilePreserved': unrelated_preserved,
              'failedExportRetentionPassed': failure_result.returncode == 0,
              'failedExportValidation': failure_result.stdout.strip(),
              'limitation': 'Acknowledged snapshots survive process termination; pending data and storage failures are outside this acknowledgement.'}
    (output/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
