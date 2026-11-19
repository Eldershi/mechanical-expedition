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

The quartz diode is assembled by Create mechanical crafters and feeds light engineering mechanism production. Hexa casts stone plates from lava for the basic mechanism part. The iron mechanism uses that part in its sequenced assembly. Capture a Blaze with Create's empty burner or craft the filled Blaze Burner with a blaze rod and an iron mechanism. The Nether mechanism is used in parallel recipes for the Diesel Generators burner, Hexa scorched alloyer, and Mekanism energized smelter. The Blaze Burner quest follows the Nether visit, and the foundry quest follows the foundry materials. The coil mechanism has recipes for the portable energy interface and Tesla coil. The IE Bottling Machine uses chromium plating solution to plate steel gears.

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

Press sugar cane in a Create basin to obtain sugar syrup and cane fiber. Press beetroot for syrup or use the sugar-fed syrup recipes. Dry fiber in a furnace or smoker to get paper, or use an item drain to recover paper and residual syrup. Heat syrup in a basin to make sugar. A covered basin and a bulk fermenter both turn syrup and crops into ethanol, which combines with plant oil to make biodiesel.

Smelt plants, flowers, leaves, bark or wood dust in a furnace to make plant ash. An IE Garden Cloche can use the ash as fertilizer at the original 1.2 growth multiplier.

The fuel chapter accepts a dried kelp block. Smelt kelp, then craft nine dried kelp into one block.

Superheat the airtight reactor kettle and pipe in 1,000 units of ultrawarm air per moon stone to obtain one pyrolyzed residue and 10 units of helium-3. Wash the residue for independently rolled machalite, machalite dust and dirty uranium dust. Create crushing wheels and millstones each turn one machalite into one dust. A normally heated kettle uses four dust, 500 mB of polysilicone ether, and 5,000 units of ultrawarm air to produce 1,000 mB of molten pure silicon. The reusable gem cast in the Hexa casting table or the airtight forging press takes 250 mB to form one crystal. Saw the crystal into a wafer for the AE2 inscriber. The existing AE2 silicon and wafer recipes also supply the inscriber.

The airtight forging press uses the gem cast in its press-head slot. A player or deployer can exchange the head. A parallel recipe can use a reusable head with one fluid feed or a solid input supported by the native press. Hexa retains its recipes for empty tables and consumed casts. Mold wear, multiple fluids, temperature conditions and sequenced Vintage Improvements steps remain on their respective machines. The standalone Vintage Improvements recipes use a built-in bucket head, a reusable silicon plate mold, or the mod's custom-head example. The CMI silicon plate mold continues to press ordinary AE2 silicon into printed silicon in the Vintage Improvements Curving Press.

The Large Electrolytic Cell uses enriched germanium-iron mixture and molten neodymium mixture to produce dragonite and 125 mB of ferrouslime. Grind dragonite, then dissolve the dust in 100 mB of liquid sulfuric acid in a heated basin. Vaporize 100 mB of germanium solution in Mekanism's Rotary Condensentrator and crystallize all 100 chemical units into one germanium crystal. The same converter also accepts the solution separated from magnetic sediment. The initial Mars-sand route continues to supply germanium for the elite circuit.

Reduce Entro peroxide solution with sodium reducing agent in a chilled airtight kettle, or convert the peroxide solution to a chemical in the Rotary Condensentrator. The Pressurized Reaction Chamber uses 100 units of that chemical, 50 mB of liquid nitrogen and one reducing agent per crystal. The rotary recipes for the germanium precursor and Entro peroxide operate in fluid-to-chemical mode.

Send end stone to Create crushing wheels in batches of at least two. Each pair produces six CMI end stone dust and a lone remainder exits intact. A single-block feed uses the installed one-block recipe. The Huge Crushing Machine makes 48 dust from 16 end stone. A heated basin mixes one dust, one delta blackstone source, and 50 mB of redstone acid into 200 mB of unstable solution.

At ambient temperature, the airtight reactor kettle uses one blackstone and 50 mB of brimstone from the native gas injection chamber. It produces one alpha, beta and gamma source per batch. A Create spout infuses each source with 100 mB of crystal catalyst, and the powered grindstone turns the resulting source crystals into ruby, sapphire and emerald. Ruby can feed the existing chromium process. The Alloy Furnace uses one of each source to make one delta source.

