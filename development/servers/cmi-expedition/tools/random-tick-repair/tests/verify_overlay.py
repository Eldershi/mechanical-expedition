#!/usr/bin/env python3
"""Small offline overlay checks. Never import/run the full packager or prepare main."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
BUILD = Path(__file__).resolve().parents[1] / 'build'
BUILD.mkdir(exist_ok=True)
spec = importlib.util.spec_from_file_location('deployment_mod_overlays', ROOT/'deployment_mod_overlays.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
manifest = json.loads((ROOT/'deployment/server-patches.json').read_text())
overlays = helper.load_mod_overlays(ROOT)
selection = {row['file']:row for row in json.loads((ROOT/'evidence/mod-selection.json').read_text())['included']}
checks = []


def passed(name):
    checks.append({'check': name, 'passed': True})


def rejects(name, action):
    try:
        action()
    except ValueError:
        passed(name)
        return
    raise AssertionError('Unexpected input was accepted: ' + name)


trees = {}
for name in ('prepare_server.py', 'package_server.py', 'deployment_mod_overlays.py'):
    text = (ROOT/name).read_text()
    compile(text, str(ROOT/name), 'exec')
    trees[name] = ast.parse(text)
passed('changed Python sources compile without executing their main/top-level packaging code')

package_tree = trees['package_server.py']
source_function = next(node for node in package_tree.body if isinstance(node, ast.FunctionDef)
                       and node.name == 'source_for_packaged_file')
namespace = {'ROOT': ROOT, 'allowed_mods': selection, 'MOD_OVERLAYS': overlays,
             'source_for_mod_package': helper.source_for_mod_package}
exec(compile(ast.Module(body=[source_function], type_ignores=[]), '<package resolver only>', 'exec'), namespace)
generated = next(node.value for node in ast.walk(package_tree) if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == 'generated' for target in node.targets))
generated_entries = {ast.literal_eval(key): value for key, value in zip(generated.keys, generated.values)}
expected_manifest_read = ast.parse("(ROOT/'deployment/server-patches.json').read_bytes()", mode='eval').body
assert ast.dump(generated_entries['server-patches.json']) == ast.dump(expected_manifest_read)
assert any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
           and node.func.id == 'apply_mod_overlay' for node in ast.walk(trees['prepare_server.py']))
passed('packaging resolver uses overlays and zip includes the patch manifest; prepare calls overlay application')

client_rows = []
for name, overlay in overlays.items():
    source = ROOT/'instance/mods'/name
    assert helper.digest(source.read_bytes()) == overlay['upstreamSha256']
    client = ROOT.parents[1]/'clients/cmi-expedition/instance/mods'/name
    assert helper.digest(client.read_bytes()) == overlay['upstreamSha256']
    actual = namespace['source_for_packaged_file'](Path('mods')/name, source)
    assert actual == overlay['path']
    assert helper.digest(actual.read_bytes()) == overlay['patchedSha256']
    client_rows.append({'file': name, 'clientAndInstanceSha256': overlay['upstreamSha256'],
                        'packagedSha256': overlay['patchedSha256']})
passed('current upstream instance/selection packages the reviewed patched bytes; clients stay upstream')

with tempfile.TemporaryDirectory(prefix='overlay-test-', dir=BUILD) as temporary:
    fixture = Path(temporary)
    directory = fixture/'deployment/mods'
    directory.mkdir(parents=True)
    manifest_path = fixture/'deployment/server-patches.json'
    manifest_path.write_text(json.dumps(manifest))
    for name, overlay in overlays.items():
        shutil.copy2(overlay['path'], directory/name)
    fixture_overlays = helper.load_mod_overlays(fixture)
    for name, overlay in fixture_overlays.items():
        target = fixture/'prepared'/name
        target.parent.mkdir(exist_ok=True)
        target.write_bytes((ROOT/'instance/mods'/name).read_bytes())
        entry = copy.deepcopy(selection[name])
        helper.apply_mod_overlay(target, entry, fixture_overlays)
        assert entry['sha256'] == overlay['patchedSha256']
        assert entry['upstreamSha256'] == overlay['upstreamSha256']
        assert helper.digest(target.read_bytes()) == overlay['patchedSha256']
        assert entry['modIds'] == selection[name]['modIds']
        assert helper.source_for_mod_package(target, entry['sha256'], fixture_overlays) == overlay['path']
    passed('future prepare applies overlay and records upstream/patched hashes; its result also packages successfully')

    name = next(iter(fixture_overlays))
    target = fixture/'prepared'/name
    original_target = target.read_bytes()
    rejects('unknown selection hash rejected', lambda: helper.source_for_mod_package(target, '0'*64, fixture_overlays))
    target.write_bytes(b'unreviewed mod bytes')
    rejects('unknown package input bytes rejected', lambda: helper.source_for_mod_package(target, selection[name]['sha256'], fixture_overlays))
    rejects('unknown prepare input bytes rejected before overwrite', lambda: helper.apply_mod_overlay(target, copy.deepcopy(selection[name]), fixture_overlays))
    assert target.read_bytes() == b'unreviewed mod bytes'
    target.write_bytes(original_target)

    unknown = directory/'unregistered.jar'
    unknown.write_bytes(b'unknown')
    rejects('unregistered deployment mod rejected', lambda: helper.load_mod_overlays(fixture))
    unknown.unlink()
    reviewed = (directory/name).read_bytes()
    (directory/name).write_bytes(reviewed+b'changed')
    rejects('overlay hash drift rejected', lambda: helper.load_mod_overlays(fixture))
    (directory/name).unlink()
    rejects('missing overlay rejected', lambda: helper.load_mod_overlays(fixture))
    (directory/name).write_bytes(reviewed)
    bad_manifest = copy.deepcopy(manifest)
    bad_manifest['mods'][0]['file'] = '../escape.jar'
    manifest_path.write_text(json.dumps(bad_manifest))
    rejects('path traversal rejected', lambda: helper.load_mod_overlays(fixture))
    bad_manifest = copy.deepcopy(manifest)
    bad_manifest['mods'].append(copy.deepcopy(bad_manifest['mods'][0]))
    manifest_path.write_text(json.dumps(bad_manifest))
    rejects('duplicate manifest mod rejected', lambda: helper.load_mod_overlays(fixture))

assert manifest['status'] and manifest['validation']['sameFaultChunkSave'] == 'verified'
assert manifest['validation']['actualPlayerSession']
assert manifest['validation']['railwayAutomationPlayerTPS'] in {'pending_live_verification', 'verified'}
assert manifest['deferredRandomTickMitigationRemainsEnabled'] is True
assert len(overlays) == 3
for name, overlay in overlays.items():
    assert helper.digest((ROOT/'instance/mods'/name).read_bytes()) == overlay['upstreamSha256']
    assert helper.digest((ROOT.parents[1]/'clients/cmi-expedition/instance/mods'/name).read_bytes()) == overlay['upstreamSha256']
passed('all three production mod inputs remain upstream and current validation status is explicit')
report = {'passed': True, 'fullZipBuildExecuted': False, 'prepareMainExecuted': False,
          'remoteAccess': False, 'clientModsModified': False, 'instanceModsModified': False,
          'status': manifest['status'], 'actualPlayerSession': manifest['validation']['actualPlayerSession'],
          'railwayAutomationPlayerTPS': manifest['validation']['railwayAutomationPlayerTPS'],
          'mods': client_rows, 'checks': checks}
output = BUILD/'overlay-verification.json'
output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
