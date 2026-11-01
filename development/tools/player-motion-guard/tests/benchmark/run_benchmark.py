#!/usr/bin/env python3
"""Compare diagnostics on/off in fresh, serial, loopback-only Forge runtimes."""
from pathlib import Path
import argparse
import ctypes
import hashlib
import json
import os
import platform
import queue
import shutil
import sqlite3
import statistics
import subprocess
import threading
import time
from zipfile import ZipFile, ZIP_DEFLATED, is_zipfile

BASE = Path(__file__).resolve().parent
PROJECT = BASE.parents[3]
DEFAULT_LIBRARIES = PROJECT / 'servers/cmi-expedition/instance/libraries'
DEPENDENCIES = ['radium-mc1.20.1-0.12.4+git.26c9d8e.jar',
                'alexscaves-2.0.2.jar', 'citadel-2.6.3-1.20.1.jar']
DEFAULT_CONFIG = {
    'jfrEnabled': True, 'watchdogEnabled': True, 'sparkExportEnabled': True,
    'stateSampleEveryTicks': 1, 'equipmentCheckEveryTicks': 20,
    'statePersistEveryTicks': 20, 'ringSamplesPerPlayer': 1200,
    'maxTrackedPlayers': 32, 'queueCapacity': 2048,
    'flushIntervalMillis': 1000, 'forceIntervalMillis': 1000,
    'eventFileBytes': 8388608, 'totalLogBytes': 134217728, 'maxLogFiles': 16,
    'watchdogStallMillis': 10000, 'watchdogRepeatMillis': 30000,
    'maxIncidentFiles': 8, 'maxIncidentBytes': 33554432,
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def directory_bytes(root):
    count = size = 0
    if root.exists():
        for path in root.rglob('*'):
            if path.is_file() and not path.is_symlink():
                count += 1
                size += path.stat().st_size
    return {'files': count, 'bytes': size}


class DarwinUsage(ctypes.Structure):
    _fields_ = [('uuid', ctypes.c_uint8 * 16)] + [(name, ctypes.c_uint64) for name in [
        'user_time', 'system_time', 'pkg_idle_wkups', 'interrupt_wkups', 'pageins',
        'wired_size', 'resident_size', 'phys_footprint', 'proc_start_abstime',
        'proc_exit_abstime', 'child_user_time', 'child_system_time',
        'child_pkg_idle_wkups', 'child_interrupt_wkups', 'child_pageins',
        'child_elapsed_abstime', 'diskio_bytesread', 'diskio_byteswritten']]


def process_io(pid):
    """OS byte counters, not the misleading net size of retained rotating files."""
    try:
        if platform.system() == 'Darwin':
            library = ctypes.CDLL('/usr/lib/libproc.dylib', use_errno=True)
            library.proc_pid_rusage.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
            library.proc_pid_rusage.restype = ctypes.c_int
            usage = DarwinUsage()
            if library.proc_pid_rusage(pid, 2, ctypes.byref(usage)) != 0:
                raise OSError(ctypes.get_errno(), 'proc_pid_rusage')
            return {'source': 'macOS proc_pid_rusage RUSAGE_INFO_V2',
                    'readBytes': usage.diskio_bytesread, 'writeBytes': usage.diskio_byteswritten}
        if platform.system() == 'Linux':
            values = dict(line.split(':', 1) for line in Path(f'/proc/{pid}/io').read_text().splitlines())
            return {'source': 'Linux /proc/pid/io', 'readBytes': int(values['read_bytes']),
                    'writeBytes': int(values['write_bytes']), 'writeSyscallBytes': int(values['wchar'])}
    except (OSError, ValueError, KeyError) as error:
        return {'source': 'unavailable', 'error': str(error)}
    return {'source': 'unavailable', 'error': 'Unsupported OS'}


def io_delta(after, before):
    if after.get('source') != before.get('source') or after.get('source') == 'unavailable':
        return {'source': 'unavailable', 'before': before, 'after': after}
    return {'source': after['source'], **{key: max(0, after[key] - before[key])
            for key in ['readBytes', 'writeBytes', 'writeSyscallBytes'] if key in after and key in before}}


def host_sample(child_pid):
    result = {'timeMillis': int(time.time() * 1000), 'logicalCpuCount': os.cpu_count(),
              'loadAverage': list(os.getloadavg())}
    try:
        output = subprocess.check_output(['ps', '-axo', 'pid=,pcpu=,comm='], text=True, timeout=3)
        others = []
        for line in output.splitlines():
            parts = line.strip().split(None, 2)
            if len(parts) != 3:
                continue
            pid, cpu, name = int(parts[0]), float(parts[1]), Path(parts[2]).name
            if pid not in {child_pid, os.getpid()}:
                others.append({'pid': pid, 'cpuPercent': cpu, 'name': name[:96]})
        result['otherCpuPercentSum'] = sum(p['cpuPercent'] for p in others)
        result['otherTopCpu'] = sorted(others, key=lambda p: p['cpuPercent'], reverse=True)[:8]
        result['otherJava'] = [p for p in others if p['name'].lower() == 'java']
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        result['error'] = type(error).__name__
    return result


def audit_database(runtime):
    database = runtime / 'database.db'
    if not database.is_file():
        return {'exists': False}
    connection = sqlite3.connect(f'file:{database}?mode=ro', uri=True, timeout=5)
    try:
        tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {'exists': True,
                'counts': {name: connection.execute('SELECT COUNT(*) FROM "' + name.replace('"', '""') + '"').fetchone()[0]
                           for name in tables},
                'integrity': [row[0] for row in connection.execute('PRAGMA integrity_check')],
                'bytes': database.stat().st_size,
                'sidecars': {p.name: p.stat().st_size for p in runtime.glob('database.db-*')}}
    finally:
        connection.close()


def diagnostics_evidence(runtime):
    root = runtime / 'expedition-diagnostics'
    types, players = {}, set()
    samples = batches = malformed = 0
    for path in sorted((root / 'events').glob('*.jsonl')):
        with path.open() as source:
            for line in source:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    malformed += 1
                    continue
                kind = event.get('type', '')
                types[kind] = types.get(kind, 0) + 1
                if kind == 'state_batch':
                    states = event.get('data', {}).get('states', [])
                    batches += 1
                    samples += len(states)
                    players.update(state.get('playerId') for state in states if state.get('playerId'))
    jfr_receipt = root / 'jfr/last-completed.json'
    jfr = {'receiptExists': jfr_receipt.is_file()}
    if jfr_receipt.is_file():
        receipt = json.loads(jfr_receipt.read_text())
        name = receipt.get('file', '')
        target = root / 'jfr' / name
        valid_name = Path(name).name == name and name.endswith('.jfr')
        exists = valid_name and target.is_file()
        magic = False
        if exists:
            with target.open('rb') as source:
                magic = source.read(4) == b'FLR\0'
        jfr.update({'referencedFileExists': exists, 'jfrMagicValid': magic,
                    'sizeMatchesReceipt': exists and target.stat().st_size == receipt.get('bytes')})
    spark = []
    for path in sorted((root / 'spark').glob('*.receipt.json')):
        receipt = json.loads(path.read_text())
        name = receipt.get('file', '')
        target = root / 'spark' / name
        valid = (Path(name).name == name and target.is_file()
                 and target.stat().st_size == receipt.get('bytes') and sha(target) == receipt.get('sha256'))
        spark.append({'receipt': path.name, 'verifiedArtifact': valid})
    return {'eventTypes': types, 'stateBatchRecords': batches, 'stateSamples': samples,
            'distinctPlayersInStateBatches': len(players), 'malformedEventLines': malformed,
            'jfr': jfr, 'sparkReceipts': spark}


def compile_fixture(args, output):
    classes = output / 'fixture-classes'
    classes.mkdir()
    primary = [args.libraries / 'net/minecraftforge/forge/1.20.1-47.4.10/forge-1.20.1-47.4.10-server.jar',
               args.libraries / 'net/minecraftforge/forge/1.20.1-47.4.10/forge-1.20.1-47.4.10-universal.jar']
    dependencies = [p for p in args.libraries.rglob('*.jar') if p not in primary and is_zipfile(p)]
    command = [args.javac, '--release', '17', '-proc:none', '-cp',
               os.pathsep.join(map(str, primary + dependencies)), '-d', str(classes),
               *map(str, sorted((BASE / 'src').rglob('*.java')))]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    (output / 'fixture-compile.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError('Fixture compilation failed; see fixture-compile.log')
    artifact = output / 'expedition-monitor-bench-test-only.jar'
    with ZipFile(artifact, 'w', ZIP_DEFLATED) as archive:
        for path in sorted(classes.rglob('*.class')):
            archive.write(path, path.relative_to(classes).as_posix())
        archive.writestr('META-INF/mods.toml', '''modLoader="javafml"
loaderVersion="[47,)"
license="All Rights Reserved"
[[mods]]
modId="expedition_monitor_bench"
version="1.0.0"
displayName="Disposable Monitoring Benchmark"
description="Test-only real Forge tick workload."
''')
        archive.writestr('pack.mcmeta', json.dumps({'pack': {
            'pack_format': 15, 'description': 'Disposable monitoring benchmark fixture'}}))
    return artifact


def prepare(args, root, index, mode, fixture):
    runtime = root / f'run-{index:02d}-{mode}'
    runtime.mkdir()
    (runtime / 'libraries').symlink_to(args.libraries, target_is_directory=True)
    mods = runtime / 'mods'
    mods.mkdir()
    for filename in DEPENDENCIES:
        shutil.copy2(args.client / 'mods' / filename, mods / filename)
    selected_guard = args.baseline_guard if mode == 'baseline' and args.baseline_guard else args.guard
    shutil.copy2(selected_guard, mods / selected_guard.name)
    for shared in args.shared_mod:
        target = mods / shared.name
        if target.exists() and sha(target) != sha(shared):
            raise RuntimeError('Shared mod filename collision: ' + shared.name)
        shutil.copy2(shared, target)
    shutil.copy2(fixture, mods / fixture.name)
    (runtime / 'config').mkdir()
    config = dict(DEFAULT_CONFIG)
    if args.monitor_config:
        config.update(json.loads(args.monitor_config.read_text()))
    config['enabled'] = mode == 'monitor'
    (runtime / 'config/expedition-diagnostics.json').write_text(json.dumps(config, indent=2) + '\n')
    if any(path.name.startswith('spark-') for path in args.shared_mod):
        (runtime / 'config/spark').mkdir()
        (runtime / 'config/spark/config.json').write_text(json.dumps({
            'backgroundProfiler': mode == 'monitor', 'backgroundProfilerEngine': 'java',
            'backgroundProfilerInterval': 20,
        }, indent=2) + '\n')
    (runtime / 'config/lithium.properties').write_text('mixin.entity.collisions.movement=false\n')
    (runtime / 'eula.txt').write_text('eula=true\n')
    (runtime / 'server.properties').write_text('\n'.join([
        'server-ip=127.0.0.1', 'server-port=0', 'online-mode=false', 'enable-query=false',
        'enable-rcon=false', 'level-name=benchmark-flat', 'level-seed=873141',
        'level-type=minecraft:flat', 'generate-structures=false',
        'generator-settings={"layers":[{"block":"minecraft:bedrock","height":1},{"block":"minecraft:dirt","height":2},{"block":"minecraft:grass_block","height":1}],"biome":"minecraft:plains"}',
        'view-distance=2', 'simulation-distance=2', 'spawn-protection=0',
        f'max-players={max(10, args.players)}', 'max-tick-time=60000',
        'motd=Disposable monitoring benchmark', 'sync-chunk-writes=false', '',
    ]))
    return runtime


def run_runtime(args, runtime, mode):
    properties = {
        'players': args.players, 'rounds': args.rounds, 'warmupTicks': args.warmup_ticks,
        'measuredTicks': args.ticks, 'stallMillis': args.stall_ms,
        'itemNbtBytes': args.item_nbt_bytes, 'mode': mode, 'scenarios': args.scenarios,
    }
    command = [args.java, '-Xms1G', '-Xmx2G', f'-XX:ActiveProcessorCount={args.processors}',
               '-Dsun.net.client.defaultConnectTimeout=5000', '-Dsun.net.client.defaultReadTimeout=5000']
    command += [f'-Dmonitorbench.{key}={value}' for key, value in properties.items()]
    command += ['@libraries/net/minecraftforge/forge/1.20.1-47.4.10/unix_args.txt', 'nogui']
    process = subprocess.Popen(command, cwd=runtime, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, bufsize=1)
    messages = queue.Queue()
    windows = []
    starts = {}
    host_samples = []
    stop_host_sampler = threading.Event()
    def sample_host():
        while not stop_host_sampler.is_set():
            host_samples.append(host_sample(process.pid))
            stop_host_sampler.wait(5)
    host_thread = threading.Thread(target=sample_host, daemon=True)
    host_thread.start()
    def read_output():
        with (runtime / 'console.log').open('w') as destination:
            for line in process.stdout:
                destination.write(line)
                if 'MONITOR_BENCH_' in line:
                    destination.flush()
                    # Sample while the child is alive, at its own measurement boundaries.
                    snapshot = {'io': process_io(process.pid),
                                'diagnostics': directory_bytes(runtime / 'expedition-diagnostics'),
                                'runtimeLogs': directory_bytes(runtime / 'logs')}
                    messages.put((line.rstrip(), snapshot))
    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    approximate_ticks = args.rounds * len(args.scenarios.split(',')) * (args.warmup_ticks + args.ticks)
    deadline = time.monotonic() + 240 + approximate_ticks / 20.0 * 2.0
    passed = failed = stop_sent = False
    while process.poll() is None and time.monotonic() < deadline:
        try:
            line, snapshot = messages.get(timeout=1)
        except queue.Empty:
            continue
        marker = line[line.index('MONITOR_BENCH_'):]
        print(f'{runtime.name}: {marker[:180]}', flush=True)
        if marker.startswith('MONITOR_BENCH_BEGIN '):
            starts[marker.split(' ', 1)[1]] = snapshot
        elif marker.startswith('MONITOR_BENCH_WINDOW '):
            row = json.loads(marker.split(' ', 1)[1])
            first = starts.get(row['window'], {})
            row['processDiskIo'] = io_delta(snapshot['io'], first.get('io', {}))
            row['diagnosticsBefore'] = first.get('diagnostics')
            row['diagnosticsAfter'] = snapshot['diagnostics']
            row['runtimeLogsBefore'] = first.get('runtimeLogs')
            row['runtimeLogsAfter'] = snapshot['runtimeLogs']
            windows.append(row)
        elif marker.startswith('MONITOR_BENCH_PASSED'):
            passed = True
        elif marker.startswith('MONITOR_BENCH_FAILED'):
            failed = True
        if (passed or failed) and not stop_sent:
            process.stdin.write('stop\n')
            process.stdin.flush()
            stop_sent = True
    if process.poll() is None:
        if not stop_sent:
            try:
                process.stdin.write('stop\n')
                process.stdin.flush()
            except BrokenPipeError:
                pass
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
    reader.join(timeout=5)
    stop_host_sampler.set()
    host_thread.join(timeout=4)
    (runtime / 'host-samples.json').write_text(json.dumps(host_samples, indent=2) + '\n')
    selected_guard = args.baseline_guard if mode == 'baseline' and args.baseline_guard else args.guard
    report = {
        'mode': mode, 'guardSha256': sha(selected_guard), 'exitCode': process.returncode,
        'passed': passed and not failed and process.returncode == 0,
        'windows': windows, 'diagnosticsFinal': directory_bytes(runtime / 'expedition-diagnostics'),
        'scope': 'Ten or more ordinary ServerPlayers run doTick once per real server tick; only outgoing network packets are discarded.',
        'allocationCaveat': 'Main thread allocation exact; live-thread sum excludes threads that exited before the endpoint.',
        'ioCaveat': 'OS process counters cover all child JVM writes; retained file bytes are reported separately and are not write throughput.',
        'hostInterference': {
            'sampleCount': len(host_samples),
            'maxOtherCpuPercentSum': max((s.get('otherCpuPercentSum', 0) for s in host_samples), default=0),
            'otherJavaObserved': any(s.get('otherJava') for s in host_samples),
            'samplingNote': 'Process names and CPU only; no command arguments. CPU percentages use 100 per logical core.',
        },
    }
    report['griefLoggerDatabase'] = audit_database(runtime)
    report['diagnosticsEvidence'] = diagnostics_evidence(runtime)
    if mode == 'monitor':
        evidence = report['diagnosticsEvidence']
        required_samples = sum(row['players'] * row['ticks'] for row in windows)
        report['stateBatchPersistenceVerified'] = (evidence['stateBatchRecords'] > 0
            and evidence['stateSamples'] >= required_samples > 0
            and evidence['distinctPlayersInStateBatches'] >= args.players
            and evidence['malformedEventLines'] == 0)
        report['passed'] = report['passed'] and report['stateBatchPersistenceVerified']
        if args.require_exports:
            status = windows[-1]['diagnosticsStatusAfter'] if windows else {}
            spark_status, jfr_status = status.get('spark', {}), status.get('jfr', {})
            report['periodicExportsVerified'] = (spark_status.get('confirmed', 0) >= 1
                and spark_status.get('deleted', 0) >= 1 and jfr_status.get('dumpCount', 0) >= 2
                and any(row['verifiedArtifact'] for row in evidence['sparkReceipts'])
                and evidence['jfr'].get('referencedFileExists')
                and evidence['jfr'].get('jfrMagicValid') and evidence['jfr'].get('sizeMatchesReceipt'))
            report['passed'] = report['passed'] and report['periodicExportsVerified']
    if any('grieflogger' in path.name.lower() for path in args.shared_mod):
        audit = report['griefLoggerDatabase']
        measured_block_actions = sum(window['realBlockPlaceBreakPairs'] * 2 for window in windows)
        report['griefLoggerWorkloadVerified'] = (audit.get('integrity') == ['ok']
            and audit.get('counts', {}).get('blocks', 0) >= measured_block_actions > 0)
        report['passed'] = report['passed'] and report['griefLoggerWorkloadVerified']
    (runtime / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def summarize(reports):
    summaries = []
    for scenario in sorted({row['scenario'] for report in reports for row in report['windows']}):
        grouped = {mode: [row for report in reports if report['mode'] == mode
                         for row in report['windows'] if row['scenario'] == scenario]
                   for mode in ['baseline', 'monitor']}
        row = {'scenario': scenario}
        for mode, windows in grouped.items():
            if not windows:
                continue
            row[mode] = {
                'windows': len(windows),
                'medianTickP50Ms': statistics.median(w['tickWallNs']['p50'] / 1e6 for w in windows),
                'medianTickP95Ms': statistics.median(w['tickWallNs']['p95'] / 1e6 for w in windows),
                'worstTickMs': max(w['tickWallNs']['max'] / 1e6 for w in windows),
                'medianProcessCpuMsPerTick': statistics.median(w['processCpuNs'] / w['ticks'] / 1e6 for w in windows),
                'medianMainAllocatedBytesPerTick': statistics.median(w['mainThreadAllocatedBytes'] / w['ticks'] for w in windows),
                'medianGcMillis': statistics.median(w['gcTimeMillis'] for w in windows),
                'medianProcessWriteBytes': statistics.median(w['processDiskIo']['writeBytes'] for w in windows
                    if 'writeBytes' in w['processDiskIo']) if any('writeBytes' in w['processDiskIo'] for w in windows) else None,
            }
        if 'baseline' in row and 'monitor' in row:
            row['monitorMinusBaselineP95Ms'] = row['monitor']['medianTickP95Ms'] - row['baseline']['medianTickP95Ms']
            row['monitorMinusBaselineCpuMsPerTick'] = row['monitor']['medianProcessCpuMsPerTick'] - row['baseline']['medianProcessCpuMsPerTick']
        summaries.append(row)
    return summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New results directory; never an installed instance')
    parser.add_argument('--guard', type=Path, required=True, help='Monitoring add-on JAR; reused in baseline unless --baseline-guard is given')
    parser.add_argument('--baseline-guard', type=Path, help='Optional old protection-only JAR for the baseline')
    parser.add_argument('--shared-mod', type=Path, action='append', default=[],
                        help='Identical additional mod in both modes; repeat for GriefLogger and its dependencies')
    parser.add_argument('--client', type=Path, required=True, help='Read-only dependency source instance')
    parser.add_argument('--libraries', type=Path, default=DEFAULT_LIBRARIES)
    parser.add_argument('--monitor-config', type=Path, help='Optional production configuration overrides')
    parser.add_argument('--order', default='baseline,monitor', help='Serial mode order; use baseline,monitor,monitor,baseline for balanced repetitions')
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--players', type=int, default=10)
    parser.add_argument('--warmup-ticks', type=int, default=200)
    parser.add_argument('--ticks', type=int, default=400)
    parser.add_argument('--scenarios', default='steady,incident')
    parser.add_argument('--stall-ms', type=int, default=150, help='One intentional long tick per incident window')
    parser.add_argument('--item-nbt-bytes', type=int, default=1024)
    parser.add_argument('--processors', type=int, default=2)
    parser.add_argument('--java', default='java')
    parser.add_argument('--javac', default='javac')
    parser.add_argument('--prepare-only', action='store_true', help='Compile and prepare; do not launch Forge')
    parser.add_argument('--require-exports', action='store_true',
                        help='Require confirmed+source-cleaned Spark archive and at least two completed JFR dumps')
    args = parser.parse_args()
    for key in ['output', 'guard', 'baseline_guard', 'client', 'libraries', 'monitor_config']:
        if getattr(args, key) is not None:
            setattr(args, key, getattr(args, key).expanduser().resolve())
    args.shared_mod = [p.expanduser().resolve() for p in args.shared_mod]
    if args.players < 10 or args.rounds < 1 or args.warmup_ticks < 40 or args.ticks < 100:
        parser.error('Require players>=10, rounds>=1, warmup-ticks>=40, ticks>=100')
    order = args.order.split(',')
    if set(order) - {'baseline', 'monitor'} or not {'baseline', 'monitor'}.issubset(order):
        parser.error('--order must contain baseline and monitor only, with both modes present')
    required = [args.guard, args.libraries / 'net/minecraftforge/forge/1.20.1-47.4.10/unix_args.txt']
    if args.baseline_guard:
        required.append(args.baseline_guard)
    required += args.shared_mod
    required += [args.client / 'mods' / name for name in DEPENDENCIES]
    if missing := [p.name for p in required if not p.is_file()]:
        parser.error('Missing required inputs: ' + ', '.join(missing))
    if args.output.exists():
        parser.error('--output must not already exist')
    args.output.mkdir(parents=True)
    fixture = compile_fixture(args, args.output)
    plan = {'order': order, 'rounds': args.rounds, 'players': args.players,
            'warmupTicksPerWindow': args.warmup_ticks, 'measuredTicksPerWindow': args.ticks,
            'scenarios': args.scenarios.split(','), 'guardSha256': sha(args.guard),
            'baselineGuardSha256': sha(args.baseline_guard or args.guard),
            'sharedModSha256': {p.name: sha(p) for p in args.shared_mod},
            'fixtureSha256': sha(fixture), 'dependencySha256': {
                name: sha(args.client / 'mods' / name) for name in DEPENDENCIES},
            'diagnosticsConfigDefaults': DEFAULT_CONFIG,
            'sparkConfigByMode': {'baseline': {'backgroundProfiler': False},
                                 'monitor': {'backgroundProfiler': True, 'backgroundProfilerEngine': 'java',
                                             'backgroundProfilerInterval': 20}},
            'preparedOnly': args.prepare_only}
    runtimes = [(prepare(args, args.output, i + 1, mode, fixture), mode) for i, mode in enumerate(order)]
    (args.output / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    if args.prepare_only:
        print('BENCHMARK_PREPARED_NO_FORGE_STARTED', flush=True)
        return
    reports = []
    for runtime, mode in runtimes:
        report = run_runtime(args, runtime, mode)
        reports.append(report)
        if not report['passed']:
            break
    output = {'plan': plan, 'passed': len(reports) == len(order) and all(x['passed'] for x in reports),
              'comparisons': summarize(reports), 'runs': reports,
              'limitations': ['Minimal Forge dependency graph plus explicitly listed identical shared mods, not full production modpack or real network clients.',
                              'Incident windows include the same intentional stall in both modes.',
                              'Startup, per-window warmup and shutdown are excluded from tick distributions.',
                              'Results require review; no automatic universal overhead pass threshold.']}
    (args.output / 'comparison.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({'passed': output['passed'], 'comparisons': output['comparisons']}, indent=2))
    raise SystemExit(0 if output['passed'] else 1)


if __name__ == '__main__':
    main()
