#!/usr/bin/env python3
"""Read-only receipt: new payload present and previous mod files unchanged."""
import hashlib
import json
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
before = json.loads((PACKAGE / 'evidence/active-before.json').read_text())
manifest = json.loads((PACKAGE / 'client-manifest.json').read_text())
root = Path(before['activeClient'])


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


changed = [row['file'] for row in before['mods']
           if digest(root / 'mods' / row['file']) != row['sha256']]
payload = [{'path': row['path'], 'passed': digest(root / row['path']) == row['afterSha256']}
           for row in manifest['operations']]
catalogs = {rel: digest(root / rel) == wanted
            for rel, wanted in manifest['protectedCatalogs'].items()}
result = {'activeClient': str(root), 'previousModCount': len(before['mods']),
          'currentModCount': len(list((root / 'mods').glob('*.jar'))),
          'changedPreviousMods': changed, 'payload': payload,
          'protectedCatalogs': catalogs,
          'passed': not changed and all(row['passed'] for row in payload) and all(catalogs.values())}
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if result['passed'] else 1)
