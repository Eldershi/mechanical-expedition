package expedition.space;

import com.google.gson.JsonParser;
import com.mojang.authlib.GameProfile;
import earth.terrarium.adastra.api.events.AdAstraEvents;
import earth.terrarium.adastra.api.systems.OxygenApi;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.EquipmentSlot;
import net.neoforged.neoforge.common.util.FakePlayerFactory;
import net.neoforged.neoforge.event.entity.player.PlayerInteractEvent;
import net.ty.createcraftedbeginning.api.canister.CanisterCapabilities;
import net.ty.createcraftedbeginning.api.gas.GasAction;
import net.ty.createcraftedbeginning.api.gas.GasStack;
import net.ty.createcraftedbeginning.content.airtights.gascanister.container.CanisterContainerConsumers;
import net.ty.createcraftedbeginning.content.airtights.gascanisterpack.GasCanisterPackContainerContents;
import net.ty.createcraftedbeginning.registry.gas.CCBGases;
import com.lowdragmc.mbd2.api.machine.IMultiController;
import com.lowdragmc.mbd2.common.machine.MBDMultiblockMachine;
import com.lowdragmc.mbd2.common.trait.forgeenergy.ForgeEnergyCapabilityTrait;
import expedition.space.FreightData.Key;
import io.netty.channel.embedded.EmbeddedChannel;
import expedition.space.FreightData.Role;
import expedition.space.FreightData.Station;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.BlockHitResult;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.capabilities.Capabilities;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;

@Mod("expedition_space_acceptance")
public final class SpaceAcceptance {
    private static final UUID TEAM = UUID.fromString("71ea5745-f541-4ad9-9034-3ef33726b34e");
    private final List<Station> stationFixtures = new ArrayList<>();
    private int phase;
    private long started;
    private Station earth;
    private Station moon;
    private Station gate;

    public SpaceAcceptance() {
        NeoForge.EVENT_BUS.addListener(this::commands);
        NeoForge.EVENT_BUS.addListener(this::tick);
    }

