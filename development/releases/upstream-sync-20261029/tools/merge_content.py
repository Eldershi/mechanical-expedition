#!/usr/bin/env python3
"""Merge upstream content into the staged Expedition instance only."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[3]
RELEASE = Path(__file__).resolve().parents[1]
STAGE = RELEASE / 'staging'
UP = RELEASE / 'upstream'
ACTIVE = (Path.home() / 'Library/Application Support/Swift Craft Launcher/profiles/机械远征-CMI-迁移测试')
BASE_ZIP = ROOT / 'clients/cmi-beta/downloads/CMI-beta-inner-test.zip'
BASE_FILES = RELEASE / 'base-files'
EVIDENCE = RELEASE / 'evidence'
spec = importlib.util.spec_from_file_location('ftb_snbt', ROOT / 'clients/cmi-expedition/tools/ftb_snbt.py')
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)
MISSING = object()
PREFIXES = (
    'kubejs/server_scripts/event/', 'kubejs/server_scripts/data/worldgen/',
    'kubejs/server_scripts/data/loots/', 'kubejs/server_scripts/loot/',
    'kubejs/assets/', 'kubejs/client_scripts/', 'kubejs/data/cmi/structures/',
)


class Number(str):
    pass


class TypedParser(parser.Parser):
    def value(self):
        self.skip()
        if self.text[self.pos] not in '{}[]\"\'':
            token = self.token()
            if token in ('true', 'false'):
                return token == 'true'
            if re.fullmatch(r'[+-]?(?:\d*\.\d+|\d+\.?)(?:[eE][+-]?\d+)?[bBsSlLfFdD]?', token):
                return Number(token)
            return token
        return super().value()


def loads(text):
    p = TypedParser(text)
    result = p.value()
    p.skip()
    assert p.pos == len(text)
    return result


def snbt(value, depth=0):
    tab, child = '\t' * depth, '\t' * (depth + 1)
    if isinstance(value, Number):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        if not value:
            return '[ ]'
        return '[\n' + '\n'.join(child + snbt(v, depth + 1) for v in value) + '\n' + tab + ']'
    if isinstance(value, dict):
        if not value:
            return '{ }'
        return '{\n' + '\n'.join(child + (k if re.fullmatch(r'[\w.+-]+', k) else snbt(k)) + ': ' + snbt(v, depth + 1) for k, v in value.items()) + '\n' + tab + '}'
    raise TypeError(type(value))


def normalized(blob):
    return blob.replace(b'\r\n', b'\n') if blob is not None else None


def digest(blob):
    return hashlib.sha256(blob).hexdigest() if blob is not None else None


def git_blob(blob):
    return hashlib.sha1(b'blob ' + str(len(blob)).encode() + b'\0' + blob).hexdigest()


def base_content(path, base_zip, base_entry):
    if base_entry is None:
        return None, 'absent_at_fixed_base'
    cached = BASE_FILES / path
    if cached.is_file():
        blob = cached.read_bytes()
        # Text tools may normalize line endings/add one trailing newline.
        if not path.endswith(('.js', '.snbt', '.json')):
            assert git_blob(blob) == base_entry['sha'], path
        return blob, 'fixed_a87_source_cache'
    current = ACTIVE / path
    if current.is_file():
        blob = current.read_bytes()
        if git_blob(blob) == base_entry['sha']:
            return blob, 'active_bytes_verified_equal_to_fixed_a87_blob'
    name = 'overrides/' + path
    if name in base_zip.namelist():
        blob = base_zip.read(name)
        assert git_blob(blob) == base_entry['sha'], ('Package ZIP is not fixed a87 baseline', path)
        return blob, 'original_package_verified_equal_to_fixed_a87_blob'
    raise ValueError('Need fixed a87 source for ' + path)


def three_way(base, local, upstream):
    if local == base:
        return copy.deepcopy(upstream)
    if upstream == base or local == upstream:
        return copy.deepcopy(local)
    if all(isinstance(v, dict) for v in (base, local, upstream)):
        result = {}
        for key in dict.fromkeys([*local, *upstream]):
            b, l, u = base.get(key, MISSING), local.get(key, MISSING), upstream.get(key, MISSING)
            if l is MISSING:
                if b is MISSING:
                    result[key] = copy.deepcopy(u)
            elif u is MISSING:
                if b is MISSING or l != b:
                    result[key] = copy.deepcopy(l)
            elif b is MISSING:
                result[key] = copy.deepcopy(l)
            else:
                result[key] = three_way(b, l, u)
        return result
    if all(isinstance(v, list) for v in (base, local, upstream)):
        keyed = lambda xs: all(isinstance(v, dict) and isinstance(v.get('id'), str) for v in xs)
        if all(keyed(v) for v in (base, local, upstream)):
            b = {v['id']: v for v in base}
            l = {v['id']: v for v in local}
            u = {v['id']: v for v in upstream}
            combined = three_way(b, l, u)
            return [combined[k] for k in dict.fromkeys([*u, *l]) if k in combined]
    # A local edit to dependencies or prose is intentional; do not reinstate
    # deleted early progression gates or overwrite Expedition's wording.
    return copy.deepcopy(local)


def node_map(docs):
    out = {}
    for filename, doc in docs.items():
        for q in doc.get('quests', []):
            qid = q['id'].upper()
            assert qid not in out, ('duplicate quest', qid, filename)
            out[qid] = (filename, q)
    return out


def walk(value):
    if isinstance(value, dict):
        yield value
        for v in value.values():
            yield from walk(v)
    elif isinstance(value, list):
        for v in value:
            yield from walk(v)


def merge_quests(base_zip, manifest):
    prefix = 'config/ftbquests/quests/chapters/'
    base = {}
    tree = json.loads((ROOT / 'clients/cmi-beta/downloads/github-tree.json').read_text())
    for entry in tree['tree']:
        name = entry['path']
        if entry['type'] == 'blob' and name.startswith(prefix) and name.endswith('.snbt'):
            blob, _ = base_content(name, base_zip, entry)
            base[Path(name).name] = loads(blob.decode('utf-8-sig'))
    local = {f.name: loads(f.read_text()) for f in (ACTIVE / prefix).glob('*.snbt')}
    upstream = {f.name: loads(f.read_text()) for f in (UP / prefix).glob('*.snbt')}
    bq, lq, uq = node_map(base), node_map(local), node_map(upstream)
    allowed_files = set(local) | (set(upstream) - set(base))
    result = {}
    for filename in allowed_files:
        if filename in local and filename in upstream:
            result[filename] = three_way(base.get(filename, {}), local[filename], upstream[filename])
        else:
            result[filename] = copy.deepcopy(local.get(filename, upstream.get(filename)))
        result[filename]['quests'] = []

    # Known upstream replacement of the chemical reactor quest. Keep the
    # Expedition linked-quest nodes, and redirect their target after merging.
    aliases = {'5486A9D8E0073EAB': '2B95E0E6947D013C'}
    intentionally_removed = set(bq) - set(lq)
    preserved_local_additions = []
    removed_unchanged_upstream = []
    for qid in dict.fromkeys([*uq, *lq]):
        if qid in intentionally_removed:
            continue
        if qid in lq and qid in uq:
            lf, l = lq[qid]
            uf, u = uq[qid]
            bf, b = bq.get(qid, (lf, {}))
            target = uf if lf == bf and uf in allowed_files else lf
            merged = three_way(b, l, u)
        elif qid in lq:
            target, merged = lq[qid]
            if qid in bq and (merged == bq[qid][1] or qid in aliases):
                removed_unchanged_upstream.append(qid)
                continue
            merged = copy.deepcopy(merged)
            if qid not in bq:
                preserved_local_additions.append(qid)
        else:
            target, merged = uq[qid]
            if target not in allowed_files:
                continue
            merged = copy.deepcopy(merged)
        if target in result:
            result[target]['quests'].append(merged)

    # Derive direct item-ID migrations from same-ID tasks and rewards. Only
    # unambiguous namespace IDs are accepted; prose and tags are not rewritten.
    candidates = {}
    def strings_at_same_keys(a, b):
        if isinstance(a, dict) and isinstance(b, dict):
            for key in a.keys() & b.keys():
                yield from strings_at_same_keys(a[key], b[key])
        elif isinstance(a, list) and isinstance(b, list):
            if all(isinstance(v, dict) and 'id' in v for v in a + b):
                bb = {v['id']: v for v in b}
                for v in a:
                    if v['id'] in bb:
                        yield from strings_at_same_keys(v, bb[v['id']])
        elif isinstance(a, str) and isinstance(b, str) and a != b:
            pat = r'[a-z0-9_.-]+:[a-z0-9_./-]+'
            if re.fullmatch(pat, a) and re.fullmatch(pat, b):
                candidates.setdefault(a, set()).add(b)
    for qid in bq.keys() & uq.keys():
        strings_at_same_keys(bq[qid][1], uq[qid][1])
    item_aliases = {k: next(iter(v)) for k, v in candidates.items() if len(v) == 1 and
                    (k.startswith(('steampowered:', 'create_steam_ages:', 'cmi:')) or next(iter(v)).startswith('steam_letters:'))}
    item_aliases.update({
        'cmi:steam_hammer': 'steam_letters:steam_hammer',
        'cmi:advanced_spout': 'steam_letters:advanced_spout',
        'cmi:bronze_casing': 'steam_letters:bronze_casing',
        'steampowered:pressurized_gas_container': 'steam_letters:empty_steam_container',
        'steampowered:bronze_steam_engine': 'steam_letters:bronze_steam_engine',
    })
    valid = {q['id'].upper() for d in result.values() for q in d['quests']}
    changed_refs, removed_deps = [], []
    def rewrite(value, path=''):
        if isinstance(value, dict):
            for key in list(value):
                v = value[key]
                if key in ('quest', 'linked_quest') and isinstance(v, str) and v.upper() in aliases:
                    target = aliases[v.upper()]
                    if target in valid:
                        changed_refs.append({'path': path, 'old': v, 'new': target})
                        value[key] = target
                elif key == 'dependencies' and isinstance(v, list):
                    kept = []
                    for dep in v:
                        mapped = aliases.get(dep.upper(), dep) if isinstance(dep, str) else dep
                        if isinstance(mapped, str) and mapped.upper() not in valid:
                            removed_deps.append({'path': path, 'dependency': dep})
                        else:
                            kept.append(mapped)
                    value[key] = kept
                elif isinstance(v, str) and v in item_aliases and key in ('item', 'icon', 'id'):
                    value[key] = item_aliases[v]
                else:
                    rewrite(v, path + '/' + key)
        elif isinstance(value, list):
            for i, v in enumerate(value):
                rewrite(v, path + '/' + str(i))
    for filename, doc in result.items():
        rewrite(doc, filename)
        if filename in local and doc == local[filename]:
            blob = (ACTIVE / prefix / filename).read_bytes()
        else:
            blob = (snbt(doc) + '\n').encode()
            assert loads(blob.decode()) == doc
        (STAGE / prefix / filename).write_bytes(blob)
        before = (ACTIVE / prefix / filename).read_bytes() if filename in local else None
        if blob != before:
            manifest['files'].append({'path': prefix + filename, 'action': 'quest_three_way_and_reference_migration',
                                      'beforeSha256': digest(before), 'afterSha256': digest(blob)})
    # Preserve all original Expedition chapters, chapter groups, data and
    # reward tables; only changed stock chapters and new upstream chapters merge.
    for qid in set(lq) - set(bq):
        assert qid in valid, ('lost Expedition quest', qid)
    ids = []
    for doc in result.values():
        ids.extend(n['id'].upper() for n in walk(doc) if isinstance(n.get('id'), str) and re.fullmatch(r'[0-9A-Fa-f]{16}', n['id']))
    dup = sorted({x for x in ids if ids.count(x) > 1})
    assert not dup, ('duplicate object IDs', dup)
    dangling = []
    for filename, doc in result.items():
        for n in walk(doc):
            for key in ('linked_quest',):
                if isinstance(n.get(key), str) and n[key].upper() not in valid:
                    dangling.append({'file': filename, 'quest': n[key]})
    # Existing unrelated dangling references may exist; do not introduce any.
    old_valid = set(lq)
    old_dangling = {(f, n['linked_quest']) for f, d in local.items() for n in walk(d)
                    if isinstance(n.get('linked_quest'), str) and n['linked_quest'].upper() not in old_valid}
    introduced = [x for x in dangling if (x['file'], x['quest']) not in old_dangling]
    assert not introduced, ('new dangling links', introduced)
    manifest['quests'] = {
        'chaptersBefore': len(local), 'chaptersAfter': len(result),
        'questsBefore': len(lq), 'questsAfter': len(valid),
        'localAddedQuestCountPreserved': len(set(lq) - set(bq)),
        'intentionallyRemovedEarlyQuestCount': len(intentionally_removed),
        'intentionallyDeletedChapterFilesNotRestored': sorted(set(base) - set(local)),
        'newUpstreamChapterFiles': sorted(set(result) - set(local)),
        'upstreamRemovedUnchangedQuestIds': removed_unchanged_upstream,
        'redirectedLinks': changed_refs, 'removedDanglingDependencies': removed_deps,
        'remainingPreexistingDanglingLinks': dangling, 'itemAliases': item_aliases,
        'duplicateObjectIds': dup,
    }


def merge_pack(path, base_blob, local_blob, upstream_blob, manifest):
    def entries(blob):
        if blob is None:
            return {}
        with ZipFile(io.BytesIO(blob)) as z:
            return {n: z.read(n) for n in z.namelist() if not n.endswith('/')}
    b, l, u = entries(base_blob), entries(local_blob), entries(upstream_blob)
    merged, conflicts = {}, []
    for name in dict.fromkeys([*u, *l]):
        bb, ll, uu = b.get(name), l.get(name), u.get(name)
        if ll == bb:
            if uu is not None:
                merged[name] = uu
        elif uu == bb or ll == uu:
            if ll is not None:
                merged[name] = ll
        elif ll is None:
            if bb is None and uu is not None:
                merged[name] = uu
        elif uu is None:
            merged[name] = ll
        else:
            try:
                if name.endswith(('.json', '.mcmeta')):
                    value = three_way(json.loads(bb) if bb else {}, json.loads(ll), json.loads(uu))
                    merged[name] = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
                else:
                    merged[name] = ll
                    conflicts.append(name)
            except (ValueError, UnicodeError):
                merged[name] = ll
                conflicts.append(name)
    output = io.BytesIO()
    with ZipFile(output, 'w', ZIP_DEFLATED) as z:
        for name, blob in merged.items():
            z.writestr(name, blob)
    manifest['resourcePacks'].append({'path': path, 'entriesBefore': len(l), 'entriesAfter': len(merged),
                                      'preservedLocalConflicts': conflicts,
                                      'localAddedEntriesPreserved': sorted(set(l) - set(b))})
    return output.getvalue()


def main():
    assert STAGE.is_dir() and UP.is_dir()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    manifest = {'scope': list(PREFIXES) + ['config/ftbquests/', 'config/paxi/resourcepacks/'],
                'activeInstanceModified': False, 'files': [], 'resourcePacks': [], 'decisions': []}
    inventory = json.loads((ROOT / 'evidence/upstream-review-20261029/file-inventory.json').read_text())
    with ZipFile(BASE_ZIP) as base_zip:
        names = set(base_zip.namelist())
        for item in inventory:
            path = item['path']
            if not path.startswith(PREFIXES) and not path.startswith('config/paxi/resourcepacks/'):
                continue
            src, dst, current = UP / path, STAGE / path, ACTIVE / path
            base_blob, base_source = base_content(path, base_zip, item.get('base'))
            local_blob = current.read_bytes() if current.is_file() else None
            up_blob = src.read_bytes() if src.is_file() else None
            action = 'adopt_upstream'
            if path.startswith('config/paxi/resourcepacks/') and path.endswith('.zip'):
                if local_blob is None and base_blob is not None:
                    output, action = None, 'preserve_intentionally_removed_resource_pack'
                    manifest['decisions'].append({'path': path, 'reason': 'Already removed from active Expedition instance; do not restore an upstream GUI pack over the local GUI design.'})
                else:
                    output = merge_pack(path, base_blob, local_blob, up_blob, manifest)
                    action = 'resource_pack_entry_three_way'
            elif normalized(local_blob) == normalized(base_blob):
                output = up_blob
            elif normalized(up_blob) == normalized(base_blob) or normalized(local_blob) == normalized(up_blob):
                output, action = local_blob, 'preserve_local'
            elif path == 'kubejs/client_scripts/jei/HideItem.js':
                output = up_blob.replace(b'\thideItemFromJEI("@pipez_optimizer")\r\n', b'').replace(b'\thideItemFromJEI("@pipez_optimizer")\n', b'')
                action = 'upstream_plus_preserved_optimizer_removal'
            elif base_blob is not None and local_blob is not None and up_blob is not None:
                try:
                    with tempfile.TemporaryDirectory() as td:
                        fs = [Path(td) / n for n in ('local', 'base', 'upstream')]
                        for f, blob in zip(fs, (local_blob, base_blob, up_blob)):
                            f.write_bytes(normalized(blob))
                        merged = subprocess.run(['git', 'merge-file', '-p', *map(str, fs)], capture_output=True)
                    if merged.returncode != 0:
                        raise ValueError('text conflict')
                    output, action = merged.stdout, 'line_three_way'
                except (ValueError, UnicodeError):
                    output, action = local_blob, 'preserve_local_conflict'
            else:
                output, action = local_blob, 'preserve_local_conflict'
            if output is None:
                dst.unlink(missing_ok=True)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(output)
            manifest['files'].append({'path': path, 'action': action, 'baseSource': base_source, 'beforeSha256': digest(local_blob), 'afterSha256': digest(output)})
        merge_quests(base_zip, manifest)

    # KubeJS foodEaten exposes the consumed item/player, not a hand property.
    food = STAGE / 'kubejs/server_scripts/event/functional/server/FoodEaten.js'
    text = food.read_text().replace('let { player, level, hand } = event', 'let { player, level } = event')
    text = text.replace('if (hand === InteractionHand.MAIN_HAND && !level.isClientSide()) {',
                        'if (!level.isClientSide()) {')
    food.write_text(text)
    manifest['decisions'].append({'path': str(food.relative_to(STAGE)), 'reason': 'Consumed event is already emitted once per completed food consumption; remove unavailable hand property so either hand works.'})

    radiation = STAGE / 'kubejs/server_scripts/event/functional/server/RadioactiveItems.js'
    radiation.write_text('''// Expedition compatibility: schedule by the individual player, never a shared counter.
(() => {
const radiationManager = Java.loadClass('mekanism.api.radiation.IRadiationManager').INSTANCE
PlayerEvents.tick(event => {
    const { player, level } = event
    if (level.isClientSide() || player.isCreative() || player.isFake() || player.isSpectator()) return
    if (player.tickCount % 10 !== 0) return
    let hasRadioactive = false
    for (let stack of player.inventory.items) {
        if (!stack.isEmpty() && stack.hasTag('cmi:radioactive_items')) {
            hasRadioactive = true
            break
        }
    }
    if (hasRadioactive) {
        radiationManager.radiate(player, 0.00000001)
    }
})
})()
''')
    manifest['decisions'].append({'path': str(radiation.relative_to(STAGE)), 'reason': 'Keep upstream late material radiation mechanic, replace global player tick counter and stale tag snapshot with per-player scheduling and live tag checks.'})
    for row in manifest['files']:
        f = STAGE / row['path']
        row['afterSha256'] = digest(f.read_bytes() if f.is_file() else None)
    (EVIDENCE / 'scope-manifest-content.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'files': len(manifest['files']), 'quests': manifest['quests'], 'resourcePacks': manifest['resourcePacks']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
