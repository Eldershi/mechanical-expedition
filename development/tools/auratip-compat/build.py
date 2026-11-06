"""Build AuraTip compatibility with OELib 0.3.1 and Forge input events."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('--input', type=Path, required=True)
parser.add_argument('--output-dir', type=Path, required=True)
parser.add_argument('--java-home', type=Path, required=True)
parser.add_argument('--asm-root', type=Path, required=True)
args = parser.parse_args()
expected = '1a9ccdf39b05eb34ccf246e9409b7fe68051e367a25b5f83dada8f63e15f55ff'
if hashlib.sha256(args.input.read_bytes()).hexdigest() != expected:
    raise RuntimeError('Unexpected AuraTip input archive')
args.output_dir.mkdir(parents=True, exist_ok=True)
classes = args.output_dir / 'classes'
classes.mkdir(exist_ok=True)
cp = ':'.join(str(args.asm_root / name / '9.8' / (name + '-9.8.jar'))
              for name in ('asm', 'asm-tree', 'asm-commons'))
source = Path(__file__).with_name('AuraTipEventPatch.java')
subprocess.run([str(args.java_home / 'bin/javac'), '--release', '17', '-cp', cp,
                '-d', str(classes), str(source)], check=True)
target = args.output_dir / args.input.name
subprocess.run([str(args.java_home / 'bin/java'), '-cp', str(classes) + ':' + cp,
                'AuraTipEventPatch', str(args.input), str(target)], check=True)
with zipfile.ZipFile(args.input) as original, zipfile.ZipFile(target) as patched:
    changed = [name for name in original.namelist() if original.read(name) != patched.read(name)]
    if set(changed) != {'cc/sighs/auratip/handler/ClientEventHandler.class',
                        'cc/sighs/auratip/handler/ClientInputHandler.class'}:
        raise RuntimeError('Unexpected archive changes')
report = {'file': target.name, 'upstreamSha256': expected,
          'patchedSha256': hashlib.sha256(target.read_bytes()).hexdigest(),
          'changedZipMembers': changed, 'oelib': '0.3.1'}
(args.output_dir / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
