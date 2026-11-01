#!/usr/bin/env python3
"""Verify full-pack startup, independent stall capture, SIGKILL persistence and restart."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import queue
import signal
import subprocess
import threading
import time
from zipfile import ZipFile, ZIP_DEFLATED

BASE = Path(__file__).resolve().parent


def json_file(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True, help='Prepared disposable full-pack directory')
    parser.add_argument('--java', default='java')
    parser.add_argument('--javac', default='javac')
    parser.add_argument('--heap', default='8G')
    args = parser.parse_args()
    runtime = args.runtime.resolve()
    properties = (runtime/'server.properties').read_text()
    if 'server-ip=127.0.0.1\n' not in properties or 'level-name=disposable-' not in properties:
        parser.error('Only an explicitly disposable loopback runtime is accepted')
    libraries = runtime/'libraries'
    classes = runtime/'probe-classes'
    classes.mkdir(exist_ok=False)
    forge = libraries/'net/minecraftforge/forge/1.20.1-47.4.10'
    primary = [forge/'forge-1.20.1-47.4.10-server.jar', forge/'forge-1.20.1-47.4.10-universal.jar']
    cp = os.pathsep.join(map(str, primary+[path for path in libraries.rglob('*.jar') if path not in primary]))
    compiled = subprocess.run([args.javac,'--release','17','-proc:none','-cp',cp,'-d',str(classes),
        *map(str,(BASE/'src').rglob('*.java'))], capture_output=True,text=True)
    (runtime/'probe-compile.log').write_text(compiled.stdout+compiled.stderr)
    if compiled.returncode:
        raise SystemExit(compiled.stderr)
    with ZipFile(runtime/'mods/expedition-diagnostics-probe-test-only.jar','w',ZIP_DEFLATED) as archive:
        for path in classes.rglob('*.class'):
            archive.write(path,path.relative_to(classes).as_posix())
        archive.writestr('META-INF/mods.toml','''modLoader="javafml"
loaderVersion="[47,)"
license="All Rights Reserved"
[[mods]]
modId="expedition_diagnostics_test"
version="1.0.0"
displayName="Disposable Diagnostics Probe"
displayTest="IGNORE_ALL_VERSION"
description="Local loopback test fixture only."
''')
    command=[args.java,'-Xms512M','-Xmx'+args.heap,'-XX:ActiveProcessorCount=4',
        '-Dsun.net.client.defaultConnectTimeout=5000','-Dsun.net.client.defaultReadTimeout=5000',
        '@libraries/net/minecraftforge/forge/1.20.1-47.4.10/unix_args.txt','nogui']
    diagnostics=runtime/'expedition-diagnostics'
    report={'passed':False,'modsIncludingTestProbe':len(list((runtime/'mods').glob('*.jar'))),
        'guardSha256':hashlib.sha256((runtime/'mods/expedition-player-motion-guard-1.1.0.jar').read_bytes()).hexdigest(),
        'productionWorldCopied':False,'bindAddress':'127.0.0.1','forcedTerminationTested':False}

    def launch(label):
        process=subprocess.Popen(command,cwd=runtime,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,text=True,bufsize=1)
        lines=queue.Queue()
        def read():
            with (runtime/(label+'-console.log')).open('w') as output:
                for line in process.stdout:
                    output.write(line);output.flush();lines.put(line)
        reader=threading.Thread(target=read,daemon=True);reader.start()
        return process,lines,reader

    def send(process,text):
        process.stdin.write(text+'\n');process.stdin.flush()

    process,lines,reader=launch('first-boot')
    ready=False; integrations_passed=False; first_receipt=None; initial_boot=None; incident_path=None
    deadline=time.monotonic()+480
    try:
        while process.poll() is None and time.monotonic()<deadline:
            try:
                line=lines.get(timeout=0.2)
                if 'Done (' in line and not ready:
                    ready=True;print('FULLPACK_READY',flush=True);send(process,'monitorprobe integrations')
                if 'MONITOR_RUNTIME_INTEGRATIONS_PASS' in line: integrations_passed=True
                if 'MONITOR_RUNTIME_INTEGRATIONS_FAIL' in line: raise AssertionError('Full-pack integration capture failed')
            except queue.Empty:
                pass
            if not ready:
                continue
            state=json_file(diagnostics/'state.json')
            receipt=json_file(diagnostics/'jfr/last-completed.json')
            spark_receipts=list((diagnostics/'spark').glob('*.receipt.json')) if (diagnostics/'spark').exists() else []
            if integrations_passed and state and receipt and spark_receipts:
                initial_boot=state['bootId'];first_receipt=receipt
                report['firstBootReady']=True
                report['carryOnAndCuriosCapturePassed']=True
                report['sparkArchiveConfirmedBeforeKill']=True
                print('FULLPACK_EXPORTS_CONFIRMED',flush=True)
                send(process,'monitorprobe stall')
                break
        if initial_boot is None:
            raise AssertionError('Full pack did not become ready with completed JFR and Spark exports')
        stall_began=False;deadline=time.monotonic()+20
        while process.poll() is None and time.monotonic()<deadline:
            try:
                if 'MONITOR_RUNTIME_STALL_BEGIN' in lines.get(timeout=0.2):stall_began=True;break
            except queue.Empty:pass
        if not stall_began:raise AssertionError('Test stall command did not run')
        deadline=time.monotonic()+14
        while time.monotonic()<deadline and process.poll() is None:
            for path in (diagnostics/'incidents').glob('*.jsonl'):
                text=path.read_text()
                if 'main_thread_stall' in text and 'FullpackProbe' in text and 'incident_complete' in text:
                    incident_path=path
                    break
            if incident_path:
                break
            time.sleep(0.1)
        if incident_path is None:
            raise AssertionError('Independent watchdog did not persist the blocked main thread')
        state=json_file(diagnostics/'state.json')
        if not state or state.get('lostWriteRecords',0) or state.get('droppedQueueRecords',0):
            raise AssertionError('Monitoring reported unpersisted events before kill')
        confirmed_sequence=state['lastContiguousForcedSequence']
        incident_hash=hashlib.sha256(incident_path.read_bytes()).hexdigest()
        print('FULLPACK_STALL_CAPTURE_FORCED',flush=True)
        os.kill(process.pid,signal.SIGKILL)
        process.wait(timeout=15);reader.join(timeout=3)
        report['firstExitCode']=process.returncode
        report['forcedTerminationTested']=process.returncode==-signal.SIGKILL
        report['independentWatchdogCapturedBeforeMainReturned']=True
        retained_state=json_file(diagnostics/'state.json')
        if not retained_state or retained_state['lastContiguousForcedSequence']<confirmed_sequence:
            raise AssertionError('Acknowledgement lost after SIGKILL')
        if hashlib.sha256(incident_path.read_bytes()).hexdigest()!=incident_hash:
            raise AssertionError('Forced incident changed after SIGKILL')
        malformed=0; found_sequence=False
        for path in (diagnostics/'events').glob('*.jsonl'):
            for line in path.read_bytes().splitlines(keepends=True):
                if not line.endswith(b'\n'):continue
                try:
                    event=json.loads(line)
                    if event.get('bootId')==initial_boot and event.get('sequence')==confirmed_sequence:found_sequence=True
                except ValueError:malformed+=1
        if malformed or not found_sequence:raise AssertionError('Confirmed event not readable')
        jfr=diagnostics/'jfr'/first_receipt['file']
        with jfr.open('rb') as stream:header=stream.read(4)
        if header!=b'FLR\0' or jfr.stat().st_size!=first_receipt['bytes']:
            raise AssertionError('Completed JFR lost after SIGKILL')
        for path in (diagnostics/'spark').glob('*.receipt.json'):
            metadata=json.loads(path.read_text()); profile=path.with_name(metadata['file'])
            if hashlib.sha256(profile.read_bytes()).hexdigest()!=metadata['sha256']:
                raise AssertionError('Completed Spark archive lost after SIGKILL')
        report.update(confirmedSequence=confirmed_sequence,confirmedEventRetained=True,
            completedJfrRetained=True,completedSparkRetained=True,incidentRetained=True)
    finally:
        if process.poll() is None:
            process.kill();process.wait(timeout=15)
        reader.join(timeout=3)
        (runtime/'fullpack-probe-result.json').write_text(json.dumps(report,indent=2)+'\n')

    process,lines,reader=launch('restart')
    ready=False; recovered=False; deadline=time.monotonic()+480
    try:
        while process.poll() is None and time.monotonic()<deadline:
            try:
                line=lines.get(timeout=0.2)
                if 'Done (' in line:ready=True
            except queue.Empty:pass
            state=json_file(diagnostics/'state.json')
            if ready and state and state.get('bootId')!=initial_boot and state.get('previousBootId')==initial_boot:
                if state.get('previousForcedSequence',0)<confirmed_sequence:
                    raise AssertionError('Restart did not recover the forced watermark')
                recovered=True;print('FULLPACK_RESTART_RECOVERED',flush=True);send(process,'stop');break
        if not recovered:raise AssertionError('Full-pack restart did not recover the previous boot')
        try:process.wait(timeout=35)
        except subprocess.TimeoutExpired:
            process.kill();process.wait(timeout=15)
            report['testShutdownNeededKillAfterSave']=True
        report['restartReady']=ready;report['previousWatermarkRecovered']=recovered
        report['restartExitCode']=process.returncode
        report['passed']=all(report.get(key,False) for key in ['carryOnAndCuriosCapturePassed','forcedTerminationTested','confirmedEventRetained',
            'completedJfrRetained','completedSparkRetained','incidentRetained','previousWatermarkRecovered'])
    finally:
        if process.poll() is None:process.kill();process.wait(timeout=15)
        reader.join(timeout=3)
        (runtime/'fullpack-probe-result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
