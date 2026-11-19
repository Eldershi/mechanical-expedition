# Industrial compatibility for NeoForge 1.21.1

Install the `kubejs` scripts and data alongside the CMI material registrations. The recipes provide the copper, railway, Nether, precision, and coil mechanism lines. They also restore the cast iron and steel processes, seawater and lithium processing, and the Hexa casting and remelting routes for CMI mechanism bases and molds. The industry overlay also supplies CMI brass, cast iron, and shadow steel tool materials, plus the material data for restoring the two supported legacy melting pan combinations.

Vintage Improvements and the IE Bottling Machine provide red mud and aluminum dust production. The IE Arc Furnace produces refractory grout and pure semi-molten osmium. Smelting the grout yields refractory bricks. A superheated Create basin makes nitric acid, and an IE Coke Oven makes coal coke from charcoal.

A normally heated Create basin under a Mechanical Press compacts eight coal coke dust into one HOP graphite dust, or one HOP graphite dust into one ingot. A Create spout adds 100 mB of IE redstone acid to either HOP graphite dust or an ingot to make one activated graphite chunk. Run `python3 update_graphite_quest.py /path/to/config/ftbquests/quests` after importing the FTB quest data.

The Engineer's Workbench has parallel component blueprints for iron parts, steel parts and electron tubes. Its molds blueprint accepts industrial iron sheets for the ten CMI molds. The Coke Oven processes wood dust into charcoal dust and creosote. Refractory kiln bricks can be assembled into blast furnace bricks.

A Create mixer uses concrete powder and water to produce the corresponding sixteen Diesel Generators cement colors. IE liquid concrete cures adjacent sources with the IE Fix Pack. The IE Assembler uses standard crafting patterns for automation.

Stonecutting turns one andesite alloy, brass or copper plate into four matching casing frameworks. A Create deployer applies one framework to ordinary planks for the corresponding casing. A brass framework can also be applied to iron bars for a Create: Connected empty fan catalyst. The native casing and fan catalyst recipes remain available.

Superheated Create compaction makes two refined radrock from one radrock. A spout adds 100 mB of Mekanism liquid sulfuric acid to one refined radrock. A Vintage Improvements centrifuge separates the acid-washed rock into dense oxide film and toxic paste. Superheated mixing extracts 250 mB of radiation-resistant creosote from one film. A Mekanism Chemical Oxidizer makes radon from the toxic paste, and the Rotary Condensentrator liquefies it. Superheated mixing combines an HDPE sheet with 100 mB each of liquefied radon and radiation-resistant creosote to make an Alex's Caves polymer plate.

Hexa casts a reusable bronze nugget cast with 360 mB of molten bronze and a consumed metal nugget. Bronze and gold nugget casts can both be used in the native nugget casting recipes. The casting table also takes Biomes O' Plenty blood for blood slime.

Rope, amethyst, refined radiance, Desh, Ostrum and Calorite are Hexa tool materials. The space-metal melting temperatures are 2250, 2425 and 2600 °C, within the range of the supplied blazing blood fuel. The foundry supplies parallel casting recipes for eligible gear, plate and ingot forms alongside the existing manufacturing processes. Extendo applies to plate chestplates, and Diving allows a modified plate helmet to use a Create backtank underwater.

The hammer head is crafted from six iron or andesite alloy plates and three corresponding ingots. The Mechanical Press uses its native recipe. The reusable mechanism mold fits the Vintage Improvements Curving Press for mechanism assembly.

The quartz diode is assembled by Create mechanical crafters and feeds light engineering mechanism production. Hexa casts stone plates from lava for the basic mechanism part. The iron mechanism uses that part in its sequenced assembly. The Nether mechanism has recipes for the Blaze Burner, the Diesel Generators burner, and the Hexa scorched alloyer. The coil mechanism has recipes for the portable energy interface and Tesla coil. The IE Bottling Machine uses chromium plating solution to plate steel gears.

Run `python3 retire_thermal_content.py /path/to/instance` after copying the FTB quest data and assets. The chapter follows the pack's installed processing, fuel and assembly routes.

The integrated workstation uses an ender mechanism for the AE2 wireless receiver, spatial IO port, spatial pylon, and Infinity Booster card. The basic Mekanism mechanism is an input for five processing machines, the boiler and turbine valves, and the induction port. The advanced Mekanism mechanism is an input for six airtight processing machines and four fission reactor components. The fission fuel assembly uses a chemical tank and Diesel Generators cement. Each of these routes has its own recipe alongside the mod's recipe.

The integrated workstation makes the four tiers of Mekanism mechanism bases. Finish each tier on a Create sequenced assembly line. A deployer fits the matching control circuit and a chrome-plated steel gear. A Vintage Improvements laser cuts the workpiece, a spout adds 200 mB of redstone acid, and deployers fit a silicone rubber plate and a Mekanism mechanism part. Each pass yields one mechanism. The overview chapter in `quests/chapters` uses the same steps in its quest instructions.

