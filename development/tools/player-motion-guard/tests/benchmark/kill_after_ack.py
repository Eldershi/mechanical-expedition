#!/usr/bin/env python3
"""SIGKILL a real ten-player Forge workload only after its durable receipt."""
from pathlib import Path
import argparse
import importlib.util
import json
import os
import queue
import signal
import subprocess
import sys
import threading
import time

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('monitor_benchmark_helpers', BASE / 'run_benchmark.py')
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)


def forced_json(path, value):
    with path.open('w') as output:
        json.dump(value, output, indent=2)
        output.write('\n')
        output.flush()
        os.fsync(output.fileno())


def read_ack(runtime, target, expected_boot):
    path = runtime / 'expedition-diagnostics/state.json'
    if not path.is_file() or path.stat().st_size > 32768:
        return None
    try:
        state = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if (state.get('bootId') != expected_boot or state.get('lastContiguousForcedSequence', -1) < target
            or state.get('lostWriteRecords', 0) or state.get('droppedQueueRecords', 0)
            or state.get('droppedOversizeRecords', 0)):
        return None
    receipt = runtime / 'expedition-diagnostics/jfr/last-completed.json'
    if not receipt.is_file() or receipt.stat().st_size > 4096:
        return None
    try:
        jfr = json.loads(receipt.read_text())
        name = jfr.get('file', '')
        file = runtime / 'expedition-diagnostics/jfr' / name
        if Path(name).name != name or not file.is_file() or file.stat().st_size != jfr.get('bytes'):
            return None
    except (OSError, json.JSONDecodeError):
        return None
    return {'state': state, 'jfr': jfr}


