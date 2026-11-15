# HUD food style composition

The builder preserves the supplied GUI pack's health, armor, air, experience and attack indicators. Only normal and Hunger-effect food slots come from the food pack. AppleSkin's food and saturation textures are preserved byte for byte.

Requires Python 3 and Pillow. Supply resource packs you have permission to use:

```sh
python build.py --gui-pack gui.zip --food-pack food.zip --output food-hud.zip
```

Load the generated pack after both inputs. The input packs and generated textures are not redistributed by this source directory. For layered health counters, use Overflowing Bars 8.0.1 and disable Mantle's `heartRenderer` so that only one renderer handles player health.