Computing, aeronautic, astronautic, and antimatter mechanisms also finish on Create sequenced assembly lines. Assemble their bases in the workstation. A laser cuts each unfinished mechanism, and a spout supplies 200 mB of structural plastic for computing, aeronautic, and astronautic mechanisms or 250 mB of ferrouslime for antimatter mechanisms.

The recipe data adds four 250 mB spout recipes for Farmer’s Spell drinks and restores white placard dyeing. Eight solid concrete blocks make sixteen cinder bricks. Supplementaries soap cleans the Alex’s Caves painting variants back into smooth limestone. The Nether culinary integrations for giant beast croissant, magma sweet and sour pork, gilded barbaric roast, and warped juice are disabled. The CC: Tweaked train network monitor recipe is disabled and its item is hidden in the client recipe viewer. Both Tree Tap Menril recipes are disabled.

The integrated workstation produces nuclear mechanism bases, fissile cores, quantum parts, and finished nuclear mechanisms. The finished mechanism also has a Create sequenced route with Vintage Improvements laser cutting. Entro alloy uses Etrium and Cryotheum in the integrated workstation. A Create spout infuses a native Farmer's Delight knife with concentrated experience, yielding the unbreakable CMI knife.

The integrated workstation assembles the airtight mechanism base and installs a Crafted Beginning gas canister with liquid silicone rubber. Crafted Beginning's gas injection chamber seals the part using compressed air. The finished mechanism is an ingredient in the basic Mekanism chemical tank, Applied Mekanistics chemical cell housing, and eleven Mekanism machine recipes. The machine recipes use silicone rubber and the corresponding advanced or elite CMI components. The stonecutter shapes an airtight mechanism into the decorative Airtight Machine, which stores airtight mechanisms. The foundry accepts airtight mechanisms when making mechanism molds.

A heated Create basin conditions crude oil with water. The Diesel Generators distillation tower separates the conditioned feed into bitumen, sulfurous diesel, and kerosene. Use four stacked layers for this recipe. Kerosene yields gasoline and naphtha. The IE Refinery cracks 200 mB of gasoline with 100 units of steam and a reusable vanadium plate. Distilling the cracked gasoline yields naphtha, benzene and light olefins. Pure crude also retains the Diesel Generators fuel recipes.

The refinery cracks 100 mB of diesel with 100 units of steam and a reusable vanadium plate. The distillation tower separates the result into acetylene and light aldehydes. The refinery converts acetylene into vinyl alcohol and polyvinyl alcohol, then combines the polymer with light aldehydes to make structural plastic. Apply structural plastic to AE2 quartz glass in the IE Bottling Machine or mix it with aluminum and osmium plates in a Create basin for Osmium Tiles.

Both cracking recipes accept an airtight steam line from Create Crafted Beginning directly at either refinery inlet with [Refinery Steam Compatibility](../industrial). Fluid steam supplied through the existing fluid capability also matches the common steam tag.

A superchilled Create Crafted Beginning Airtight Fractionation Tower processes 10,000 units of natural air per 200-tick batch. Layer 1 yields 210 mB of Mekanism liquid oxygen and layer 2 yields 780 mB of liquid nitrogen. Give each layer its own liquid outlet and ordinary fluid tank. Feed the tower with the existing airtight natural-air network.

Refine IE plant oil and naphtha with a reusable copper plate to make lubricating oil. The heavy engineering mechanism uses this oil in its Create sequenced assembly and unlocks an additional recipe for the Diesel Generators huge engine.

Ferment rice in a covered Create basin or an IE Fermenter. The distillation tower separates vinegar into acetic acid and water. A heated Create basin combines silicon and light olefins to make light silicone ether. An IE Refinery with a reusable copper plate polymerizes the ether and reacts the polymer with acetic acid to make liquid silicone rubber. A Hexa casting table yields a piece of rubber when empty or a rubber plate when fitted with a reusable plate cast.

The bronze mechanism starts as a bronze plate curved with a mechanism mold. Fill it with molten bronze, then install a bronze cogwheel, a bronze plate, and a mechanical mechanism part. Steam Powered supplies the burners, boilers, engines, and flywheels for the steam power tasks. The three steam engines each have an additional recipe using the bronze mechanism. The Create spout and mechanical press handle filling and pressing.

With `nbtlib==2.0.4`, export supported legacy Tinkers tools, parts and manuals from copies of Anvil terrain or entity regions.

```sh
python3 export_legacy_tools.py --output /path/to/new-report.json /path/to/copied-region.mca
```

The report records the source chunk and NBT path, the original item data, and the corresponding Hexa stack. Durable tools retain their damage, materials and explicitly applied upgrades. Unsupported material or fluid combinations are recorded as withheld with the original item data intact. Apply the converted stacks separately to the migration copy.
