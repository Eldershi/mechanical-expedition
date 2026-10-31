#!/usr/bin/env python3
"""Offline integration checks against a fake Java console server only."""
import hashlib
import atexit
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
RUNS = BUILD / "test-runs"
JAVA = shutil.which("java")
ENV = os.environ.copy()
REMOVED_ENV_NAMES = []
for name in ("_JAVA_OPTIONS", "JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS"):
    if name in ENV:
        REMOVED_ENV_NAMES.append(name)
        del ENV[name]
RESULTS = []
ACTIVE = []


@atexit.register
def cleanup_test_processes():
    for process in ACTIVE:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def events(work):
    path = work / "events.txt"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def start(name, mode, extra=()):
    work = RUNS / name
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    shutil.copy2(BUILD / "server-bootstrap.jar", work / "server.jar")
    shutil.copy2(BUILD / "fake-server.jar", work / "server-upstream-20261017.jar")
    output = (work / "console.log").open("wb")
    command = [JAVA, "-Xms128M", "-Xmx18G",
               "-Duser.timezone=Asia/Shanghai", "-Duser.language=zh",
               "-Dexpedition.test.unicode=中文 字段 with spaces",
               "-Dexpedition.bootstrap.stopGraceMs=500",
               "-Dexpedition.bootstrap.termGraceMs=1500",
               "-jar", str(work / "server.jar"), mode, "nogui", "中文 参数", "--safeMode", *extra]
    process = subprocess.Popen(command, cwd=work, stdin=subprocess.PIPE,
                               stdout=output, stderr=subprocess.STDOUT, env=ENV)
    ACTIVE.append(process)
    deadline = time.monotonic() + 15
    while "jvm=" not in events(work) and time.monotonic() < deadline:
        if process.poll() is not None:
            break
        time.sleep(0.05)
    data = events(work)
    assert "jvm=" in data, (name, process.poll(), (work / "console.log").read_text())
    assert "heapMax=12884901888\n" in data, data
    assert "processors=6\n" in data, data
    assert "timezone=Asia/Shanghai\n" in data, data
    assert "language=zh\n" in data, data
    assert "customProperty=中文 字段 with spaces\n" in data, data
    assert "-Duser.timezone=Asia/Shanghai" in data, data
    assert "-Duser.language=zh" in data, data
    assert "-Dexpedition.test.unicode=中文 字段 with spaces" in data, data
    assert "expedition.bootstrap.stopGraceMs" not in data, data
    assert "expedition.bootstrap.termGraceMs" not in data, data
    assert f"cwd={work}\n" in data, data
    assert f"args=[{mode}, nogui, 中文 参数, --safeMode" in data, data
    child_pid = int(next(line.split("=", 1)[1] for line in data.splitlines() if line.startswith("pid=")))
    return work, process, output, child_pid


def finish(name, work, process, output, assertions, details=None):
    output.close()
    data = events(work)
    console = (work / "console.log").read_text(encoding="utf-8")
    assert "FAKE_READY " in console, console
    assert "FAKE_STDERR" in console, console
    assert "Max. Heap Size: 12.00G" in console, console
    for expected in assertions:
        assert expected in data, (name, expected, data)
    RESULTS.append({"test": name, "passed": True, "parentExitCode": process.returncode,
                    "details": details or {}, "events": str(work / "events.txt"),
                    "console": str(work / "console.log")})


def rss_bytes(pid):
    output = subprocess.check_output(["ps", "-o", "rss=", "-p", str(pid)], text=True)
    return int(output.strip()) * 1024


def assert_dead(pid):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)
    raise AssertionError(f"Child {pid} is still present after parent exit")


