"""Check and deliver Create's offline feature manual without running the game."""
from collections import Counter
from datetime import datetime
from html import escape
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile
from zoneinfo import ZoneInfo

from build_create_basics import ROOT, PROJECT, QUESTS, EVIDENCE, GROUP, FILES, read_entries
from ftb_snbt import loads


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def walk(node):
    if isinstance(node, dict):
        if re.fullmatch('[A-F0-9]{16}', str(node.get('id', ''))):
            yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def validate():
    before = json.loads((EVIDENCE / 'before-files.json').read_text())
    backup = Path(before['backup']) / 'instance/config/ftbquests/quests'
    old_files = {str(p.relative_to(backup)): loads(p.read_text()) for p in backup.rglob('*.snbt')}
    current = {str(p.relative_to(QUESTS)): loads(p.read_text()) for p in QUESTS.rglob('*.snbt')}
    original = {q['id']: q for f, c in old_files.items() if f.startswith('chapters/') for q in c.get('quests', [])}
    quests = {q['id']: q for f, c in current.items() if f.startswith('chapters/') for q in c.get('quests', [])}
    counts = Counter(e['id'] for data in current.values() for e in walk(data))
    duplicates = [key for key, n in counts.items() if n != 1]
    missing = [(key, dep) for key, q in quests.items() for dep in q.get('dependencies', []) if dep not in quests]
    original_changes = []
    for qid, quest in original.items():
        other = quests.get(qid)
        if qid == '1EA33F05E5B01612' and other:
            a, b = dict(quest), dict(other)
            previous = a.pop('description', [])
            current_description = b.pop('description', [])
            if a != b or current_description[:len(previous)] != previous:
                original_changes.append(qid)
        elif quest != other:
            original_changes.append(qid)
    concurrent_path = EVIDENCE / 'concurrent-quest-review.json'
    concurrent = json.loads(concurrent_path.read_text()) if concurrent_path.exists() else {}
    acknowledged = concurrent.get('currentExistingQuests', {})
    unreviewed_quest_changes = [qid for qid in original_changes if quests.get(qid) != acknowledged.get(qid)]
    if acknowledged:
        unreviewed_quest_changes += [qid for qid, quest in acknowledged.items() if quests.get(qid) != quest]
    cycles, visiting, visited = [], set(), set()

    def visit(key):
        if key in visiting:
            cycles.append(key)
            return
        if key in visited:
            return
        visiting.add(key)
        for dep in quests[key].get('dependencies', []):
            if dep in quests:
                visit(dep)
        visiting.remove(key)
        visited.add(key)

    for key in quests:
        visit(key)
    groups = current['chapter_groups.snbt']['chapter_groups']
    group_ids = {g['id'] for g in groups}
    bad_groups = [f for f, c in current.items() if f.startswith('chapters/') and c.get('group') and c['group'] not in group_ids]
    coverage = json.loads((EVIDENCE / 'coverage-audit.json').read_text())
    new = [q for f, c in current.items() if f.startswith('chapters/create_basics_') for q in c.get('quests', [])]
    source_drift = [name for name, expected in before['sources'].items()
                    if not (ROOT / name).exists() or sha(ROOT / name) != expected]
    content_drift = [name for name, expected in coverage['contentHash'].items() if sha(QUESTS / name) != expected]
    json_drift = [name for name, expected in coverage['sourceFiles'].items() if sha(EVIDENCE / name) != expected]
    bad_sources, seen_sources, jar_cache, lang_cache = [], set(), {}, {}
    for row in coverage['coverage']:
        for source in row['sources']:
            path = Path(source['path'])
            if not path.is_absolute():
                path = PROJECT / path
            key = (str(path), source.get('entry', ''))
            if not path.exists():
                bad_sources.append(str(path))
                continue
            seen_sources.add(key)
            if source.get('entry') and path.suffix == '.json':
                data = json.loads(path.read_text())
                native = re.search(r'nativeId="?([^\]"]+)', source['entry'])
                if native and not any(r.get('nativeId') == native[1] for r in data.get('recipes', [])):
                    bad_sources.append(key)
                if source['entry'] == 'targets (creative_motor absent)' and 'create:creative_motor' in data.get('targets', []):
                    bad_sources.append(key)
                continue
            if source.get('entry'):
                member, _, anchor = source['entry'].partition('#')
                if path not in jar_cache:
                    with zipfile.ZipFile(path) as archive:
                        jar_cache[path] = set(archive.namelist())
                if member not in jar_cache[path]:
                    bad_sources.append(key)
                elif member.endswith('.json') and '/lang/' in member:
                    if (path, member) not in lang_cache:
                        with zipfile.ZipFile(path) as archive:
                            lang_cache[path, member] = json.loads(archive.read(member))
                    language = lang_cache[path, member]
                    range_anchor = re.fullmatch(r'(.+?)(\d+)\.\.(\d+)', anchor)
                    if range_anchor:
                        if any(range_anchor[1] + str(i) not in language for i in range(int(range_anchor[2]), int(range_anchor[3]) + 1)):
                            bad_sources.append(key)
                    elif anchor and not any(k.startswith(anchor) for k in language):
                        bad_sources.append(key)
                    if any(k not in language for k in source.get('keys', [])):
                        bad_sources.append(key)
    coords = []
    for filename, c in current.items():
        if filename.startswith('chapters/create_basics_'):
            positions = Counter((q.get('x'), q.get('y')) for q in c.get('quests', []))
            coords += [(filename, pos) for pos, n in positions.items() if n > 1]
    checks = {'allSnbtParsed': True, 'uniqueIds': not duplicates, 'validChapterGroups': not bad_groups,
        'noMissingDependencies': not missing, 'acyclicDependencies': not cycles,
        'existingQuestsPreservedOrConcurrentEditsRetained': not unreviewed_quest_changes,
        'noNewTechnologyOrCraftingGates': all(not q.get('dependencies') and not q.get('rewards') and
            len(q['tasks']) == 1 and q['tasks'][0]['type'] == 'checkmark' for q in new),
        'all164DedicatedGuidesPresent': len(new) == coverage['tutorialEntries'] == 164,
        'noUnclassifiedCoreBlockstates': not coverage['unclassifiedBlockstates'],
        'noNodeCoordinateOverlap': not coords, 'allDeclaredSourcesResolve': not bad_sources,
        'sourceRecipesAndModsUnchanged': not source_drift, 'authoredDataMatchesGeneratedQuests': not (content_drift or json_drift)}
    report = {'checkedAt': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(), 'checks': checks,
        'passed': all(checks.values()), 'questsBefore': len(original), 'questsAfter': len(quests),
        'tutorialChapters': coverage['tutorialChapters'], 'dedicatedTutorials': len(new),
        'sourceReferencesChecked': len(seen_sources), 'duplicateIds': duplicates, 'missingDependencies': missing,
        'cycles': cycles, 'changedOriginalQuests': original_changes, 'sourceDrift': source_drift,
        'originalQuestSnapshotUnchanged': not original_changes,
        'unreviewedQuestChanges': unreviewed_quest_changes,
        'concurrentQuestReview': str(concurrent_path) if concurrent else None,
        'badSources': bad_sources, 'contentDrift': content_drift, 'inputDataDrift': json_drift,
        'mode': 'static-only; no game or server launch',
        'limits': ['Resource classification is a bounded audit of installed Create 6.0.8, not every addon.',
                   'Colour and engine-internal states share their parent tutorial; materials and building palettes have explicit exclusions.',
                   'Game rendering, interaction and multiplayer behaviour have not been tested in a new runtime.']}
    (EVIDENCE / 'static-validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['passed', 'checks', 'questsBefore', 'questsAfter', 'dedicatedTutorials', 'sourceReferencesChecked']}, ensure_ascii=False, indent=2))
    if not report['passed']:
        raise SystemExit(1)
    return before, report, current, coverage


def render_preview(current, chapters, stats, coverage):
    nav, sections = [], []
    paragraph = lambda s: '<hr>' if s == '{@pagebreak}' else ('' if s.startswith('{image:') else '<p>' + escape(re.sub(r'&[0-9a-fk-or]', '', s, flags=re.I)) + '</p>')
    for chapter in chapters:
        key, title = chapter['key'], chapter['title']
        nav.append(f'<a href="#{key}">{escape(title)} <small>{len(chapter["entries"])}</small></a>')
        cards = []
        for entry in chapter['entries']:
            cards.append(f'<details class="card" id="q-{entry["questId"]}" open><summary>{escape(entry["title"])}</summary><div class="content">'
                + ''.join(paragraph(p) for p in entry['description'])
                + '<footer>' + escape(entry['item']) + '</footer></div></details>')
        sections.append(f'<section id="{key}"><h2>{escape(title)}</h2>{"".join(cards)}</section>')
    mainline_names = ['expedition_technology', 'steam_railway', 'precision_component', 'ascend_on_burning_oil', 'expedition_components']
    mainline = []
    for name in mainline_names:
        if 'chapters/' + name + '.snbt' not in current:
            continue
        c = current['chapters/' + name + '.snbt']
        title = c['title']
        nav.append(f'<a class="secondary" href="#mainline-{name}">{escape(title)}</a>')
        cards = []
        for quest in c.get('quests', []):
            label = quest.get('title') or next((t['title'] for t in quest.get('tasks', []) if t.get('title')), '任务')
            cards.append(f'<details class="card" id="q-{quest["id"]}"><summary>{escape(re.sub(r"&[0-9a-fk-or]", "", label, flags=re.I))}</summary><div class="content">'
                + ''.join(paragraph(p) for p in quest.get('description', [])) + '</div></details>')
        mainline.append(f'<section id="mainline-{name}"><h2>{escape(title)} · 科技主线</h2>{"".join(cards)}</section>')
    feature_rows = ''.join('<tr><td>' + escape(row['title']) + '</td><td>' + escape(row['item'])
                           + '</td><td><a href="#q-' + row['questId'] + '">查看独立教程</a></td></tr>' for row in coverage['coverage'])
    html = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>机械动力 · 逐功能教程</title>
<style>*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font:16px/1.8 system-ui,-apple-system,sans-serif;color:#283932;background:#f5f3eb}aside{position:fixed;inset:0 auto 0 0;width:260px;background:#173e36;color:#edf7ec;padding:27px 22px;overflow:auto}aside strong{display:block;font-size:22px;line-height:1.4;margin-bottom:24px}aside a{display:block;color:#dfebdf;text-decoration:none;padding:8px 0;font-size:14px;border-bottom:1px solid #ffffff14}aside small{float:right;color:#9fc3aa}.secondary{opacity:.65}main{margin-left:260px;padding:40px 5vw 90px;max-width:1250px}h1{font-size:33px;line-height:1.35;margin:0 0 14px}h2{font-size:24px;scroll-margin-top:25px}header p{color:#65736a}.stats{display:flex;gap:28px;padding:17px 22px;border-radius:8px;background:#e4ecdf;flex-wrap:wrap}.stats b{display:block;font-size:27px}input{width:100%;padding:14px 16px;border:1px solid #b7c8b8;border-radius:7px;font:inherit;margin:22px 0}.card{background:#fff;border:1px solid #d8e1d5;border-radius:9px;margin:12px 0;scroll-margin-top:15px}summary{cursor:pointer;padding:15px 21px;font-weight:650}.content{padding:0 22px 19px}.content p{margin:10px 0}footer{margin-top:16px;padding-top:10px;border-top:1px solid #e3e9df;color:#849083;font-size:12px;overflow-wrap:anywhere}a{color:#367959}table{width:100%;border-collapse:collapse;background:#fff;font-size:13px}td,th{text-align:left;padding:10px;border-bottom:1px solid #e0e7dc;overflow-wrap:anywhere}th{background:#e4ecdf}hr{border:0;border-top:1px solid #dde5d8;margin:20px 0}section{margin-top:35px}.note{font-size:13px;background:#edeade;padding:13px 18px;border-radius:7px}@media(max-width:800px){aside{position:static;width:auto}aside a{display:inline-block;padding:8px;margin-right:12px}aside small{margin-left:8px}main{margin:0;padding:24px}h1{font-size:27px}}</style>
<aside><strong>机械动力<br>逐功能教程</strong>NAV<a href="#coverage">覆盖清单</a></aside><main><header><h1>每台机器，都有自己的操作说明</h1><p>工具 → 传动 → 加工 → 物流 → 流体 → 动态结构 → 控制 → 包裹 → 列车<br>2026-10-18 · 本地 Create 6.0.8 与现行魔改配方</p><div class="stats"><span><b>164</b>独立教程节点</span><span><b>11</b>功能章节</span><span><b>276</b>功能及变体状态关联</span></div><p class="note">教程可直接阅读，不要求先制作方块，不增加科技硬门槛。相同功能的颜色变体和机器内部状态归到同一教程；常用工具也分别说明。材料与普通建筑配色不当作独立机器。此页不宣称覆盖所有附属模组，且未启动游戏做运行验证。</p><input id="search" placeholder="搜索功能、材料、机器或操作，例如：风车、30 RPM、时刻表…" aria-label="搜索教程"></header>
SECTIONS<details><summary>展开现有构件科技主线</summary>MAINLINE</details><section id="coverage"><h2>逐项覆盖清单</h2><p>已核对本体643个方块状态资源，全部有分类记录；276个功能及变体状态关联到教程。下表另含常用手持工具，不将每种颜色重复计为新功能。</p><table><thead><tr><th>功能</th><th>物品或图标</th><th>教程</th></tr></thead><tbody>ROWS</tbody></table></section></main>
<script>const cards=[...document.querySelectorAll('.card')];document.querySelector('#search').addEventListener('input',e=>{const q=e.target.value.toLowerCase();for(const c of cards){c.hidden=!c.textContent.toLowerCase().includes(q);if(q)c.open=true}for(const s of document.querySelectorAll('section:not(#coverage)'))s.hidden=![...s.querySelectorAll('.card')].some(c=>!c.hidden)});addEventListener('hashchange',()=>{const e=document.getElementById(decodeURIComponent(location.hash.slice(1)));if(e){e.hidden=false;for(let p=e;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true}})</script></html>'''
    return html.replace('NAV', ''.join(nav)).replace('SECTIONS', ''.join(sections)).replace('MAINLINE', ''.join(mainline)).replace('ROWS', feature_rows)


def main():
    before, stats, current, coverage = validate()
    merge_path = EVIDENCE / 'concurrent-quest-review.json'
    merge = json.loads(merge_path.read_text()) if merge_path.exists() else {}
    previous_path = EVIDENCE / 'completion.json'
    previous = json.loads(previous_path.read_text()) if previous_path.exists() else {}
    delivered = {row['path']: row['sha256'] for row in previous.get('files', [])}
    payload = []
    manifest_path = ROOT / 'evidence/overlay-files.json'
    manifest = json.loads(manifest_path.read_text())
    names = list(coverage['contentHash'])
    for name in names:
        source = QUESTS / name
        relative = Path('config/ftbquests/quests') / name
        for parent in [ROOT / 'overlay', PROJECT / 'servers/cmi-expedition/instance']:
            target = parent / relative
            old_key = str(target.relative_to(ROOT)) if parent == ROOT / 'overlay' else str(target.relative_to(PROJECT))
            expected = before['quests'].get(old_key)
            if str(target.resolve()) in merge.get('syncMergeBaseHashes', {}):
                expected = merge['syncMergeBaseHashes'][str(target.resolve())]
            if target.exists() and sha(target) not in {expected, sha(source), delivered.get(str(relative))}:
                raise RuntimeError('Concurrent quest edit needs merging before sync: ' + str(target))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            assert target.read_bytes() == source.read_bytes()
        manifest[str(relative)] = sha(source)
        payload.append({'path': str(relative), 'sha256': sha(source)})
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    preview = EVIDENCE / '机械动力逐功能教程预览.html'
    preview.write_text(render_preview(current, read_entries(), stats, coverage))
    class Links(HTMLParser):
        def __init__(self):
            super().__init__(); self.ids = []; self.anchors = []
        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            if a.get('id'): self.ids.append(a['id'])
            if a.get('href', '').startswith('#'): self.anchors.append(a['href'][1:])
    p = Links(); p.feed(preview.read_text())
    assert len(p.ids) == len(set(p.ids))
    assert set(p.anchors) <= set(p.ids), set(p.anchors) - set(p.ids)
    # Keep the previously delivered review link current, preserving its old bytes.
    legacy = ROOT / 'evidence/mainline-guide-20261018/主线任务离线预览.html'
    legacy_backup = Path(before['backup']) / 'previous-mainline-preview.html'
    if legacy.exists() and not legacy_backup.exists(): shutil.copy2(legacy, legacy_backup)
    shutil.copy2(preview, legacy)
    completion = {'completedAt': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
        'tutorialChapters': 11, 'independentTutorials': 164, 'functionalAndVariantStatesCovered': 276,
        'files': payload, 'clientOverlayLocalServerIdentical': True, 'previewAnchorsValid': True,
        'preview': str(preview.resolve()), 'backup': before['backup'],
        'staticValidation': str((EVIDENCE / 'static-validation.json').resolve()),
        'coverageAudit': str((EVIDENCE / 'coverage-audit.json').resolve()),
        'gameOrServerStarted': False, 'runtimeValidated': False, 'publishedRemotely': False}
    (EVIDENCE / 'completion.json').write_text(json.dumps(completion, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'syncedFiles': len(payload), 'preview': str(preview.resolve())}, ensure_ascii=False))


if __name__ == '__main__':
    main()
