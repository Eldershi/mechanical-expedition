#!/usr/bin/env python3
"""Build a server-only Forge command observer; never write active game files."""
from pathlib import Path
import hashlib,json,os,subprocess,zipfile
TOOL=Path(__file__).resolve().parent
ROOT=TOOL.parents[1]
OUT=ROOT/'releases/ftb-action-announcements-20261027'
BUILD=TOOL/'build'
CLASSES=BUILD/'classes'
LIBS=(Path.home() / 'Library/Application Support/Swift Craft Launcher/meta/libraries')
INSTANCE=(Path.home() / 'Library/Application Support/Swift Craft Launcher/profiles/机械远征-CMI-迁移测试')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(args,name):
    result=subprocess.run(list(map(str,args)),text=True,capture_output=True,timeout=50)
    (BUILD/name).write_text(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    return result.stdout+result.stderr
def member(z,name,blob):
    info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.create_system=3;info.external_attr=0o100644<<16;info.compress_type=zipfile.ZIP_DEFLATED
    z.writestr(info,blob)
def main():
    CLASSES.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    vanilla=LIBS/'net/minecraft/client/1.20.1-20230612.114412/client-1.20.1-20230612.114412-srg.jar'
    deps=[vanilla]
    for rel in ['net/minecraftforge/forge/1.20.1-47.4.10','net/minecraftforge/fmlcore/1.20.1-47.4.10',
        'net/minecraftforge/javafmllanguage/1.20.1-47.4.10','net/minecraftforge/fmlloader/1.20.1-47.4.10',
        'net/minecraftforge/eventbus','com/mojang/brigadier/1.1.8','com/google/guava/guava/31.1-jre',
        'com/mojang/datafixerupper/6.0.8','com/google/code/gson/gson/2.10','org/jetbrains/annotations']:
        deps.extend(p for p in (LIBS/rel).rglob('*.jar') if zipfile.is_zipfile(p))
    cp=os.pathsep.join(map(str,deps))
    run(['javac','--release','17','-proc:none','-encoding','UTF-8','-cp',cp,'-d',CLASSES,
         *sorted((TOOL/'src').rglob('*.java')),*sorted((TOOL/'tests').rglob('*.java'))],'compile.log')
    regression=run(['java','-Xverify:all','-cp',str(CLASSES)+os.pathsep+cp,'ActionRegression'],'regression.log')
    ftb=INSTANCE/'mods/ftb-library-forge-2001.2.13.jar'
    with zipfile.ZipFile(ftb) as z:buttons=json.loads(z.read('assets/ftblibrary/sidebar_buttons.json'))
    clicks={k:v['click'] for k,v in buttons.items()}
    assert set(clicks.values())=={'command:/ftblibrary '+a for a in ['gamemode','rain','day','night']}
    assert all(v.get('requires_op') is True for v in buttons.values())
    bytecode=run(['javap','-classpath',ftb,'-c','-p','dev.ftb.mods.ftblibrary.FTBLibraryCommands'],'ftb-commands.javap.txt')
    permission=bytecode[bytecode.index('private static boolean lambda$registerCommands$0'):]
    assert 'iconst_2' in permission and 'm_6761_' in permission
    jar=OUT/'expedition-ftb-action-announcements-1.0.0.jar'
    with zipfile.ZipFile(jar,'w',zipfile.ZIP_DEFLATED) as z:
        member(z,'META-INF/MANIFEST.MF','Manifest-Version: 1.0\r\n\r\n')
        member(z,'META-INF/mods.toml','''modLoader="javafml"
loaderVersion="[47,)"
license="Private modpack compatibility patch"
[[mods]]
modId="expedition_ftb_action_announcements"
version="1.0.0"
displayName="Expedition FTB Action Announcements"
displayTest="IGNORE_ALL_VERSION"
description="Announce successful changed FTB sidebar weather, day/night, and gamemode actions to all players. Server only."
[[dependencies.expedition_ftb_action_announcements]]
modId="minecraft"
mandatory=true
versionRange="[1.20.1,1.20.2)"
side="SERVER"
[[dependencies.expedition_ftb_action_announcements]]
modId="ftblibrary"
mandatory=true
versionRange="[2001.2.13]"
side="SERVER"
''')
        member(z,'pack.mcmeta',json.dumps({'pack':{'pack_format':15,'description':'Expedition FTB action chat announcements'}}))
        for path in sorted((CLASSES/'expedition').rglob('*.class')):member(z,path.relative_to(CLASSES).as_posix(),path.read_bytes())
    report={'jar':str(jar),'sha256':sha(jar),'serverOnly':True,'activeInstanceModified':False,'onlineServerModified':False,
      'ftbLibraryVersion':'2001.2.13','ftbJarSha256':sha(ftb),'sidebarButtons':clicks,
      'originalPermission':'ftblibrary root requires permission level2; sidebar requires_op=true; unchanged',
      'implementation':'Forge CommandEvent LOWEST, uncanceled; exact two-node four FTB leaves; wraps existing callback only',
      'successRule':'Original handler returns >0 and actual state changes; exactly one global system-chat broadcast',
      'weatherState':'Persistent LevelData rain/thunder flags, not interpolated rain strength',
      'regression':regression.strip(),'minecraftOrForgeStarted':False,'liveMultiplayerTestCompleted':False,
      'limitation':'Actual Brigadier tests with isolated state; Forge/server and two-player chat test still outstanding.'}
    (OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (OUT/'SHA256SUMS.txt').write_text(sha(jar)+'  '+jar.name+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
