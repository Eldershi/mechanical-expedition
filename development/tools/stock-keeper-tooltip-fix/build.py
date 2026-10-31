#!/usr/bin/env python3
"""Build/test a client-only add-on; never modify the installed instance."""
from pathlib import Path
import hashlib, json, os, subprocess, zipfile

TOOL = Path(__file__).resolve().parent
ROOT = TOOL.parents[1]
INSTANCE = (Path.home() / 'Library/Application Support/Swift Craft Launcher/profiles/机械远征-CMI-迁移测试')
LIBS = (Path.home() / 'Library/Application Support/Swift Craft Launcher/meta/libraries')
OUT = ROOT / 'releases/bugfix-bundle-20261027/storage-fix'
BUILD = TOOL / 'build'
CLASSES = BUILD / 'classes'

def run(args, name, timeout=45):
    result = subprocess.run(list(map(str,args)), text=True, capture_output=True, timeout=timeout)
    (BUILD / name).write_text(result.stdout + result.stderr)
    if result.returncode: raise RuntimeError(result.stdout + result.stderr)
    return result.stdout + result.stderr

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def zip_member(archive, name, data):
    info = zipfile.ZipInfo(name, date_time=(1980,1,1,0,0,0))
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, data)

def main():
    CLASSES.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    create = INSTANCE / 'mods/create-1.20.1-6.0.8.jar'
    apoth = INSTANCE / 'mods/Apotheosis-1.20.1-7.4.8.jar'
    originals = {str(path):sha(path) for path in (create,apoth)}
    vanilla = LIBS / 'net/minecraft/client/1.20.1-20230612.114412/client-1.20.1-20230612.114412-srg.jar'
    deps = [vanilla, vanilla.with_name(vanilla.name.replace('-srg.jar','-extra.jar')),
            create, LIBS / 'org/spongepowered/mixin/0.8.5/mixin-0.8.5.jar']
    # Use Minecraft 1.20.1's exact bundled dependency versions, not a newer game's libraries.
    server_libs = ROOT / 'servers/cmi-expedition/instance/libraries'
    vanilla_bundle = server_libs / 'net/minecraft/server/1.20.1/server-1.20.1.jar'
    with zipfile.ZipFile(vanilla_bundle) as z:
        for line in z.read('META-INF/libraries.list').decode().splitlines():
            if not line.strip(): continue
            relative = line.split('\t')[2]
            dependency = LIBS / relative
            dependency = dependency if zipfile.is_zipfile(dependency) else server_libs / relative
            if zipfile.is_zipfile(dependency): deps.append(dependency)
    asm = [LIBS / f'org/ow2/asm/{name}/9.8/{name}-9.8.jar' for name in ['asm','asm-tree']]
    cp = os.pathsep.join(map(str,deps+asm))
    sources = sorted((TOOL/'src').rglob('*.java')) + sorted((TOOL/'tests').rglob('*.java'))
    run(['javac','--release','17','-proc:none','-encoding','UTF-8','-cp',cp,'-d',CLASSES,*sources], 'compile.log')
    runtime = os.pathsep.join([str(CLASSES),cp])
    inspect = run(['java','-Xverify:all','-cp',runtime,'ExtractAndInspect',apoth,create,CLASSES], 'targets.log')
    regression = run(['java','-Xverify:all','-Xmx512m','-cp',runtime,'TooltipRegression'], 'regression.log',90)
    config = {'required': True,'minVersion':'0.8','package':'expedition.storage.mixin','compatibilityLevel':'JAVA_17',
              'client':['StockKeeperTooltipMixin'],'injectors':{'defaultRequire':1}}
    jar = OUT / 'expedition-stock-keeper-tooltip-fix-1.0.0.jar'
    with zipfile.ZipFile(jar,'w',zipfile.ZIP_DEFLATED) as z:
        zip_member(z,'META-INF/MANIFEST.MF','Manifest-Version: 1.0\r\nMixinConfigs: expedition-stock-keeper-tooltip.mixins.json\r\n\r\n')
        zip_member(z,'META-INF/mods.toml','''modLoader="lowcodefml"
loaderVersion="[47,)"
license="MIT"
[[mods]]
modId="expedition_stock_keeper_tooltip_fix"
version="1.0.0"
displayName="Expedition Stock Keeper Tooltip Fix"
displayTest="IGNORE_SERVER_VERSION"
description="Builds Create Stock Keeper tooltips from item copies, preserving exact logistics NBT. Client only."
[[dependencies.expedition_stock_keeper_tooltip_fix]]
modId="minecraft"
mandatory=true
versionRange="[1.20.1,1.20.2)"
side="CLIENT"
[[dependencies.expedition_stock_keeper_tooltip_fix]]
modId="create"
mandatory=true
versionRange="[6.0.8]"
side="CLIENT"
''')
        zip_member(z,'expedition-stock-keeper-tooltip.mixins.json',json.dumps(config))
        zip_member(z,'pack.mcmeta',json.dumps({'pack':{'pack_format':15,
            'description':'Expedition Stock Keeper tooltip isolation compatibility patch'}}))
        for source in sorted((CLASSES/'expedition').rglob('*.class')):
            zip_member(z,source.relative_to(CLASSES).as_posix(),source.read_bytes())
    assert originals == {str(path):sha(path) for path in (create,apoth)}
    report = {'candidateOnly':True,'clientOnly':True,'activeInstanceModified':False,'serverModified':False,
        'minecraftStarted':False,'inWorldTestCompleted':False,'jar':str(jar),'sha256':sha(jar),
        'originalInputs':originals,'exactTargets':inspect.strip(),'regression':regression.strip(),
        'fix':'Copy only the two tooltip input stacks in StockKeeperRequestScreen.renderForeground; preserve original NBT and exact matching.',
        'scope':'Minecraft 1.20.1 Forge 47, Create 6.0.8; diagnosed with Apotheosis 7.4.8',
        'primaryEvidence':'https://github.com/Creators-of-Create/Create/issues/8559',
        'limitation':'Standalone real ItemStack/NBT and extracted installed Apotheosis method regression; full client launch/in-world order validation still required.'}
    (OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (OUT/'SHA256SUMS.txt').write_text(sha(jar)+'  '+jar.name+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