    private void commands(RegisterCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("expeditionspaceproof").requires(source -> source.hasPermission(4))
            .then(Commands.literal("run").executes(context -> {
                start(context.getSource().getServer());
                return 1;
            })).then(Commands.literal("reload").executes(context -> {
                FreightData data = FreightData.get(context.getSource().getServer());
                int[] delivered = data.deliveries.get(TEAM);
                require(delivered != null && delivered[0] == 2 && delivered[1] == 1, "delivery counts across restart");
                require(data.shipments.isEmpty(), "completed shipment returned after restart");
                Station moon = data.stations.get(new Key(TEAM, SpaceLogistics.MOON_ORBIT, Role.LAUNCH));
                require(moon != null && moon.getItem(FreightData.OUTPUT).is(Items.GOLD_INGOT), "persisted received cargo");
                context.getSource().sendSuccess(() -> Component.literal("EXPEDITION_SPACE_RELOAD_PASS"), false);
                return 1;
            })).then(Commands.literal("air").executes(context -> {
                proveAir(context.getSource().getServer());
                return 1;
            })).then(Commands.literal("gate").executes(context -> {
                MinecraftServer server = context.getSource().getServer();
                gate = place(server.getLevel(SpaceLogistics.MOON), Role.GATE, new BlockPos(5, 150, 6), false);
                ServerLevel level = server.getLevel(SpaceLogistics.MOON);
                for (BlockPos pos : BlockPos.betweenClosed(gate.pos.offset(-3,-1,-3), gate.pos.offset(3,-1,3))) {
                    level.setBlock(pos, Blocks.SMOOTH_STONE.defaultBlockState(), Block.UPDATE_ALL);
                }
                started = server.overworld().getGameTime();
                phase = 6;
                return 1;
            })));
    }

    private void start(MinecraftServer server) {
        stationFixtures.clear();
        var data = FreightData.get(server);
        require(data.shipments.isEmpty() && !data.stable(TEAM), "run against a clean proof world");
        int x = 0;
        for (Role role : Role.values()) {
            if (role == Role.BEACON) continue;
            place(server.overworld(), role, new BlockPos(x, 150, 8), false);
            x += 12;
        }
        earth = place(server.getLevel(SpaceLogistics.EARTH_ORBIT), Role.LAUNCH, new BlockPos(2, 150, 5), true);
        moon = place(server.getLevel(SpaceLogistics.MOON_ORBIT), Role.LAUNCH, new BlockPos(2, 150, 5), true);
        for (ServerLevel orbit : List.of(server.getLevel(SpaceLogistics.EARTH_ORBIT), server.getLevel(SpaceLogistics.MOON_ORBIT))) {
            place(orbit, Role.SATELLITE, new BlockPos(2, 150, 11), true);
        }
        for (ServerLevel ground : List.of(server.overworld(), server.getLevel(SpaceLogistics.MOON))) {
            place(ground, Role.BEACON, new BlockPos(2, 150, 2), true);
        }
        started = server.overworld().getGameTime();
        phase = 1;
    }

    private Station place(ServerLevel level, Role role, BlockPos origin, boolean register) {
        try {
            BlockPos controller = origin;
            if (role == Role.BEACON) {
                level.setChunkForced(origin.getX() >> 4, origin.getZ() >> 4, true);
                level.setBlock(origin, block("expedition_space:surface_beacon").defaultBlockState(), Block.UPDATE_ALL);
            } else {
                var cells = JsonParser.parseString(Files.readString(Path.of("space-fixtures.json")))
                    .getAsJsonObject().getAsJsonArray(role.path);
                for (var entry : cells) {
                    var cell = entry.getAsJsonArray();
                    BlockPos pos = origin.offset(cell.get(0).getAsInt(), cell.get(1).getAsInt(), cell.get(2).getAsInt());
                    level.setChunkForced(pos.getX() >> 4, pos.getZ() >> 4, true);
                    String id = cell.get(3).getAsString();
                    level.setBlock(pos, block(id).defaultBlockState(), Block.UPDATE_ALL);
                    if (id.equals("expedition_space:" + role.path)) controller = pos;
                }
                var machine = controller(level, controller);
                machine.setFrontFacing(Direction.NORTH);
                machine.notifyPatternDirty();
            }
            var key = new Key(TEAM, level.dimension(), role);
            var data = FreightData.get(level.getServer());
            var station = data.new Station(key, controller);
            stationFixtures.add(station);
            if (register) {
                station.registered = true;
                data.stations.put(key, station);
                data.setDirty();
                level.invalidateCapabilities(controller);
            }
            return station;
        } catch (Exception error) {
            throw new IllegalStateException("placing " + role, error);
        }
    }

    private void tick(ServerTickEvent.Post event) {
        if (phase == 0) return;
        try {
            MinecraftServer server = event.getServer();
            FreightData data = FreightData.get(server);
            long elapsed = server.overworld().getGameTime() - started;
            require(elapsed < 1400, "phase " + phase + " timed out, " + data.shipments.size() + " pending");
            int[] count = data.deliveries.getOrDefault(TEAM, new int[2]);
            switch (phase) {
                case 1 -> {
                    if (elapsed < 30) return;
                    for (Station station : stationFixtures) {
                        require(SpaceLogistics.operational(server, station), "failed to form " + station.key + " at " + station.pos);
                    }
                    for (Role role : Role.values()) {
                        require(server.getRecipeManager().byKey(SpaceLogistics.id("station/" + role.path)).isPresent(),
                            "missing recipe " + role.path);
                    }
                    for (int slot = FreightData.OUTPUT; slot < FreightData.OUTPUT + FreightData.BATCH; slot++) {
                        moon.setItem(slot, new ItemStack(Items.COBBLESTONE, 64));
                    }
                    load(server, earth, new ItemStack(Items.IRON_INGOT, 3));
                    phase = 2;
                    System.out.println("EXPEDITION_SPACE_STRUCTURES_PASS");
                }
                case 2 -> {
                    if (elapsed < 370) return;
                    require(data.shipments.size() == 1 && count[0] == 0, "full destination must hold exactly one shipment");
                    for (int slot = FreightData.OUTPUT; slot < FreightData.OUTPUT + FreightData.BATCH; slot++) {
                        moon.setItem(slot, ItemStack.EMPTY);
                    }
                    phase = 3;
                }
                case 3 -> {
                    if (count[0] == 0) return;
                    require(moon.getItem(FreightData.OUTPUT).getCount() == 3, "iron delivery count");
                    moon.setItem(FreightData.OUTPUT, ItemStack.EMPTY);
                    load(server, moon, new ItemStack(Items.COPPER_INGOT, 7));
                    phase = 4;
                }
                case 4 -> {
                    if (count[1] == 0) return;
                    require(earth.getItem(FreightData.OUTPUT).getCount() == 7 && !data.stable(TEAM), "return cargo or premature stability");
                    load(server, earth, new ItemStack(Items.GOLD_INGOT, 2));
                    phase = 5;
                }
                case 5 -> {
                    if (!data.stable(TEAM)) return;
                    require(count[0] == 2 && count[1] == 1 && data.shipments.isEmpty(), "duplicate shipment or wrong counts");
                    require(moon.getItem(FreightData.OUTPUT).is(Items.GOLD_INGOT), "third shipment");
                    phase = 0;
                    System.out.println("EXPEDITION_SPACE_FREIGHT_PASS");
                }
                case 6 -> {
                    if (elapsed < 40) return;
                    phase = 0;
                    proveGate(server, data);
                }
                default -> throw new IllegalStateException("unknown proof phase");
            }
        } catch (Exception error) {
            phase = 0;
            error.printStackTrace();
            System.out.println("EXPEDITION_SPACE_PROOF_FAILED");
        }
    }

    private void proveGate(MinecraftServer server, FreightData data) {
        require(data.stable(TEAM) && SpaceLogistics.operational(server, gate), "gate fixture or persisted freight");
        var moon = server.getLevel(SpaceLogistics.MOON);
        var actor = FakePlayerFactory.get(moon, new GameProfile(TEAM, "SpaceGateTest"));
        var channel = new EmbeddedChannel(actor.connection.getConnection());
        try {
            exerciseGate(data, moon, actor);
        } finally {
            channel.finishAndReleaseAll();
        }
    }

    private void exerciseGate(FreightData data, ServerLevel moon, net.minecraft.server.level.ServerPlayer actor) {
        data.milestones.remove(TEAM);
        data.returnGates.remove(TEAM);
        data.setDirty();
        actor.setPos(gate.pos.getX() + .5, gate.pos.getY(), gate.pos.getZ() - 1.5);
        var energy = controller(moon, gate.pos).getTraitByName(ForgeEnergyCapabilityTrait.class, "forge_energy_storage");
        for (int i = 0; i < 5; i++) energy.getStorage().receiveEnergy(4_000, false);
        var hit = new BlockHitResult(gate.pos.getCenter(), Direction.NORTH, gate.pos, false);
        require(!SpaceLogistics.mayUseOtherPad(actor), "first native pad visit should be locked");
        NeoForge.EVENT_BUS.post(new PlayerInteractEvent.RightClickBlock(actor, InteractionHand.MAIN_HAND, gate.pos, hit));
        require(!data.returnGates.containsKey(TEAM) && actor.level().dimension().equals(SpaceLogistics.MOON), "premature gate use");
        data.mark(TEAM, FreightData.DUNGEON);
        NeoForge.EVENT_BUS.post(new PlayerInteractEvent.RightClickBlock(actor, InteractionHand.MAIN_HAND, gate.pos, hit));
        require(actor.level().dimension().equals(SpaceLogistics.OTHER), "lunar gate did not reach The Other");
        require(SpaceLogistics.mayUseOtherPad(actor), "native pad did not unlock on arrival");
        actor.setItemSlot(EquipmentSlot.MAINHAND, item("expedition_space:lunar_signature"));
        NeoForge.EVENT_BUS.post(new PlayerInteractEvent.RightClickItem(actor, InteractionHand.MAIN_HAND));
        require(actor.level().dimension().equals(SpaceLogistics.MOON), "signature did not return to the moon");
        System.out.println("EXPEDITION_SPACE_GATE_PASS");
    }

    private static void proveAir(MinecraftServer server) {
        var orbit = server.getLevel(SpaceLogistics.EARTH_ORBIT);
        var player = FakePlayerFactory.get(orbit, new GameProfile(TEAM, "SpaceAirTest"));
        player.setPos(6.5, 151, 6.5);
        String ccb = "createcraftedbeginning:";
        ItemStack helmet = item(ccb + "airtight_helmet");
        ItemStack pack = item(ccb + "gas_canister_pack");
        player.setItemSlot(EquipmentSlot.MAINHAND, item("expedition_space:life_support_module"));
        player.setItemSlot(EquipmentSlot.OFFHAND, pack);
        NeoForge.EVENT_BUS.post(new PlayerInteractEvent.RightClickItem(player, InteractionHand.MAIN_HAND));
        player.setItemSlot(EquipmentSlot.OFFHAND, helmet);
        NeoForge.EVENT_BUS.post(new PlayerInteractEvent.RightClickItem(player, InteractionHand.MAIN_HAND));
        player.setItemSlot(EquipmentSlot.HEAD, helmet);
        player.setItemSlot(EquipmentSlot.CHEST, item(ccb + "airtight_chestplate"));
        player.setItemSlot(EquipmentSlot.LEGS, item(ccb + "airtight_leggings"));
        player.setItemSlot(EquipmentSlot.FEET, item(ccb + "airtight_boots"));
        player.setItemSlot(EquipmentSlot.OFFHAND, ItemStack.EMPTY);

        var container = (GasCanisterPackContainerContents) pack.getCapability(CanisterCapabilities.ITEM);
        require(container != null, "pack capability");
        try {
            var put = GasCanisterPackContainerContents.class.getDeclaredMethod("setCanister", int.class, ItemStack.class);
            put.setAccessible(true);
            put.invoke(container, 0, item(ccb + "gas_canister"));
        } catch (ReflectiveOperationException error) {
            throw new IllegalStateException("probe could not prepare a native canister", error);
        }
        var gas = CCBGases.NATURAL_AIR.get();
        require(container.fill(0, new GasStack(gas, container.getTankMaxAmount(0)), GasAction.EXECUTE) > 0,
            "native gas fill");
        container.save();
        player.getInventory().setItem(20, pack);
        long before = amount(pack);
        require(before >= 500 && LifeSupport.reserve(pack, 0), "native capacity and reserved slot");
        require(CanisterContainerConsumers.findAffordableFuel(player, gas, ignored -> 1).isEmpty(), "combat tried to use reserve");
        require(AdAstraEvents.EntityOxygenEvent.fire(player, false), "vacuum oxygen");
        long remaining = amount(pack);
        require(remaining < before, "vacuum reserve did not drain");
        require(!AdAstraEvents.ColdTemperatureTickEvent.fire(orbit, player) && amount(pack) == remaining,
            "cold and oxygen used the same paid window");
        require(AdAstraEvents.HotTemperatureTickEvent.fire(orbit, player), "heat protection without lining");
        player.setItemSlot(EquipmentSlot.FEET, ItemStack.EMPTY);
        require(!AdAstraEvents.EntityOxygenEvent.fire(player, false), "incomplete armor");
        player.setItemSlot(EquipmentSlot.FEET, item(ccb + "airtight_boots"));
        OxygenApi.API.setOxygen(orbit, player.blockPosition(), true);
        require(AdAstraEvents.EntityOxygenEvent.fire(player, true) && amount(pack) == remaining, "airtight room should not drain reserve");
        OxygenApi.API.removeOxygen(orbit, player.blockPosition());
        System.out.println("EXPEDITION_SPACE_AIR_PASS");
    }

    private static long amount(ItemStack pack) {
        return pack.getCapability(CanisterCapabilities.ITEM).getGasInTank(0).getAmount();
    }

    private static ItemStack item(String id) {
        return new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse(id)));
    }

    private static Block block(String name) {
        Block block = BuiltInRegistries.BLOCK.get(ResourceLocation.parse(name));
        require(block != Blocks.AIR, "missing block " + name);
        return block;
    }

    private static MBDMultiblockMachine controller(ServerLevel level, BlockPos pos) {
        return (MBDMultiblockMachine) IMultiController.ofController(level, pos).orElseThrow();
    }

    private static void load(MinecraftServer server, Station station, ItemStack stack) {
        var level = server.getLevel(station.key.dimension());
        var machine = controller(level, station.pos);
        var power = machine.getTraitByName(ForgeEnergyCapabilityTrait.class, "forge_energy_storage");
        for (int i = 0; i < 10; i++) power.getStorage().receiveEnergy(4_000, false);
        var port = level.getCapability(Capabilities.ItemHandler.BLOCK, station.pos, Direction.UP);
        require(port != null && port.insertItem(0, stack, false).isEmpty(), "automation port");
        station.setItem(FreightData.CARRIER, new ItemStack(BuiltInRegistries.ITEM.get(SpaceLogistics.id("freight_module"))));
        station.setItem(FreightData.FUEL, new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse("ad_astra:fuel_bucket"))));
        station.automatic = true;
    }

    private static void require(boolean valid, String message) {
        if (!valid) throw new IllegalStateException(message);
    }
}
