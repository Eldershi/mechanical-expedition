"""Compose a Minecraft 1.20.1 HUD atlas from two supplied resource packs."""
import argparse
import io
import json
from pathlib import Path
import zipfile
from PIL import Image

ICONS = 'assets/minecraft/textures/gui/icons.png'
FOOD_SLOTS = (16, 25, 52, 61, 88, 97, 133, 142)

def build(gui_pack, food_pack, output):
    with zipfile.ZipFile(gui_pack) as gui, zipfile.ZipFile(food_pack) as food:
        base = Image.open(io.BytesIO(gui.read(ICONS))).convert('RGBA')
        source = Image.open(io.BytesIO(food.read(ICONS))).convert('RGBA')
        if base.size != (256, 256) or source.size != (256, 256):
            raise ValueError('Expected Minecraft 1.20.1 256x256 HUD atlases')
        result = base.copy()
        for x in FOOD_SLOTS:
            box = (x, 27, x + 9, 36)
            result.paste(source.crop(box), box)
        for y in range(256):
            for x in range(256):
                preserved = 27 <= y < 36 and any(left <= x < left + 9 for left in FOOD_SLOTS)
                expected = source.getpixel((x, y)) if preserved else base.getpixel((x, y))
                if result.getpixel((x, y)) != expected:
                    raise ValueError('HUD atlas verification failed')
        buffer = io.BytesIO()
        result.save(buffer, format='PNG')
        entries = {ICONS: buffer.getvalue(), 'pack.mcmeta': (json.dumps({'pack': {'pack_format': 15, 'description': 'Create HUD with yellow apple food icons'}}, ensure_ascii=False, indent=2) + '\n').encode()}
        apple = 'assets/appleskin/textures/icons.png'
        if apple in food.namelist():
            entries[apple] = food.read(apple)
        prefix = 'assets/minecraft/textures/gui/sprites/hud/food'
        for name in food.namelist():
            if name.startswith(prefix) and name.endswith('.png'):
                entries[name] = food.read(name)
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(entries.items()):
                item = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
                item.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(item, data)
    return output

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gui-pack', type=Path, required=True)
    parser.add_argument('--food-pack', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(build(args.gui_pack, args.food_pack, args.output))