Crush reduced Entro crystal in Create's crushing wheels or millstone or the Mekanism Crusher. The Large Electrolytic Cell combines the dust and 50 mB of liquid crystal Etrium into an Etrium peroxide crystal and 50 mB of crystalline Entro solution. A heated airtight kettle uses 50 mB each of molten silicon-containing compound, delta unstable solution and pure crystal source to make four Entro compounds. The Shaft Furnace processes the compound and the oxidizer into liquid crystal Entro, which the kettle combines with the crystalline Entro solution to make two Entro alloy.

The Osmium Compressor makes chaotic void dust with one unit of osmium. Feed the dust to a Metallurgic Infuser to convert it to an infusion chemical. Infuse osmium dust to make infused osmium, which supplies an additional carbon nanotube recipe. Infuse magnetic alloy with titanium oxide for piezoelectric ceramic. The ceramic is an ingredient in the magnetic contact and an alternative fusion reactor frame recipe. Charging a chromatic compound uses 5,000 FE and makes an overcharged alloy ingot for a parallel Pattern Encoding Terminal recipe.

Crush ordinary Galena in the crushing wheels, millstone, Mekanism Crusher or Huge Crushing Machine. The Shaft Furnace turns the dust into a magnetic source. The Large Electrolytic Cell combines that source with ionized red dust for magnetic sediment and 100 mB of germanium solution. The same cell separates spiritcore into two crystals, and the Shaft Furnace melts the ionized crystal. The AE2 inscriber uses piezoelectric ceramic at the bottom, ferrite core in the middle and a composite magnetic conduction plate at the top. The integrated workstation accepts the resulting contacts for a parallel wireless energy tower recipe.

The Alloy Furnace makes one magnetic alloy from one iron ingot, one magnetic source and 15 mB each of molten azure and scarlet neodymium. Hexa melts each color's ingot at 1024 °C into 90 mB. The Large Electrolytic Cell uses 100 mB of each color and one magnetic sediment to make 200 mB of molten neodymium mixture and one refractory material powder.

The Large Electrolytic Cell separates bromine and waste brine from alkaline brine and liquid chlorine. The airtight reactor kettle combines 200 mB of bromine with two refractory powder. The Mechanical Press compacts the resulting flame retardant with an Alex's Caves polymer plate in a superheated basin, yielding two flame-retardant plastic.

The Alloy Furnace accepts ingots or dusts of chromium and vanadium to make two polymerization catalytic alloy. The Hydropress uses one alloy and 1 mB of water to make two ethylene polymerization catalytic plates. An IE Refinery uses the plate as a reusable catalyst for ethene. The Mechanical Press solidifies the HDPE into pellets in a heated basin. Mekanism's native HDPE route remains available.

Blast raw vanadium into a Vintage Improvements vanadium ingot, then press it into a vanadium sheet. IE's steam cracking recipes use the same sheet as a reusable catalyst.

Process unrefined waste in the airtight reactor kettle and pipe its waste gas into the chilled airtight fractionation tower. The tower separates it into polonium and plutonium electrolytes. Fluorite processing supplies radioactive sediment, raw polonium and the ionized plutonium crystal. Mill raw polonium into powder, react it with radioactive acid and reduce the resulting polonium solution with zinc dust. The native uranium and polonium production recipes remain available.

When actively cooling, a Snow Golem Freezer or Breeze Cooler supplies either mod's chilled basin mixing and compacting recipes and encased fan cooling. A fan tries its selected source's native recipe first. A captured Snow Golem Freezer without fuel still provides its original passive Dragons Plus freezing. Ordinary ice likewise supplies passive freezing. Airtight kettles and fractionation towers use their native thermoregulator sources.

The bronze mechanism starts as a bronze plate curved with a mechanism mold. Fill it with molten bronze, then install a bronze cogwheel, a bronze plate, and a mechanical mechanism part. Steam Powered supplies the burners, boilers, engines, and flywheels for the steam power tasks. The three steam engines each have an additional recipe using the bronze mechanism. The Create spout and mechanical press handle filling and pressing.

With `nbtlib==2.0.4`, export supported legacy Tinkers tools, parts and manuals from copies of Anvil terrain or entity regions.

```sh
python3 export_legacy_tools.py --output /path/to/new-report.json /path/to/copied-region.mca
```

The report records the source chunk and NBT path, the original item data, and the corresponding Hexa stack. Durable tools retain their damage, materials and explicitly applied upgrades. Unsupported material or fluid combinations are recorded as withheld with the original item data intact. Apply the converted stacks separately to the migration copy.
