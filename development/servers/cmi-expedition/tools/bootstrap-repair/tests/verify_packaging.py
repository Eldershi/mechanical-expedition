#!/usr/bin/env python3
"""Read/compile the packaging source without importing it or rebuilding its large zip."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOOLS = Path(__file__).resolve().parents[1]
EXPECTED_HASHES = {
    "server.jar": "975ea80508343d522aaa9fc834e3f0cd52c4d92810946a59efb705d7f6007336",
    "server-upstream-20261017.jar": "d019d815868d451e57bdb965174b8443ec361336e84e9c41abc41a6c627bacd1",
}
EXPECTED_ARGS = ["-Xms4G", "-Xmx12G", "-XX:+UseG1GC", "-XX:ActiveProcessorCount=6",
                 "-Dsun.net.client.defaultConnectTimeout=10000",
                 "-Dsun.net.client.defaultReadTimeout=10000"]


def parsed(path):
    text = path.read_text(encoding="utf-8")
    compile(text, str(path), "exec")
    return ast.parse(text, filename=str(path))


package = parsed(ROOT / "package_server.py")
generated = next(node.value for node in ast.walk(package)
                 if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == "generated"
                         for target in node.targets))
assert isinstance(generated, ast.Dict)
entries = {ast.literal_eval(key): value for key, value in zip(generated.keys, generated.values)}
rows = []
for name in ("server.jar", "server-upstream-20261017.jar", "user_jvm_args.txt"):
    expected = ast.parse(f"(ROOT / 'deployment/{name}').read_bytes()", mode="eval").body
    assert ast.dump(entries[name]) == ast.dump(expected), (name, ast.unparse(entries[name]))
    # Evaluate only these three exact, already-checked file reads; never import package_server.
    blob = eval(compile(ast.Expression(entries[name]), "<checked-package-entry>", "eval"),
                {"__builtins__": {}, "ROOT": ROOT})
    digest = hashlib.sha256(blob).hexdigest()
    if name in EXPECTED_HASHES:
        assert digest == EXPECTED_HASHES[name], (name, digest)
    rows.append({"archivePath": name, "source": str(ROOT / "deployment" / name),
                 "bytes": len(blob), "sha256": digest})

prepare = parsed(ROOT / "prepare_server.py")
expected_write = ast.parse("(SERVER/'user_jvm_args.txt').write_bytes("
                           "(ROOT/'deployment/user_jvm_args.txt').read_bytes())", mode="eval").body
assert any(ast.dump(node) == ast.dump(expected_write) for node in ast.walk(prepare))
canonical = (ROOT / "deployment/user_jvm_args.txt").read_bytes()
assert canonical.decode().splitlines() == EXPECTED_ARGS
assert (ROOT / "instance/user_jvm_args.txt").read_bytes() == canonical
assert (ROOT / "deployment/panel_jvm_args.txt").read_text().split() == EXPECTED_ARGS
instance_hash = hashlib.sha256((ROOT / "instance/server.jar").read_bytes()).hexdigest()
assert instance_hash == EXPECTED_HASHES["server-upstream-20261017.jar"]
report = {"passed": True, "fullZipBuildExecuted": False, "productionOrRemoteAccess": False,
          "sourceSyntaxChecks": ["package_server.py", "prepare_server.py"],
          "generatedEntries": rows, "canonicalJvmArgs": EXPECTED_ARGS,
          "prepareReadsCanonicalDeploymentJvmArgs": True, "instanceArgsMatchDeployment": True,
          "panelArgsMatchDeployment": True, "instanceOriginalJarSha256": instance_hash}
output = TOOLS / "build/packaging-verification.json"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
