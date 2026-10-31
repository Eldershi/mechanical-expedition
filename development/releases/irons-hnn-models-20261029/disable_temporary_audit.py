"""Keep the one-off validation source as an inert backup, never reload anything."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent.parent
REL = Path('kubejs/server_scripts/expedition/IronsHnnAudit.js')
ACTIVE = (Path.home() / 'Library/Application Support/Swift Craft Launcher/profiles/机械远征-CMI-迁移测试')
parser = argparse.ArgumentParser()
parser.add_argument('--active-client', action='store_true')
args = parser.parse_args()
roots = [ACTIVE] if args.active_client else [PROJECT / 'servers/cmi-expedition/instance', PROJECT / 'servers/cmi-expedition/deployment', PROJECT / 'clients/cmi-expedition/overlay']
expected = hashlib.sha256((ROOT / 'payload' / REL).read_bytes()).hexdigest()
rows = []
for root in roots:
    source = root / REL
    dest = source.with_name(source.name + '.disabled')
    if source.exists():
        assert hashlib.sha256(source.read_bytes()).hexdigest() == expected, source
        assert not dest.exists(), dest
        source.rename(dest)
    assert dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == expected
    rows.append(str(dest))
name = 'active-client-audit-disabled.json' if args.active_client else 'workspace-audit-disabled.json'
(ROOT / name).write_text(json.dumps({'disabled': rows, 'sha256': expected}, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'disabledAuditCopies': len(rows), 'modelsChanged': 0}))
