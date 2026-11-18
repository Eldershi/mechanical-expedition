package expedition.space.test;

import cn.dancingsnow.neoecoae.blocks.entity.ECOIntegratedWorkingStationBlockEntity;
import cn.dancingsnow.neoecoae.recipe.IntegratedWorkingStationRecipe;
import com.simibubi.create.content.processing.recipe.ProcessingRecipe;
import com.simibubi.create.content.processing.sequenced.SequencedAssemblyRecipe;
import earth.terrarium.adastra.api.planets.Planet;
import earth.terrarium.adastra.api.planets.PlanetApi;
import earth.terrarium.adastra.common.blockentities.machines.NasaWorkbenchBlockEntity;
import earth.terrarium.adastra.common.config.AdAstraConfig;
import earth.terrarium.adastra.common.entities.vehicles.Rocket;
import earth.terrarium.adastra.common.recipes.machines.NasaWorkbenchRecipe;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import mekanism.api.recipes.PressurizedReactionRecipe;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.capabilities.Capabilities;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;
import net.neoforged.neoforge.common.util.FakePlayerFactory;
import net.neoforged.neoforge.fluids.FluidStack;
import net.neoforged.neoforge.fluids.capability.IFluidHandler;
import net.neoforged.neoforge.items.IItemHandler;

@Mod("expedition_space_manufacturing_probe")
public final class SpaceManufacturingProbe {
    private static final String PATH = "expedition:factory/space/";
    private static final BlockPos LAUNCH_SITE = new BlockPos(7, 72, 8);
    private static final List<String> MATERIALS = List.of("steel", "desh", "ostrum", "calorite");
    private static final List<String> STATION_SUPPORT = List.of("incomplete_tungsten_steel_plate",
        "carbon_polymerization_catalytic_plate", "incomplete_composite_carbon_fiber_plate",
        "superconducting_mercury_ingot", "composite_magnetic_conduction_plate", "astronautic_mechanism_basement",
        "astronautic_mechanism", "engine_frame");

    private final List<StationRun> stations = new ArrayList<>();
    private final Map<String, ItemStack> products = new HashMap<>();
    private ServerLevel level;
    private Rocket launchRocket;
    private LivingEntity testPassenger;
    private int ticks;

    public SpaceManufacturingProbe() {
        NeoForge.EVENT_BUS.addListener(this::register);
        NeoForge.EVENT_BUS.addListener(this::tick);
    }