def main():
    RUNS.mkdir(parents=True, exist_ok=True)
    subprocess.run(["sh", str(ROOT / "build.sh")], check=True, env=ENV)
    first_hash = sha(BUILD / "server-bootstrap.jar")
    subprocess.run(["sh", str(ROOT / "build.sh")], check=True, env=ENV)
    assert sha(BUILD / "server-bootstrap.jar") == first_hash
    RESULTS.append({"test": "reproducible-build", "passed": True, "sha256": first_hash})

    work, process, output, child = start("console-stop-and-arguments", "console")
    parent_rss, child_rss = rss_bytes(process.pid), rss_bytes(child)
    assert parent_rss < 256 * 1024 * 1024, parent_rss
    assert child_rss < 512 * 1024 * 1024, child_rss
    process.communicate("say offline-probe\nstop\n".encode(), timeout=10)
    assert process.returncode == 0
    assert_dead(child)
    finish("console-stop-and-arguments", work, process, output,
           ["stdin=say offline-probe\n", "console-stop-saved\n", "shutdown-hook-saved\n"],
           {"parentRssBytes": parent_rss, "fakeChildRssBytes": child_rss,
            "parentMaxHeapGiB": 18, "childMaxHeapGiB": 12, "childInitialHeapGiB": 4,
            "explicitParentPropertiesPreserved": ["user.timezone=Asia/Shanghai", "user.language=zh",
                                                   "expedition.test.unicode=中文 字段 with spaces"],
            "bootstrapControlPropertiesFiltered": True})

    work, process, output, child = start("stdin-eof", "eof")
    process.communicate(b"say eof-probe\n", timeout=10)
    assert process.returncode == 0
    assert_dead(child)
    finish("stdin-eof", work, process, output, ["stdin=say eof-probe\n", "stdin-eof\n"])

    work, process, output, child = start("child-exit-code", "exit23")
    process.communicate(timeout=10)
    assert process.returncode == 23, process.returncode
    assert_dead(child)
    finish("child-exit-code", work, process, output, ["shutdown-hook-saved\n"])

    work, process, output, child = start("parent-sigterm-console-save", "console")
    began = time.monotonic()
    process.send_signal(signal.SIGTERM)
    process.wait(timeout=10)
    process.stdin.close()
    assert process.returncode in (143, -signal.SIGTERM), process.returncode
    assert_dead(child)
    finish("parent-sigterm-console-save", work, process, output,
           ["stdin=stop\n", "console-stop-saved\n", "shutdown-hook-saved\n"],
           {"shutdownSeconds": round(time.monotonic() - began, 3)})

    work, process, output, child = start("parent-sigterm-term-fallback", "ignore-stop")
    began = time.monotonic()
    process.send_signal(signal.SIGTERM)
    process.wait(timeout=10)
    process.stdin.close()
    assert process.returncode in (143, -signal.SIGTERM), process.returncode
    assert_dead(child)
    assert "console-stop-saved\n" not in events(work)
    finish("parent-sigterm-term-fallback", work, process, output,
           ["stdin=stop\n", "shutdown-hook-saved\n"],
           {"shutdownSeconds": round(time.monotonic() - began, 3)})

    work, process, output, child = start("parent-sigterm-full-stdin-pipe", "ignore-input")
    def flood():
        try:
            process.stdin.write(b"x" * (1024 * 1024))
            process.stdin.flush()
        except (BrokenPipeError, ValueError):
            pass
    flood_thread = threading.Thread(target=flood, daemon=True)
    flood_thread.start()
    time.sleep(0.3)
    began = time.monotonic()
    process.send_signal(signal.SIGTERM)
    process.wait(timeout=10)
    flood_thread.join(timeout=2)
    assert not flood_thread.is_alive(), "stdin writer remained blocked after child exit"
    try:
        process.stdin.close()
    except BrokenPipeError:
        pass
    assert process.returncode in (143, -signal.SIGTERM), process.returncode
    assert_dead(child)
    finish("parent-sigterm-full-stdin-pipe", work, process, output,
           ["shutdown-hook-saved\n"], {"shutdownSeconds": round(time.monotonic() - began, 3)})

    report = {"offlineOnly": True, "minecraftOrForgeStarted": False,
              "portsOrNetworkUsed": False, "productionFilesModified": False,
              "javaVersion": subprocess.run([JAVA, "-version"], capture_output=True,
                                             text=True, env=ENV).stderr.strip(),
              "testEnvironmentOptionVariablesRemoved": REMOVED_ENV_NAMES,
              "results": RESULTS, "allPassed": True}
    report_path = BUILD / "verification.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"allPassed": True, "checks": len(RESULTS), "report": str(report_path),
                      "artifact": str(BUILD / "server-bootstrap.jar"), "sha256": first_hash},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
