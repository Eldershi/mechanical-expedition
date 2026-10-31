"""Build, test and install the client-only mechanical spell-preview presentation layer."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile
import ponder_compat

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / 'instance'
EVIDENCE = ROOT / 'evidence/ponder-ui-v3'
TEST = EVIDENCE / 'test-instance'
JAR = ROOT / 'downloads/ponder-addons/expedition-ponder-ui-1.0.2.jar'
LIBS = (Path.home() / 'Library/Application Support/Swift Craft Launcher/meta/libraries')


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def setup():
    ponder_compat.EVIDENCE = EVIDENCE
    ponder_compat.TEST = TEST
    ponder_compat.WORLD = 'Ponder-UI-Test'


def prepare():
    setup()
    ponder_compat.prepare()
    for old in (TEST/'mods').glob('expedition-ponder-ui-*.jar'):old.unlink()


def classpath():
    paths = [LIBS / 'net/minecraft/client/1.20.1-20230612.114412/client-1.20.1-20230612.114412-srg.jar']
    if JAR.exists():paths.append(JAR)
    paths.extend(sorted((ROOT / 'evidence/ponder-addons/inspect-libs').glob('*.jar')))
    paths.extend(sorted((LIVE / 'mods').glob('*.jar')))
    for name in ['org/spongepowered/mixin', 'com/google/code/gson', 'com/google/guava',
                 'com/mojang', 'org/slf4j', 'org/apache', 'org/lwjgl', 'org/joml',
                 'io/netty', 'it/unimi/dsi', 'net/minecraftforge']:
        paths.extend(sorted((LIBS / name).rglob('*.jar')))
    return ':'.join(map(str, paths))


def build():
    classes = EVIDENCE / 'classes'
    classes.mkdir(parents=True, exist_ok=True)
    sources = sorted((ROOT / 'tools/compat/ponder').glob('*.java'))
    result = subprocess.run(['javac','--release','17','-proc:none','-encoding','UTF-8',
        '-cp',classpath(),'-d',str(classes),*map(str,sources)],capture_output=True,text=True)
    (EVIDENCE / 'compile.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    with zipfile.ZipFile(JAR,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('META-INF/MANIFEST.MF',
            'Manifest-Version: 1.0\nMixinConfigs: expedition-ponder-ui.mixins.json\n\n')
        archive.writestr('pack.mcmeta',json.dumps({'pack':{'pack_format':15,
            'description':'Expedition mechanical spell preview UI'}}))
        archive.writestr('META-INF/mods.toml','''modLoader="lowcodefml"
loaderVersion="[47,)"
license="Private local presentation adapter"
[[mods]]
modId="expedition_ponder_ui"
version="1.0.2"
displayName="Expedition Mechanical Spell Preview UI"
displayTest="IGNORE_ALL_VERSION"
[[dependencies.expedition_ponder_ui]]
modId="minecraft"
mandatory=true
versionRange="[1.20.1,1.20.2)"
side="CLIENT"
[[dependencies.expedition_ponder_ui]]
modId="iss_ponder"
mandatory=true
versionRange="[1.0.3]"
side="CLIENT"
''')
        archive.writestr('expedition-ponder-ui.mixins.json',json.dumps({
            'required':True,'minVersion':'0.8','package':'expedition.ponderui.mixin',
            'compatibilityLevel':'JAVA_17',
            'client':['SpellPreviewSkin','SpellStatAccess','PreviewProjectionAccess',
                'SpellPonderIndexBridge','SpellPonderTagNavigation','SpellPonderClientSync','SpellPonderTagText','PonderTagIconAccess'],
            'injectors':{'defaultRequire':1}}))
        for lang, labels in {
            'zh_cn':{'parameters':'法术参数','data':'施法数据','index':'思索索引',
                'school_description':'包含 %s 种法术，选择法术开始演示。'},
            'en_us':{'parameters':'Spell Parameters','data':'Casting Data','index':'Ponder Index',
                'school_description':'%s spells. Select a spell to begin its demonstration.'},
        }.items():
            archive.writestr('assets/expedition_ponder_ui/lang/'+lang+'.json',json.dumps({
                'gui.expedition_ponder_ui.'+key:value for key,value in labels.items()},ensure_ascii=False))
        for source in classes.rglob('*.class'):
            archive.write(source,str(source.relative_to(classes)))
    dump(EVIDENCE/'build.json',{'at':datetime.now().astimezone().isoformat(),
        'jar':str(JAR),'sha256':sha(JAR),'upstreamJarSha256':sha(LIVE/'mods/iss_ponder-forge1.20.1-1.0.3-all.jar'),
        'sourceFiles':{str(source.relative_to(ROOT)):sha(source) for source in sources},
        'style':{'scene':'borderless and unclipped, fitted complete platform, no camera hint',
                 'parameters':'framed mechanical paper panel, 27% width with 128px minimum',
                 'panelMarginsGuiPixels':{'top':14,'bottom':14,'right':14},
                 'entry':'bottom-left current spell and school, opens native Ponder index',
                 'index':'school tags in global Ponder index; school-specific native NBT scroll models including add-on schools; paginated 20px spell icons with inner strokes and native 28px cells/8px spacing',
                 'buttons':'active minecraft:textures/gui/widgets.png; same nine-slice and state coordinates as vanilla'},
        'scope':'Client presentation, layout hitboxes, navigation and Ponder category registration. No packet, spell calculation or server session code is patched.'})
    if TEST.exists():
        target=TEST/'mods'/JAR.name
        if not target.exists():target.symlink_to(JAR)
    print('Built',JAR)


def probe():
    classes=EVIDENCE/'probe-classes';classes.mkdir(exist_ok=True)
    result=subprocess.run(['javac','--release','17','-proc:none','-encoding','UTF-8',
        '-cp',classpath(),'-d',str(classes),str(ROOT/'tools/diagnostics/PonderUiProbe.java')],capture_output=True,text=True)
    (EVIDENCE/'probe-compile.log').write_text(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    with zipfile.ZipFile(TEST/'mods/expedition-ui-probe-1.0.jar','w',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('pack.mcmeta',json.dumps({'pack':{'pack_format':15,
            'description':'Disposable spell UI integration probe'}}))
        archive.writestr('META-INF/mods.toml','modLoader="lowcodefml"\nloaderVersion="[47,)"\n'
            'license="Disposable test"\n[[mods]]\nmodId="expedition_ui_probe"\nversion="1.0"\n'
            'displayName="Disposable spell UI integration probe"\n')
        for source in classes.rglob('*.class'):archive.write(source,str(source.relative_to(classes)))
    (TEST/'kubejs/client_scripts/event/PonderUiProbe.js').write_text(
        "const ExpeditionUiProbe = Java.loadClass('expedition.ponder.PonderUiProbe')\n"
        "const UiScaleInteger = Java.loadClass('java.lang.Integer')\n"
        "ClientEvents.tick(event => {\n"
        "  if (ExpeditionUiProbe.scaleRequested()) {\n"
        "    let client = Java.loadClass('net.minecraft.client.Minecraft').getInstance()\n"
        "    client.options.guiScale().set(UiScaleInteger.valueOf('4'))\n"
        "    client.resizeDisplay()\n"
        "    ExpeditionUiProbe.scaleApplied()\n"
        "  }\n"
        "  ExpeditionUiProbe.tick()\n"
        "})\n")
    print('Built disposable UI probe')


def launch():
    setup();ponder_compat.launch()


def validate():
    result=json.loads((TEST/'kubejs/exported/ponder-ui-result.json').read_text())
    console=(EVIDENCE/'console.log').read_text(errors='replace')
    scripts={}
    for name in ['startup','client','server']:
        path=TEST/'logs/kubejs'/(name+'.log')
        baseline=LIVE/'logs/kubejs'/(name+'.log')
        lines=path.read_text(errors='replace').splitlines()
        baseline_lines=baseline.read_text(errors='replace').splitlines()
        def errors(source):
            headers=set()
            for line in source:
                if '[ERROR]' not in line:continue
                text=re.sub(r'^!\s*','',line.split('[ERROR]',1)[1].strip())
                if not text.startswith(('at ','...')):headers.add(text)
            return headers
        observed,known=errors(lines),errors(baseline_lines)
        scripts[name]={'summaries':[line for line in lines if re.search(r'Loaded \d+/\d+ KubeJS',line)],
            'observedErrorHeaders':sorted(observed),'baselineErrorHeaders':sorted(known),
            'newErrors':sorted(observed-known),'baselineLog':str(baseline)}
    screenshots=sorted((TEST/'screenshots').glob('*.png'))
    checks={
        'uiInteractionChecksPassed':result['passed'] and all(row['passed'] for row in result['checks']),
        'twelveScreenshotsCaptured':len(screenshots)==12,
        'jemmIntegration':result.get('jemmCategoryCount',0)>=9,
        'noProbeMetadataWarning':'Missing metadata in pack mod:expedition_ui_probe' not in console,
        'noAdapterMixinFailure':not any(word in console for word in ['MixinApplyError','InvalidInjectionException','InjectionError']),
        'noNewScriptRuntimeErrors':all(not row['newErrors'] for row in scripts.values()),
        'scriptsCompile':all(row['summaries'] and all('with 0 errors' in line for line in row['summaries']) for row in scripts.values()),
        'noCrashReports':not list((TEST/'crash-reports').glob('*.txt')),
        'noNativeCrashReports':not list(TEST.glob('hs_err_pid*.log')),
        'previewSessionsCleanedUp':result.get('sessionsAfterClose')==0,
        'testWorldSaved':'ThreadedAnvilChunkStorage: All dimensions are saved' in console,
    }
    validation={'checkedAt':datetime.now().astimezone().isoformat(),'passed':all(checks.values()),
        'validatedJarSha256':sha(JAR),
        'checks':checks,'interactionChecks':result['checks'],'scripts':scripts,
        'screenshots':[str(path.relative_to(EVIDENCE)) for path in screenshots],
        'limitations':['Local client and integrated server only; no remote multiplayer test.',
            'Known pre-existing Immersive Engineering blueprint ID script error is compared against the live baseline.']}
    dump(EVIDENCE/'validation.json',validation)
    print(json.dumps({'passed':validation['passed'],'checks':checks},ensure_ascii=False,indent=2))
    assert validation['passed'],validation


def install():
    validation=json.loads((EVIDENCE/'validation.json').read_text())
    assert validation['passed'],validation
    assert sha(JAR)==validation['validatedJarSha256']
    result=json.loads((TEST/'kubejs/exported/ponder-ui-result.json').read_text())
    assert result['passed'],result
    assert not list((TEST/'crash-reports').glob('*.txt'))
    before=json.loads((EVIDENCE/'before.json').read_text())
    unchanged=all(sha(LIVE/'mods'/name)==digest for name,digest in before['modHashes'].items())
    worlds={str(p.relative_to(LIVE/'saves')):sha(p) for p in (LIVE/'saves').rglob('*') if p.is_file()}
    assert unchanged and worlds==before['worldHashes']
    assert sha(LIVE/'options.txt')==before['optionsHash']
    assert sha(LIVE/'SOURCE.json')==before['sourceHash']
    assert sha(JAR)==json.loads((EVIDENCE/'build.json').read_text())['sha256']
    jemm=json.loads((EVIDENCE/'jemm-download.json').read_text())
    jemm_source=ROOT/'downloads/ponder-addons'/jemm['file']
    jemm_target=LIVE/'mods'/jemm['file']
    assert not jemm_target.exists() and sha(jemm_source)==jemm['sha256']
    backup=ROOT/('backups/before-ponder-ui-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True)
    shutil.copy2(LIVE/'SOURCE.json',backup/'SOURCE.json')
    target=LIVE/'mods'/JAR.name
    previous=list((LIVE/'mods').glob('expedition-ponder-ui-*.jar'))
    for old in previous:shutil.copy2(old,backup/old.name)
    shutil.copy2(JAR,target)
    sources=json.loads((LIVE/'SOURCE.json').read_text())
    for old in previous:
        if old!=target:old.unlink()
        sources['sources'].pop('mods/'+old.name,None)
    sources['sources']['mods/'+target.name]={'origin':'local_client_ui_adapter',
        'buildScript':'tools/ponder_ui.py','sha256':sha(target),
        'description':'Native Ponder school/spell index with scroll and spell icons; bottom-left entry; inset mechanical parameters; fitted borderless demonstration'}
    shutil.copy2(jemm_source,jemm_target)
    sources['sources']['mods/'+jemm_target.name]={'origin':'approved_multiblock_jei_addon',
        'url':jemm['download'],'projectUrl':jemm['project'],'sha256':jemm['sha256']}
    dump(LIVE/'SOURCE.json',sources)
    unchanged=all(sha(LIVE/'mods'/name)==digest for name,digest in before['modHashes'].items()
        if not name.startswith('expedition-ponder-ui-'))
    receipt={'installedAt':datetime.now().astimezone().isoformat(),'file':str(target),
        'sha256':sha(target),'backup':str(backup),'upstreamModsUnchanged':unchanged,
        'jemm':{'file':str(jemm_target),'sha256':sha(jemm_target),'categoryCount':result['jemmCategoryCount']},
        'optionsUnchanged':sha(LIVE/'options.txt')==before['optionsHash'],
        'worldsUnchanged':worlds==before['worldHashes'],'uiTestPassed':result['passed']}
    dump(EVIDENCE/'installation.json',receipt)
    assert all(receipt[key] for key in ['upstreamModsUnchanged','optionsUnchanged','worldsUnchanged'])
    print(json.dumps(receipt,ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','build','probe','launch','validate','install'])
    globals()[parser.parse_args().action]()