    private void register(RegisterCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("expeditionspaceproof")
            .requires(source -> source.hasPermission(4)).executes(context -> {
                level = context.getSource().getLevel();
                level.setChunkForced(0, 0, true);
                return 1;
            }));
    }

    private void tick(ServerTickEvent.Post event) {
        if (level == null) return;
        try {
            if (stations.isEmpty() && level.hasChunkAt(new BlockPos(2, -40, 5))) prepare();
            for (var station : stations) advance(station);
            if (!stations.isEmpty() && stations.stream().allMatch(StationRun::finished)) {
                if (launchRocket == null) prepareLaunch(assembleRockets());
                else if (launchRocket.hasLaunched() && launchRocket.getY() > LAUNCH_SITE.getY() + 1) {
                    var tank = launchRocket.getCapability(Capabilities.FluidHandler.ENTITY, Direction.UP);
                    require(tank != null && tank.getFluidInTank(0).isEmpty(), "rocket did not consume loaded fuel");
                    System.out.println("EXPEDITION_SPACE_LAUNCH tier=" + launchRocket.tier()
                        + " y=" + launchRocket.getY() + " fuelConsumed=" + AdAstraConfig.launchFuelCost);
                    System.out.println("EXPEDITION_SPACE_PASS stationProducts=" + products.size() + " rockets=4");
                    stop();
                    return;
                } else testPassenger.setJumping(true);
            }
            require(++ticks < 2600, "timed out after producing " + products.keySet());
        } catch (Exception error) {
            error.printStackTrace();
            System.out.println("EXPEDITION_SPACE_FAILED " + error);
            stop();
        }
    }

    private void prepare() {
        int total = 0;
        for (var recipe : level.getRecipeManager().getRecipes()) {
            if (!recipe.id().toString().startsWith(PATH)) continue;
            if (recipe.value() instanceof IntegratedWorkingStationRecipe working) {
                require(working.inputItems().stream().allMatch(i -> i.ingredient().getItems().length > 0),
                    "empty workstation input " + recipe.id());
            } else if (recipe.value() instanceof NasaWorkbenchRecipe nasa) {
                require(nasa.ingredients().stream().allMatch(i -> i.getItems().length > 0), "empty NASA input " + recipe.id());
            } else if (recipe.value() instanceof SequencedAssemblyRecipe assembly) {
                require(assembly.getIngredient().getItems().length > 0, "empty sequence input " + recipe.id());
                for (var step : assembly.getSequence()) checkProcessingInput(step.getRecipe(), recipe.id());
            } else if (recipe.value() instanceof ProcessingRecipe<?, ?> processing) {
                checkProcessingInput(processing, recipe.id());
            } else if (!recipe.value().getIngredients().isEmpty() || recipe.value() instanceof PressurizedReactionRecipe) {
                require(!recipe.value().isIncomplete(), "incomplete recipe " + recipe.id());
            }
            total++;
        }
        require(total >= 51, "too few loaded space recipes: " + total);
        System.out.println("EXPEDITION_SPACE_RECIPE_REGISTRY recipes=" + total);
        checkStages();
        checkOre("etrium_ore", "raw_etrium");
        checkOre("deepslate_etrium_ore", "raw_etrium");
        checkOre("galena_titanium_ore", "raw_titanium");
        assertReaction("mercury_mixture_from_cinnabar", "alltheores:cinnabar_dust", "cmi:mercury_mixture", 10);
        assertReaction("superconducting_mercury_ingot_from_mixture", "alltheores:silver_ingot", "mekanism:sulfur_trioxide", 100);

        stations.add(station(new BlockPos(2, -40, 5), STATION_SUPPORT));
        for (int i = 0; i < MATERIALS.size(); i++) {
            String tier = "tier_" + (i + 1) + "_rocket_";
            String metal = MATERIALS.get(i);
            stations.add(station(new BlockPos(5 + i * 3, -40, 5), List.of(tier + "nose_cone", tier + "body",
                tier + "fin", metal + "_engine", metal + "_tank")));
        }
    }

    private void checkStages() {
        int[] availableTiers = {1, 2, 3, 3, 4};
        var planetKeys = List.of(Planet.MOON, Planet.MARS, Planet.MERCURY, Planet.VENUS, Planet.GLACIO);
        for (int i = 0; i < availableTiers.length; i++) {
            var key = planetKeys.get(i);
            var planet = PlanetApi.API.getPlanet(key);
            require(planet != null && planet.tier() == availableTiers[i] && level.getServer().getLevel(key) != null,
                "inaccessible planet registry target " + key.location());
            System.out.println("EXPEDITION_SPACE_DESTINATION " + key.location() + " tier=" + planet.tier());
        }
        for (var id : List.of("ad_astra:nasa_workbench", "ad_astra:launch_pad", "ad_astra:fuel_refinery",
                "ad_astra:refining/fuel_from_refining_oil",
                "ad_astra:oxygen_loader", "ad_astra:oxygen_gear", "ad_astra:etrionic_capacitor", "ad_astra:fan",
                "expedition:factory/metallurgy/chromium_ingot", "expedition:radar/acquisition/molten_etrium")) {
            require(level.getRecipeManager().byKey(ResourceLocation.parse(id)).isPresent(), "missing supporting recipe " + id);
        }
    }

    private void checkOre(String ore, String raw) {
        var material = stack("cmi:" + raw);
        var block = block("cmi:" + ore);
        var drops = Block.getDrops(block.defaultBlockState(), level, BlockPos.ZERO, null, null, new ItemStack(Items.DIAMOND_PICKAXE));
        require(drops.stream().anyMatch(drop -> ItemStack.isSameItem(drop, material)), "ore did not drop " + material);
        boolean magnetic = ore.startsWith("galena");
        var feature = ResourceKey.create(Registries.PLACED_FEATURE, ResourceLocation.parse(
            magnetic ? "cmi:galena_titanium_ore" : "cmi:etrium_ore"));
        var placement = level.registryAccess().registryOrThrow(Registries.PLACED_FEATURE).getHolderOrThrow(feature);
        var biome = level.registryAccess().registryOrThrow(Registries.BIOME).get(ResourceLocation.parse(
            magnetic ? "alexscaves:magnetic_caves" : "minecraft:plains"));
        require(biome.getGenerationSettings().features().stream().anyMatch(set -> set.contains(placement)),
            "ore placement missing from native " + (magnetic ? "magnetic caves" : "overworld"));
        var blast = recipe(raw.equals("raw_titanium") ? "titanium_ingot" : "etrium_ingot");
        require(blast.getIngredients().stream().anyMatch(ingredient -> ingredient.test(material)), "ore cannot be refined " + material);
        System.out.println("EXPEDITION_SPACE_ORE ore=" + ore + " drop=" + material + " refined="
            + blast.getResultItem(level.registryAccess()));
    }

    private void checkProcessingInput(ProcessingRecipe<?, ?> recipe, ResourceLocation id) {
        require(recipe.getIngredients().stream().allMatch(i -> i.getItems().length > 0)
            && recipe.getFluidIngredients().stream().allMatch(i -> i.ingredient().getStacks().length > 0),
            "empty Create input " + id);
    }

    private void assertReaction(String id, String itemId, String chemicalId, long amount) {
        var reaction = (PressurizedReactionRecipe) recipe(id);
        var input = stack(itemId);
        var fluid = reaction.getInputFluid().getRepresentations().getFirst();
        var chemical = reaction.getInputChemical().getRepresentations().getFirst();
        require(reaction.test(input, fluid, chemical), "native reaction did not accept " + input);
        var result = reaction.getOutput(input, fluid, chemical);
        require(result.chemical().getAmount() == amount && result.chemical().getChemicalHolder()
            .unwrapKey().orElseThrow().location().equals(ResourceLocation.parse(chemicalId)), "unexpected chemical output " + result);
        System.out.println("EXPEDITION_SPACE_REACTION " + id + " output=" + result);
    }

    private StationRun station(BlockPos position, List<String> outputs) {
        level.setBlock(position, block("neoecoae:integrated_working_station").defaultBlockState(), Block.UPDATE_ALL);
        level.setBlock(position.east(), block("ae2:creative_energy_cell").defaultBlockState(), Block.UPDATE_ALL);
        var station = (ECOIntegratedWorkingStationBlockEntity) level.getBlockEntity(position);
        require(station != null, "missing integrated working station at " + position);
        return new StationRun(station, outputs);
    }

    private void advance(StationRun run) {
        if (run.finished() || !run.station.getMainNode().isActive()) return;
        var name = run.outputs.get(run.index);
        IItemHandler items = level.getCapability(Capabilities.ItemHandler.BLOCK, run.station.getBlockPos(), Direction.UP);
        require(items != null, "no workstation item capability");
        if (run.running == null) {
            run.working = false;
            run.running = (IntegratedWorkingStationRecipe) recipe(name);
            for (int i = 0; i < run.running.inputItems().size(); i++) {
                var input = run.running.inputItems().get(i);
                var variants = input.ingredient().getItems();
                require(variants.length > 0, "empty input in station recipe " + name);
                require(items.insertItem(i, variants[0].copyWithCount(input.count()), false).isEmpty(),
                    "station rejected " + variants[0] + " in " + name);
            }
            if (!run.running.inputFluid().ingredient().isEmpty()) {
                var fluid = run.running.inputFluid().ingredient().getStacks()[0].copy();
                fluid.setAmount(run.running.inputFluid().amount());
                require(run.station.getFluidCombined().fill(fluid, IFluidHandler.FluidAction.EXECUTE) == fluid.getAmount(),
                    "station rejected fluid in " + name);
            }
        } else {
            run.working |= run.station.isWorking();
            for (int slot = 0; slot < items.getSlots(); slot++) {
                var candidate = items.extractItem(slot, 64, true);
                if (!ItemStack.matches(candidate, run.running.itemOutput())) continue;
                require(run.working, "station never processed " + name);
                var actual = items.extractItem(slot, 64, false);
                require(ItemStack.matches(candidate, actual), "station could not extract " + name);
                products.put(name, actual);
                System.out.println("EXPEDITION_SPACE_STATION " + name + " result=" + actual + " energy=" + run.running.energy());
                run.running = null;
                run.index++;
                return;
            }
        }
    }

    private ItemStack assembleRockets() {
        var site = new BlockPos(7, -40, 10);
        level.setBlock(site, block("ad_astra:nasa_workbench").defaultBlockState(), Block.UPDATE_ALL);
        var bench = (NasaWorkbenchBlockEntity) level.getBlockEntity(site);
        require(bench != null && bench.items().size() == 15, "no physical 14-input NASA workbench");
        ItemStack tierOne = ItemStack.EMPTY;
        for (int i = 0; i < MATERIALS.size(); i++) {
            int tier = i + 1;
            String name = "tier_" + tier + "_rocket";
            String metal = MATERIALS.get(i);
            var original = ResourceLocation.parse("ad_astra:nasa_workbench/" + name + "_from_nasa_workbench");
            require(level.getRecipeManager().byKey(original).isPresent(), "native recipe missing " + original);
            var custom = (NasaWorkbenchRecipe) recipe(name);
            require(custom.ingredients().size() == 14, "wrong slot count for " + name);
            var nose = products.get(name + "_nose_cone");
            var body = products.get(name + "_body");
            var fin = products.get(name + "_fin");
            var tank = products.get(metal + "_tank");
            var engine = products.get(metal + "_engine");
            var order = List.of(nose, body, body, body, body, body, body, fin, tank, tank, fin, fin, engine, fin);
            for (int slot = 0; slot < order.size(); slot++) bench.items().set(slot, order.get(slot).copyWithCount(1));
            bench.items().set(12, tank.copyWithCount(1));
            bench.update();
            require(!bench.canCraft(), "wrong engine slot still crafted " + name);
            bench.items().set(12, engine.copyWithCount(1));
            bench.update();
            require(bench.canCraft(), "NASA workbench could not assemble " + name);
            var expected = stack("ad_astra:" + name);
            bench.serverTick(level, 1, bench.getBlockState(), site);
            require(ItemStack.matches(bench.items().get(14), expected), "NASA workbench showed the wrong result");
            bench.craft();
            var output = level.getEntitiesOfClass(ItemEntity.class, new AABB(site).inflate(3),
                entity -> ItemStack.matches(entity.getItem(), expected));
            require(output.size() == 1, "NASA workbench did not release " + name);
            var built = output.getFirst().getItem().copy();
            output.getFirst().discard();
            require(bench.items().subList(0, 14).stream().allMatch(ItemStack::isEmpty), "NASA inputs not consumed");
            System.out.println("EXPEDITION_SPACE_NASA tier=" + tier + " result=" + built + " slots=14");
            if (tier == 1) tierOne = built.copy();
            bench.items().set(14, ItemStack.EMPTY);
        }
        return tierOne;
    }

    private void prepareLaunch(ItemStack built) {
        var astronaut = FakePlayerFactory.getMinecraft(level);
        astronaut.setPos(LAUNCH_SITE.getX() + 0.5, LAUNCH_SITE.getY(), LAUNCH_SITE.getZ() - 3.5);
        for (var existing : level.getEntitiesOfClass(Rocket.class, new AABB(LAUNCH_SITE).inflate(6))) existing.discard();
        for (var pos : BlockPos.betweenClosed(LAUNCH_SITE.offset(-1, -1, -1), LAUNCH_SITE.offset(1, -1, 1))) {
            level.setBlock(pos, Blocks.STONE.defaultBlockState(), Block.UPDATE_ALL);
            level.removeBlock(pos.above(), false);
        }
        var padItem = stack("ad_astra:launch_pad");
        var ground = LAUNCH_SITE.below();
        var placeOn = new BlockHitResult(Vec3.atCenterOf(ground), Direction.UP, ground, false);
        astronaut.setItemInHand(InteractionHand.MAIN_HAND, padItem);
        require(((BlockItem) padItem.getItem()).place(new BlockPlaceContext(astronaut, InteractionHand.MAIN_HAND,
            padItem, placeOn)).consumesAction(), "launch pad rejected the site");
        astronaut.setItemInHand(InteractionHand.MAIN_HAND, built);
        var pad = new BlockHitResult(Vec3.atCenterOf(LAUNCH_SITE), Direction.UP, LAUNCH_SITE, false);
        require(built.getItem().useOn(new UseOnContext(astronaut, InteractionHand.MAIN_HAND, pad)).consumesAction(),
            "assembled rocket could not be placed");
        var nearby = level.getEntitiesOfClass(Rocket.class, new AABB(LAUNCH_SITE).inflate(6));
        require(nearby.size() == 1, "did not find the placed rocket");
        launchRocket = nearby.getFirst();
        require(launchRocket.tier() == 1 && !launchRocket.hasEnoughFuel(), "expected an empty tier-one rocket");
        var tank = launchRocket.getCapability(Capabilities.FluidHandler.ENTITY, Direction.UP);
        require(tank != null, "rocket did not expose a fluid capability");
        var fuel = new FluidStack(BuiltInRegistries.FLUID.get(ResourceLocation.parse("ad_astra:fuel")),
            AdAstraConfig.launchFuelCost);
        require(tank.fill(fuel, IFluidHandler.FluidAction.EXECUTE) == fuel.getAmount() && launchRocket.hasEnoughFuel(),
            "rocket did not accept standard fuel");
        testPassenger = EntityType.ARMOR_STAND.create(level);
        require(testPassenger != null, "could not create the launch test passenger");
        testPassenger.setPos(astronaut.position());
        require(level.addFreshEntity(testPassenger) && testPassenger.startRiding(launchRocket, true),
            "could not board the fueled rocket");
        testPassenger.setJumping(true);
    }

    private Recipe<?> recipe(String name) {
        return level.getRecipeManager().byKey(ResourceLocation.parse(PATH + name))
            .orElseThrow(() -> new IllegalStateException("missing space recipe " + name)).value();
    }

    private void stop() {
        if (testPassenger != null) testPassenger.discard();
        level.setChunkForced(0, 0, false);
        level = null;
    }

    private static ItemStack stack(String id) {
        return new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse(id)));
    }

    private static Block block(String id) {
        return BuiltInRegistries.BLOCK.get(ResourceLocation.parse(id));
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalStateException(message);
    }

    private static final class StationRun {
        private final ECOIntegratedWorkingStationBlockEntity station;
        private final List<String> outputs;
        private IntegratedWorkingStationRecipe running;
        private int index;
        private boolean working;

        private StationRun(ECOIntegratedWorkingStationBlockEntity station, List<String> outputs) {
            this.station = station;
            this.outputs = outputs;
        }

        private boolean finished() {
            return index == outputs.size();
        }
    }
}
