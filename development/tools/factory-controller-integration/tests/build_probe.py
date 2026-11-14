#!/usr/bin/env python3
"""Build a disposable Forge probe from caller-supplied libraries and test mods."""
import argparse
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile


def build(libraries, mods_directory, output, javac):
    source = Path(__file__).with_name('FactoryControllerProbe.java')
    libraries = libraries.resolve()
    mods_directory = mods_directory.resolve()
    output = output.resolve()
    libs = sorted(libraries.rglob('*.jar'))
    # Prefer the SRG game archive over raw game archives in the same installation.
    libs.sort(key=lambda p: (not p.name.endswith('-srg.jar'), str(p)))
    mods = sorted(mods_directory.glob('*.jar'))
    if not libs or not mods:
        raise ValueError('Expected Forge libraries and a populated isolated mods directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='factory-controller-probe-') as temporary:
        work = Path(temporary)
        classes = work / 'classes'
        classes.mkdir()
        nested_directory = work / 'nested'
        nested_directory.mkdir()
        nested = []

        def add_nested(blob, parent):
            with zipfile.ZipFile(io.BytesIO(blob)) as archive:
                for name in archive.namelist():
                    if not name.endswith('.jar'):
                        continue
                    raw = archive.read(name)
                    target = nested_directory / (parent + '--' + Path(name).name)
                    target.write_bytes(raw)
                    nested.append(target)
                    add_nested(raw, target.stem)

        for mod in mods:
            add_nested(mod.read_bytes(), mod.stem)
        classpath = os.pathsep.join(map(str, [*libs, *mods, *nested]))
        result = subprocess.run([javac, '--release', '17', '-proc:none', '-cp', classpath,
                                 '-d', str(classes), str(source)])
        if result.returncode:
            raise SystemExit(result.returncode)
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('META-INF/mods.toml',
                            'modLoader="javafml"\nloaderVersion="[47,)"\n'
                            'license="All Rights Reserved"\n[[mods]]\n'
                            'modId="expedition_factorycontroller_probe"\nversion="1.0"\n'
                            'displayName="Factory Controller isolated runtime probe"\n')
            archive.writestr('pack.mcmeta', json.dumps({'pack': {
                'pack_format': 15, 'description': 'Isolated runtime validation'}}))
            for path in sorted(classes.rglob('*.class')):
                archive.write(path, path.relative_to(classes).as_posix())
    print(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--libraries', '--libs', required=True, type=Path)
    parser.add_argument('--mods', required=True, type=Path)
    parser.add_argument('--output', '--out', required=True, type=Path)
    parser.add_argument('--javac', default='javac')
    args = parser.parse_args()
    build(args.libraries, args.mods, args.output, args.javac)
