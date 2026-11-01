#!/usr/bin/env python3
"""Run real Forge player movement callbacks in a disposable loopback world."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import queue
import shutil
import subprocess
import threading
import time
from zipfile import ZipFile, ZIP_DEFLATED

BASE = Path(__file__).resolve().parent
TOOL = BASE.parents[1]
PROJECT = TOOL.parents[1]
DEFAULT_LIBRARIES = PROJECT / 'servers/cmi-expedition/instance/libraries'
DEFAULT_GUARD = TOOL / 'dist/expedition-player-motion-guard-1.1.0.jar'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', type=Path, required=True,
                        help='New disposable output directory; must not already exist')
    parser.add_argument('--client', type=Path, required=True,
                        help='Read-only client instance supplying the three test dependencies')
    parser.add_argument('--libraries', type=Path, default=DEFAULT_LIBRARIES,
                        help='Existing complete Forge 47.4.10 libraries directory')
    parser.add_argument('--guard', type=Path, default=DEFAULT_GUARD,
                        help='Built player motion guard JAR')
    parser.add_argument('--java', default='java', help='Java 17 executable')
    parser.add_argument('--javac', default='javac', help='Java 17 compiler executable')
    args = parser.parse_args()
    libraries = args.libraries.expanduser().resolve()
    client = args.client.expanduser().resolve()
    guard = args.guard.expanduser().resolve()
    runtime = args.runtime_root.expanduser().resolve()
    forge_relative = 'net/minecraftforge/forge/1.20.1-47.4.10'
    dependency_names = ['radium-mc1.20.1-0.12.4+git.26c9d8e.jar',
                        'alexscaves-2.0.2.jar', 'citadel-2.6.3-1.20.1.jar']
    required = [libraries / forge_relative / 'unix_args.txt', guard]
    required += [client / 'mods' / filename for filename in dependency_names]
    if missing := [str(path) for path in required if not path.is_file()]:
        parser.error('Missing required inputs: ' + ', '.join(missing))
    runtime.mkdir(parents=True, exist_ok=False)
    (runtime / 'libraries').symlink_to(libraries, target_is_directory=True)
    mods = runtime / 'mods'
    mods.mkdir()
    for filename in dependency_names:
        shutil.copy2(client / 'mods' / filename, mods / filename)
    shutil.copy2(guard, mods / guard.name)
    (runtime / 'config').mkdir()
    (runtime / 'config/lithium.properties').write_text('mixin.entity.collisions.movement=false\n')
    (runtime / 'eula.txt').write_text('eula=true\n')
    (runtime / 'server.properties').write_text('\n'.join([
        'server-ip=127.0.0.1', 'server-port=0', 'online-mode=false', 'enable-query=false', 'enable-rcon=false',
        'level-name=disposable-motion-probe', 'level-type=minecraft:flat', 'generate-structures=false',
        'generator-settings={"layers":[{"block":"minecraft:bedrock","height":1},{"block":"minecraft:dirt","height":2},{"block":"minecraft:grass_block","height":1}],"biome":"minecraft:plains"}',
        'view-distance=2', 'simulation-distance=2', 'spawn-protection=0', 'max-players=1',
        'motd=Disposable player motion validation', 'max-tick-time=60000', 'sync-chunk-writes=false', '',
    ]))
    classes = runtime / 'probe-classes'
    classes.mkdir(exist_ok=True)
    # The Forge server patch jar takes precedence over the unpatched SRG classes.
    primary = [libraries / 'net/minecraftforge/forge/1.20.1-47.4.10/forge-1.20.1-47.4.10-server.jar',
               libraries / 'net/minecraftforge/forge/1.20.1-47.4.10/forge-1.20.1-47.4.10-universal.jar']
    dependencies = [p for p in libraries.rglob('*.jar') if p not in primary]
    cp = os.pathsep.join(map(str, primary + dependencies))
    compile_result = subprocess.run([args.javac, '--release', '17', '-proc:none', '-cp', cp,
        '-d', str(classes), *map(str, (BASE/'src').rglob('*.java'))], text=True, capture_output=True)
    (runtime/'probe-compile.log').write_text(compile_result.stdout + compile_result.stderr)
    if compile_result.returncode:
        raise SystemExit(compile_result.stderr)
    with ZipFile(mods/'expedition-motion-probe-test-only.jar', 'w', ZIP_DEFLATED) as archive:
        for path in classes.rglob('*.class'):
            archive.write(path, path.relative_to(classes).as_posix())
        archive.writestr('META-INF/mods.toml', '''modLoader="javafml"
loaderVersion="[47,)"
license="All Rights Reserved"
[[mods]]
modId="expedition_motion_probe"
version="1.0.0"
displayName="Disposable Player Motion Probe"
description="Local test fixture only."
''')
    process = subprocess.Popen([args.java, '-Xms256M', '-Xmx2G', '-XX:ActiveProcessorCount=2',
        '-Dmixin.debug.export=true',
        '-Dsun.net.client.defaultConnectTimeout=5000', '-Dsun.net.client.defaultReadTimeout=5000',
        '@libraries/net/minecraftforge/forge/1.20.1-47.4.10/unix_args.txt', 'nogui'], cwd=runtime,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    lines = queue.Queue()
    transcript = []
    def read_output():
        with (runtime/'console.log').open('w') as output:
            for line in process.stdout:
                transcript.append(line)
                output.write(line)
                output.flush()
                lines.put(line)
    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    deadline = time.monotonic() + 180
    stopped = False
    while process.poll() is None and time.monotonic() < deadline:
        try:
            line = lines.get(timeout=1)
        except queue.Empty:
            continue
        if 'MOTION_PROBE_' in line:
            print(line.strip(), flush=True)
        if ('MOTION_PROBE_PASSED' in line or 'MOTION_PROBE_FAILED' in line) and not stopped:
            process.stdin.write('stop\n')
            process.stdin.flush()
            stopped = True
    if process.poll() is None:
        if not stopped:
            try:
                process.stdin.write('stop\n')
                process.stdin.flush()
            except BrokenPipeError:
                pass
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=10)
    reader.join(timeout=3)
    text = ''.join(transcript)
    report = {
        'guardSha256': digest(guard),
        'checks': [line.split('MOTION_PROBE_OK ', 1)[1].strip() for line in transcript if 'MOTION_PROBE_OK ' in line],
        'passed': 'MOTION_PROBE_PASSED' in text and 'MOTION_PROBE_FAILED' not in text and process.returncode == 0,
        'exitCode': process.returncode,
        'bindAddress': '127.0.0.1',
        'activeClientModified': False,
        'onlineServerModified': False,
        'radiumCollisionFallback': 'mixin.entity.collisions.movement=false',
    }
    (runtime/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
