"""Small, lossless helpers for editing existing FTB quest text offline."""
import hashlib
import json
import re
from pathlib import Path

from ftb_snbt import loads

ROOT = Path(__file__).resolve().parents[1]
QUESTS = ROOT / 'instance/config/ftbquests/quests'
EVIDENCE = ROOT / 'evidence/mainline-guide-20261018'


def stable_id(name):
    return f'{int(hashlib.sha256(("expedition-guide:" + name).encode()).hexdigest()[:16], 16) & ((1 << 63) - 1):016X}'


def replace_description(text, quest_id, paragraphs):
    # Match only top-level quest blocks. Preserve all existing NBT numeric types,
    # item stacks, tasks, rewards and formatting outside the description itself.
    blocks = list(re.finditer(r'^\t\t\{\n.*?^\t\t\}', text, re.M | re.S))
    matches = [m for m in blocks if re.search(r'^\t{3}id: "' + re.escape(quest_id) + '"$', m.group(), re.M)]
    if len(matches) != 1:
        raise ValueError(f'Expected one quest: {quest_id}, got {len(matches)}')
    match = matches[0]
    block = match.group()
    before = loads(block)
    replacement = '\t\t\tdescription: [\n' + ''.join('\t\t\t\t' + json.dumps(p, ensure_ascii=False) + '\n' for p in paragraphs) + '\t\t\t]'
    desc = re.search(r'^\t{3}description:.*?(?=^\t{3}[a-z_]+:|^\t\t\})', block, re.M | re.S)
    if desc:
        block = block[:desc.start()] + replacement + '\n' + block[desc.end():]
    else:
        block = block.replace('\t\t{\n', '\t\t{\n' + replacement + '\n', 1)
    after = loads(block)
    assert {k: v for k, v in before.items() if k != 'description'} == {k: v for k, v in after.items() if k != 'description'}
    return text[:match.start()] + block + text[match.end():]


def quest_block(key, title, item, paragraphs, x, y, dependencies=()):
    q = lambda s: json.dumps(s, ensure_ascii=False)
    rows = ['\t\t{', f'\t\t\tid: {q(stable_id(key))}', f'\t\t\ttitle: {q(title)}',
            f'\t\t\ticon: {q(item)}', f'\t\t\tx: {x:.1f}d', f'\t\t\ty: {y:.1f}d',
            '\t\t\tdescription: [']
    rows += ['\t\t\t\t' + q(p) for p in paragraphs]
    rows.append('\t\t\t]')
    if dependencies:
        rows.append('\t\t\tdependencies: [' + ' '.join(q(stable_id(d)) for d in dependencies) + ']')
    rows += ['\t\t\ttasks: [{', f'\t\t\t\tid: {q(stable_id(key + ":task"))}']
    if key in {'read-route', 'read-assembly', 'late-intro'}:
        rows.append('\t\t\t\ttype: "checkmark"')
    else:
        rows += ['\t\t\t\ttype: "item"', f'\t\t\t\titem: {q(item)}', '\t\t\t\tconsume_items: false']
    rows += ['\t\t\t}]', '\t\t}']
    return '\n'.join(rows)


def replace_dependencies(text, quest_id, dependencies):
    blocks = list(re.finditer(r'^\t\t\{\n.*?^\t\t\}', text, re.M | re.S))
    match = next(m for m in blocks if re.search(r'^\t{3}id: "' + quest_id + '"$', m.group(), re.M))
    block = match.group()
    before = loads(block)
    replacement = '\t\t\tdependencies: [' + ' '.join(json.dumps(d) for d in dependencies) + ']'
    dep = re.search(r'^\t{3}dependencies:.*?(?=^\t{3}[a-z_]+:|^\t\t\})', block, re.M | re.S)
    if dep:
        block = block[:dep.start()] + replacement + '\n' + block[dep.end():]
    else:
        block = block.replace('\t\t{\n', '\t\t{\n' + replacement + '\n', 1)
    after = loads(block)
    assert {k: v for k, v in before.items() if k != 'dependencies'} == {k: v for k, v in after.items() if k != 'dependencies'}
    return text[:match.start()] + block + text[match.end():]
