"""Shared reviewed dedicated overrides for preparation and packaging."""
from pathlib import Path
import hashlib
import json

PRESERVE_REMOTE = (
    'kubejs/config/idle-pregeneration-20261020.json',
    'kubejs/config/idle-pregeneration-20261020-state.json',
    'kubejs/config/reset-player-spawn-20261018.json',
    'config/chunky/',
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def runtime_server_overlays(release):
    release = Path(release)
    manifest = release / 'evidence/csa-steamletters-compat/patch-manifest.json'
    if not manifest.is_file():
        return {}
    row = json.loads(manifest.read_text())
    client = release / row['patched']
    server = release / row['dedicatedServer']['file']
    if (client.is_symlink() or server.is_symlink() or
            digest(client) != row['patchedSha256'] or
            digest(server) != row['dedicatedServer']['sha256']):
        raise ValueError('CSA dedicated runtime overlay does not match reviewed manifest')
    return {client.name: {'path': server, 'upstreamSha256': row['patchedSha256'],
                          'patchedSha256': row['dedicatedServer']['sha256'],
                          'patchId': 'csa-steamletters-coexistence-dedicated-render-supplier-fix'}}


def live_server_additions(release):
    """Exact existing server-only FTB patch, absent from the client by design."""
    release = Path(release)
    name = 'expedition-ftb-action-announcements-1.0.0.jar'
    expected = 'f1eac3f9f1080aed47252d5381e35b4efa4085dde41df25142b7779cce75a231'
    path = release / 'evidence/live-before/mods' / name
    if not path.exists():
        return {}
    if path.is_symlink() or digest(path) != expected:
        raise ValueError('Live FTB action patch does not match captured production artifact')
    return {name: {'path': path, 'blob': path.read_bytes(), 'sha256': expected,
                   'modIds': ['expedition_ftb_action_announcements'],
                   'patchId': 'preserve-live-ftb-action-announcements'}}


def is_worldgen(relative):
    parts = Path(relative).parts
    return parts[:2] == ('kubejs', 'data') and bool(
        set(parts[3:-1]) & {'worldgen', 'dimension', 'dimension_type'})


def overlay_decision(relative, stage_exists):
    """Dedicated settings win; merged recipes, catalogs and quests stay newer."""
    rel = Path(relative).as_posix()
    if rel.startswith('config/ftbquests/'):
        return 'merged quest tree retained'
    if rel.startswith('config/') or is_worldgen(rel):
        return 'apply dedicated overlay'
    if rel.startswith('kubejs/'):
        return 'merged staging retained' if stage_exists else 'apply deployment-only addition'
    return 'outside deployment overlay scope'
