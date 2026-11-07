# Crop appearance

Duplicate tomatoes, rice and onions use the installed Farmer's Delight textures.
Client model overrides cover the Cookery and Thermal crop items, tomato seeds,
Thermal rice seeds, Cookery rice panicles and all planted growth states. The
original crop geometry, number of segments and block states remain in use.

Item identity, planting, recipes, drops and the existing One Enough Item rules
are unchanged. Thermal onion seeds retain their seed appearance because
Farmer's Delight plants onion bulbs and has no matching onion-seed texture.
Lettuce, cabbage, flax, tea and Nether rice are distinct crops or have no
Farmer's Delight counterpart and retain their own appearance.

The generated JSON models reference Farmer's Delight assets directly; no
third-party texture files are copied. This is client content and requires
Farmer's Delight, Kaleidoscope Cookery and Thermal Cultivation.

Build into an empty staging directory:

```sh
python3 tools/crop-appearance/build.py --instance /path/to/client --output /path/to/staging
```

The builder validates source model layouts, texture references and coverage of
every affected planted block state before writing the client overrides.
