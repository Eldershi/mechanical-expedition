"""Select distributable game files and omit local private or generated state."""

from pathlib import Path, PurePosixPath

import os

import re

SOURCE = Path()

FOLDERS=['mods','config','shaderpacks','defaultconfigs','hotai','ldlib','patchouli_books','moonlight-global-datapacks','datapacks','tlm_custom_pack','resourcepacks','oeb','oei','oef']

KUBE=['startup_scripts','server_scripts','client_scripts','data','assets','config']

FORBIDDEN={'.git','.github','.index','.cache','__pycache__','saves','playerdata','players','accounts','account','logs','log','crash-reports','screenshots','backups','backup','cache','caches','exported','exports','probe','probes','.expedition','updater','xaerowaypoints','distant_horizons_server_data','tmp','temp'}

SKIP=['config/resourceful-config-web.json','config/embeddium-fingerprint.json','config/touhou_little_maid/sites','config/touhou_little_maid/info.json','config/roadweaver/structure_cache_overworld.json','config/chunky/tasks','config/jei/world','config/fancymenu/layout_editor','config/fancymenu/last_world.meta','config/fancymenu/legacy_checklist.txt','config/fancymenu/dragger_metas.json','config/fancymenu/audio_element_controller_metas.json','config/expedition-keybind-migrations.json','kubejs/client_scripts/event/ExpeditionSessionPerformance.js']

TEXT={'.toml','.json','.json5','.properties','.txt','.cfg','.snbt','.ini','.yaml','.yml','.js','.mcmeta','.md'}

ABSOLUTE=re.compile(r'(?i)(?:/(?:Users|home|Volumes|private/var|var/folders|Applications)/|(?<![\w])[A-Z]:[\\/](?!/))')

URL=re.compile(r'https?://[^\s"\x27<>]+')

UUID=re.compile(r'(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b')

CREDENTIAL=re.compile(r'''(?i)["']?\b(api[_-]?key|access[_-]?token|refresh[_-]?token|auth[_-]?token|password|secret|authorization|auth|token)["']?\s*[:=]\s*["']([^"'\r\n]+)["']''')

def skip_reason(relative):
    path=PurePosixPath(relative);lower=relative.lower();parts={p.lower() for p in path.parts}
    if path.name.casefold().startswith('agents') and path.suffix.casefold()=='.md':return 'local instructions'
    if parts&{'local-only','.agents','.codex'}:return 'local project state'
    if path.name.casefold().startswith('install_for_codex') or '安装提示词' in path.name:return 'local installation instructions'
    if parts&FORBIDDEN:return 'generated/private/cache directory'
    if path.name.startswith('.') or lower in {'servers.dat','servers.dat_old','usercache.json','usernamecache.json','options.txt'}:return 'hidden or personal runtime file'
    if any(lower==s.lower() or lower.startswith(s.lower()+'/') for s in SKIP):return 'explicit private/generated exclusion'
    if lower.startswith('config/spark/') and lower!='config/spark/config.json':return 'profiler output/cache'
    if path.suffix.lower() in {'.db','.sqlite','.sqlite3','.jfr','.sparkprofile','.log','.bak','.old','.tmp','.lock'}:return 'database/log/backup/runtime state'
    if any(v in path.name.lower() for v in ['_cache.','_cache_','fingerprint','chat_history','chat-history','last_world','user_variables','bookmark']):return 'personal/generated state'
    if lower.startswith('shaderpacks/') and lower.endswith('.zip.txt'):return 'omit per-machine shader quality overrides'
    if lower.startswith('mods/') and any(v in lower for v in ('expedition-ui-probe','expedition-recipe-audit','-prototype-')):return 'non-production test instrumentation'
    return None

def privacy(relative,blob):
    """Never return secret values in findings; preserve formal UI/quest identifiers."""
    if PurePosixPath(relative).suffix.lower() not in TEXT:return blob,[]
    try:text=blob.decode('utf-8-sig')
    except UnicodeError:return blob,[]
    if PurePosixPath(relative).suffix.lower()=='.json':
        import json
        def scrub(value):
            if isinstance(value,dict):
                return {key:scrub(item) for key,item in value.items()
                        if not (isinstance(item,str) and
                                (re.search(r'https?://chatgpt\.com/(?:c/|g/|space/|share/)',item) or
                                 key in {'pageId','threadId','turnId','conversationId'} and
                                 (item.startswith('page_') or re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',item))))}
            if isinstance(value,list):return [scrub(item) for item in value]
            return value
        try:
            original=json.loads(text);cleaned=scrub(original)
            if cleaned!=original:
                text=json.dumps(cleaned,ensure_ascii=False,indent=2)+'\n';blob=text.encode('utf-8')
        except json.JSONDecodeError:pass
    findings=[];lines=text.splitlines(keepends=True);changed=False;last_key=''
    for index,line in enumerate(lines):
        number=index+1
        if line.lstrip().startswith(('#','//','*')):continue
        key_match=re.match(r'''\s*["']?([\w. -]+)["']?\s*[:=]''',line)
        if key_match:last_key=key_match.group(1).strip()
        if ABSOLUTE.search(URL.sub('',line)):
            findings.append({'path':relative,'line':number,'key':last_key or '(string-list entry)','reason':'local absolute path'})
            if relative=='config/ModernUI/client.toml' and re.fullmatch(r'''\s*["'].*["']\s*,?\s*(?:#.*)?''',line.strip()):
                ending='\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else ''
                lines[index]=re.match(r'\s*',line).group()+'# Local font file path omitted for clean import'+ending;changed=True
            else:return None,findings
        if line.lstrip().startswith(('#','//','*')):continue
        for match in CREDENTIAL.finditer(line):
            value=match.group(2)
            if value.lower() not in {'none','false','true','null','unknown','changeme'} and not re.fullmatch(r'[\w.-]+:[\w/.-]+',value):
                findings.append({'path':relative,'line':number,'key':match.group(1),'reason':'nonempty credential-like setting'});return None,findings
        formal_ids=relative.startswith(('config/fancymenu/','config/ftbquests/quests/'))
        if UUID.search(line) and not formal_ids:
            findings.append({'path':relative,'line':number,'key':last_key or '(UUID value)','reason':'possible player/personal UUID outside formal UI/quest schemas'});return None,findings
    if changed:
        bom=b'\xef\xbb\xbf' if blob.startswith(b'\xef\xbb\xbf') else b''
        blob=bom+''.join(lines).encode('utf-8')
        import tomllib
        tomllib.loads(blob.decode('utf-8-sig'))
    return blob,findings

def discover():
    files={};excluded=[]
    roots=[SOURCE/folder for folder in FOLDERS]+[SOURCE/'kubejs'/folder for folder in KUBE]
    for source in roots:
        if not source.exists():continue
        for directory,dirs,names in os.walk(source,followlinks=False):
            folder=Path(directory)
            for name in list(dirs):
                p=folder/name;relative=p.relative_to(SOURCE).as_posix();reason=skip_reason(relative)
                if p.is_symlink() or reason:
                    excluded.append({'path':relative,'reason':'symlink' if p.is_symlink() else reason});dirs.remove(name)
            for name in names:
                p=folder/name;relative=p.relative_to(SOURCE).as_posix();reason=skip_reason(relative)
                if p.is_symlink() or reason:excluded.append({'path':relative,'reason':'symlink' if p.is_symlink() else reason});continue
                if p.is_file():files[relative]=p
    for name in ['LICENSE','License.md','icon.png','SOURCE.json','kubejs/guide-tome-catalog.json']:
        p=SOURCE/name
        if p.is_file() and not p.is_symlink():files[name]=p
    return files,excluded