def validate_confirmed_events(runtime, ack):
    boot, watermark = ack['state']['bootId'], ack['state']['lastContiguousForcedSequence']
    records = {}
    malformed = 0
    for path in sorted((runtime / 'expedition-diagnostics/events').glob('*.jsonl')):
        with path.open() as source:
            for line in source:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    malformed += 1
                    continue
                if event.get('bootId') == boot and 1 <= event.get('sequence', 0) <= watermark:
                    sequence = event['sequence']
                    if sequence in records:
                        raise AssertionError('Duplicate acknowledged event sequence')
                    records[sequence] = event
    if set(records) != set(range(1, watermark + 1)):
        raise AssertionError('An acknowledged contiguous JSONL sequence is missing')
    samples = []
    types = {}
    for record in records.values():
        kind = record.get('type', '')
        types[kind] = types.get(kind, 0) + 1
        if kind == 'state_batch':
            samples.extend(record.get('data', {}).get('states', []))
    return {'watermark': watermark, 'acknowledgedEventsRead': len(records),
            'stateSamplesRead': len(samples),
            'distinctPlayersRead': len({state['playerId'] for state in samples}),
            'eventTypes': types, 'unacknowledgedMalformedTailLines': malformed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New disposable runtime parent')
    parser.add_argument('--guard', type=Path, required=True)
    parser.add_argument('--client', type=Path, required=True)
    parser.add_argument('--spark', type=Path, required=True)
    parser.add_argument('--libraries', type=Path, default=helpers.DEFAULT_LIBRARIES)
    parser.add_argument('--java', default='java')
    parser.add_argument('--javac', default='javac')
    args = parser.parse_args()
    for key in ['output', 'guard', 'client', 'spark', 'libraries']:
        setattr(args, key, getattr(args, key).expanduser().resolve())
    if args.output.exists():
        parser.error('--output must be new')
    required = [args.guard, args.spark,
                args.libraries / 'net/minecraftforge/forge/1.20.1-47.4.10/unix_args.txt']
    required += [args.client / 'mods' / name for name in helpers.DEPENDENCIES]
    if missing := [p.name for p in required if not p.is_file()]:
        parser.error('Missing input: ' + ', '.join(missing))
    args.output.mkdir(parents=True)
    args.baseline_guard = args.monitor_config = None
    args.shared_mod = [args.spark]
    args.players, args.rounds, args.warmup_ticks, args.ticks = 10, 1, 200, 200
    fixture = helpers.compile_fixture(args, args.output)
    runtime = helpers.prepare(args, args.output, 1, 'monitor', fixture)
    command = [args.java, '-Xms1G', '-Xmx2G', '-XX:ActiveProcessorCount=2',
        '-Dsun.net.client.defaultConnectTimeout=5000', '-Dsun.net.client.defaultReadTimeout=5000',
        '-Dmonitorbench.players=10', '-Dmonitorbench.rounds=1', '-Dmonitorbench.warmupTicks=200',
        '-Dmonitorbench.measuredTicks=200', '-Dmonitorbench.scenarios=steady',
        '-Dmonitorbench.stallMillis=0', '-Dmonitorbench.mode=monitor',
        '@libraries/net/minecraftforge/forge/1.20.1-47.4.10/unix_args.txt', 'nogui']
    process = subprocess.Popen(command, cwd=runtime, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, bufsize=1)
    messages = queue.Queue()
    def reader():
        with (runtime / 'console.log').open('w') as output:
            for line in process.stdout:
                output.write(line)
                if 'MONITOR_BENCH_' in line:
                    output.flush()
                    messages.put(line[line.index('MONITOR_BENCH_'):].strip())
    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    window = ack = None
    passed_marker = False
    deadline = time.monotonic() + 240
    failure = None
    try:
        while process.poll() is None and time.monotonic() < deadline:
            try:
                marker = messages.get(timeout=.2)
            except queue.Empty:
                marker = ''
            if marker:
                print(marker[:180], flush=True)
            if marker.startswith('MONITOR_BENCH_WINDOW '):
                window = json.loads(marker.split(' ', 1)[1])
            elif marker.startswith('MONITOR_BENCH_FAILED'):
                raise AssertionError('Real player fixture failed before acknowledgement')
            elif marker.startswith('MONITOR_BENCH_PASSED'):
                passed_marker = True
            if passed_marker and window:
                status = window['diagnosticsStatusAfter']
                target = status['writer']['lastAcceptedSequence']
                ack = read_ack(runtime, target, status['bootId'])
                if ack:
                    ack['targetAcceptedSequenceFromLiveStatus'] = target
                    ack['guardSha256'] = helpers.sha(args.guard)
                    forced_json(args.output / 'acknowledgement-before-kill.json', ack)
                    # Deliberately never send stop, close, SIGTERM or a shutdown hook.
                    process.send_signal(signal.SIGKILL)
                    process.wait(timeout=10)
                    break
        if not ack or process.returncode != -signal.SIGKILL:
            raise AssertionError('No healthy contiguous receipt plus completed JFR before SIGKILL')
        event_proof = validate_confirmed_events(runtime, ack)
        if event_proof['distinctPlayersRead'] < 10 or event_proof['stateSamplesRead'] < 2000:
            raise AssertionError('Confirmed trajectory data does not cover ten real players')
        if 'server_stopping' in event_proof['eventTypes'] or 'server_stopped' in event_proof['eventTypes']:
            raise AssertionError('Graceful shutdown occurred before the crash test')
        # Use the existing real JFR artifact validator, in inspect mode only.
        source = helpers.PROJECT / 'tools/player-motion-guard/tests/jfr/JfrDurabilityProbe.java'
        classes = args.output / 'validator-classes'
        classes.mkdir()
        compiled = subprocess.run([args.javac, '--release', '17', '-cp', str(args.guard),
            '-d', str(classes), str(source)], capture_output=True, text=True, timeout=30)
        (args.output / 'validator-compile.log').write_text(compiled.stdout + compiled.stderr)
        if compiled.returncode:
            raise AssertionError('JFR inspector compilation failed')
        jfr_file = runtime / 'expedition-diagnostics/jfr' / ack['jfr']['file']
        inspected = subprocess.run([args.java, '-Xverify:all', '-cp', os.pathsep.join([str(classes), str(args.guard)]),
            'JfrDurabilityProbe', 'inspect', str(jfr_file)], capture_output=True, text=True, timeout=30)
        (args.output / 'jfr-inspection.log').write_text(inspected.stdout + inspected.stderr)
        if inspected.returncode or 'JFR_DURABILITY_VALID' not in inspected.stdout:
            raise AssertionError('Completed JFR failed the real RecordingFile reader after SIGKILL')
        result = {'passed': True, 'exitCode': process.returncode, 'noGracefulShutdownSent': True,
            'guardSha256': helpers.sha(args.guard), 'contiguousJsonl': event_proof,
            'jfrValidation': inspected.stdout.strip(), 'liveWindow': window,
            'postKillEvidence': helpers.diagnostics_evidence(runtime),
            'durabilityScope': 'Only records through the healthy captured contiguous force receipt and the completed JFR receipt; no claim for pending data or power loss.'}
    except Exception as error:
        failure = error
        result = {'passed': False, 'error': type(error).__name__ + ': ' + str(error),
                  'exitCode': process.returncode, 'acknowledgementCaptured': ack is not None}
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        thread.join(timeout=3)
    forced_json(args.output / 'result.json', result)
    print(json.dumps({k: result[k] for k in ['passed', 'exitCode']}, indent=2))
    if failure:
        raise SystemExit(str(failure))


if __name__ == '__main__':
    main()
