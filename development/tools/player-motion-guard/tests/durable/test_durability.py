#!/usr/bin/env python3
"""Verify real file-force acknowledgements across SIGKILL, tail recovery and bounded retention."""
from pathlib import Path
import argparse
import json
import os
import queue
import shutil
import subprocess
import threading
import time

BASE = Path(__file__).resolve().parent
TOOL = BASE.parents[1]
PROJECT = TOOL.parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New disposable test output directory')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    classes = output / 'classes'
    classes.mkdir()
    gson = PROJECT / 'servers/cmi-expedition/instance/libraries/com/google/code/gson/gson/2.10/gson-2.10.jar'
    if not gson.is_file():
        gson = Path.home() / 'Library/Application Support/Swift Craft Launcher/meta/libraries/com/google/code/gson/gson/2.10/gson-2.10.jar'
    sources = [TOOL / 'src/expedition/motionguard/diagnostics' / name for name in
               ('DiagnosticsConfig.java', 'PlayerSnapshot.java', 'DurableJsonLog.java')]
    sources.append(BASE / 'DurableLogProbe.java')
    subprocess.run(['javac', '--release', '17', '-cp', str(gson), '-d', str(classes), *map(str, sources)], check=True)
    classpath = os.pathsep.join(map(str, (classes, gson)))

    def probe(directory, mode, kill):
        process = subprocess.Popen(['java', '-Xmx128m', '-cp', classpath, 'DurableLogProbe', str(directory), mode],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        lines = queue.Queue()
        transcript = []

        def consume():
            for line in process.stdout:
                transcript.append(line)
                lines.put(line)

        reader = threading.Thread(target=consume, daemon=True)
        reader.start()
        deadline = time.monotonic() + 15
        acknowledgement = None
        while time.monotonic() < deadline:
            try:
                line = lines.get(timeout=.2)
            except queue.Empty:
                if process.poll() is not None:
                    break
                continue
            if line.startswith('FORCED_ACK '):
                acknowledgement = json.loads(line.split(' ', 1)[1])
                if kill:
                    process.kill()
                break
        if acknowledgement is None:
            process.kill()
            raise AssertionError('No forced acknowledgement: ' + ''.join(transcript))
        process.wait(timeout=10)
        reader.join(timeout=2)
        (output / (mode + '-console.log')).write_text(''.join(transcript))
        return acknowledgement, process.returncode

    logs = output / 'durable'
    first, code = probe(logs, 'kill', True)
    assert code == -9
    marker = json.loads((logs / 'state.json').read_text())
    assert marker['lastContiguousForcedSequence'] >= first['lastContiguousForcedSequence']
    confirmed = logs / 'events' / marker['lastForcedFile']
    rows = [json.loads(line) for line in confirmed.read_text().splitlines()]
    assert any(row['sequence'] == first['lastContiguousForcedSequence'] for row in rows)
    assert rows[0]['data']['number'] == 'NaN'
    with confirmed.open('ab') as handle:
        handle.write(b'{"unfinished":')
    recovered, code = probe(logs, 'recover', True)
    assert code == -9 and recovered['recoveredIncompleteTailFiles'] >= 1
    assert recovered['previousBootId'] == first['bootId']
    rotation, code = probe(output / 'rotation', 'rotation', False)
    assert code == 0
    files = list((output / 'rotation/events').glob('*.jsonl'))
    assert len(files) <= 4 and sum(path.stat().st_size for path in files) <= 16384
    oversized, code = probe(output / 'oversize', 'oversize', False)
    assert code == 0 and oversized['droppedOversizeRecords'] == 1
    assert oversized['lastAcceptedSequence'] == oversized['lastContiguousForcedSequence'] == 2
    failed, code = probe(output / 'writefailure', 'writefailure', False)
    assert code == 0 and failed['firstLostSequence'] == 2 and failed['lastContiguousForcedSequence'] == 1
    for mode, prefix in (('unforcedfailure', 0), ('unforcedprefixfailure', 1)):
        abandoned, code = probe(output / mode, mode, False)
        assert code == 0 and abandoned['lastForcedSequence'] == prefix + 3
        assert abandoned['firstLostSequence'] == prefix + 2
        assert abandoned['firstUnconfirmedClosedFileSequence'] == prefix + 1
        assert abandoned['lastContiguousForcedSequence'] == prefix
        assert abandoned['unconfirmedClosedFileRecords'] == 1
        marker = json.loads((output / mode / 'state.json').read_text())
        assert marker['lastContiguousForcedSequence'] == prefix
        confirmed = output / mode / 'events' / marker['lastForcedFile']
        assert any(json.loads(line)['sequence'] == prefix + 3 for line in confirmed.read_text().splitlines())
    receipt, code = probe(output / 'receiptfailure', 'receiptfailure', False)
    assert code == 0 and receipt['markerFailures'] >= 1
    result = {'killAfterForcedAckPassed': True, 'incompleteTailRecoveryPassed': True,
              'boundedRotationPassed': True, 'oversizeNotAcknowledgedPassed': True,
              'writeFailureGapNotAcknowledgedPassed': True, 'receiptFailureBlockedAcknowledgementPassed': True,
              'abandonedUnforcedFileNotAcknowledgedPassed': True,
              'abandonedUnforcedFilePreservesEarlierConfirmedPrefixPassed': True,
              'forcedSequence': first['lastContiguousForcedSequence']}
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
