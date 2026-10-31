"""Resolve only the installed Forge 1.20.1 runtime, never mixed launcher versions."""
from pathlib import Path
import shlex

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
INSTANCE = WORKSPACE / 'servers/cmi-expedition/instance'
ARGS = INSTANCE / 'libraries/net/minecraftforge/forge/1.20.1-47.4.10/unix_args.txt'
LAUNCHER_LIBS = (Path.home() / 'Library/Application Support/Swift Craft Launcher/meta/libraries')
SRG = LAUNCHER_LIBS / 'net/minecraft/client/1.20.1-20230612.114412/client-1.20.1-20230612.114412-srg.jar'


def classpath(client=False):
    args = shlex.split(ARGS.read_text())
    paths = [SRG]
    for index, arg in enumerate(args):
        if arg.startswith('-DlegacyClassPath='):
            paths.extend(INSTANCE / item for item in arg.split('=', 1)[1].split(':'))
        elif arg in ('-p', '--module-path', '-cp', '--class-path'):
            paths.extend(INSTANCE / item for item in args[index + 1].split(':'))
    if client:
        paths.append(INSTANCE / 'libraries/net/minecraftforge/forge/1.20.1-47.4.10/forge-1.20.1-47.4.10-universal.jar')
    paths = list(dict.fromkeys(path.resolve() for path in paths))
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError('Missing pinned 1.20.1 dependencies: ' + ', '.join(missing))
    dfu = [path for path in paths if 'datafixerupper' in str(path)]
    if len(dfu) != 1 or dfu[0].name != 'datafixerupper-6.0.8.jar':
        raise RuntimeError('Expected exactly Minecraft 1.20.1 DataFixerUpper 6.0.8')
    return paths
