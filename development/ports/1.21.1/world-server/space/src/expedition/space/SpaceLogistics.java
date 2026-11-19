package expedition.space;

import com.lowdragmc.mbd2.api.machine.IMultiController;
import com.lowdragmc.mbd2.common.machine.MBDMultiblockMachine;
import com.lowdragmc.mbd2.common.trait.forgeenergy.ForgeEnergyCapabilityTrait;
import dev.ftb.mods.ftbteams.api.FTBTeamsAPI;
import expedition.space.FreightData.Key;
import expedition.space.FreightData.Role;
import expedition.space.FreightData.Shipment;
import expedition.space.FreightData.Station;
import java.util.UUID;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.stats.Stats;
import net.minecraft.tags.TagKey;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.SimpleMenuProvider;
import net.minecraft.world.inventory.ChestMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.phys.AABB;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.capabilities.Capabilities;
import net.neoforged.neoforge.capabilities.RegisterCapabilitiesEvent;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;
import net.neoforged.neoforge.event.entity.player.PlayerInteractEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;

@Mod("expedition_space")
public final class SpaceLogistics {
    static final ResourceKey<Level> MOON = dimension("ad_astra:moon");
    static final ResourceKey<Level> EARTH_ORBIT = dimension("ad_astra:earth_orbit");
    static final ResourceKey<Level> MOON_ORBIT = dimension("ad_astra:moon_orbit");
    static final ResourceKey<Level> OTHER = dimension("allthemodium:the_other");
    private static final TagKey<Structure> MOON_DUNGEON = TagKey.create(Registries.STRUCTURE, id("moon_dungeon"));
    private static final ResourceKey<Structure> DUNGEON_STRUCTURE = ResourceKey.create(
        Registries.STRUCTURE, ResourceLocation.parse("ad_astra:moon_dungeon"));
    private static final ResourceLocation FUEL_BUCKET = ResourceLocation.parse("ad_astra:fuel_bucket");
    private static final int FLIGHT_TICKS = 240;

    public SpaceLogistics(IEventBus modBus) {
        modBus.addListener(this::capabilities);
        NeoForge.EVENT_BUS.addListener(this::clickBlock);
        NeoForge.EVENT_BUS.addListener(this::clickItem);
        NeoForge.EVENT_BUS.addListener(this::dimensionChanged);
        NeoForge.EVENT_BUS.addListener(this::login);
        NeoForge.EVENT_BUS.addListener(this::tick);
        NeoForge.EVENT_BUS.addListener(this::commands);
        LifeSupport.install();
    }

    private void capabilities(RegisterCapabilitiesEvent event) {
        for (Role role : Role.values()) {
            if (!canSend(role) && role != Role.BEACON) continue;
            var block = BuiltInRegistries.BLOCK.get(id(role.path));
            if (block == net.minecraft.world.level.block.Blocks.AIR) continue;
            event.registerBlock(Capabilities.ItemHandler.BLOCK, (level, pos, state, entity, side) -> {
                if (!(level instanceof ServerLevel serverLevel) || side == null) return null;
                for (Station station : FreightData.get(serverLevel.getServer()).stations.values()) {
                    if (station.key.dimension().equals(level.dimension()) && station.key.role() == role
                        && station.pos.equals(pos)) return new CargoPort(serverLevel, station, side);
                }
                return null;
            }, block);
        }
    }

    static boolean correctSupply(int slot, ItemStack stack) {
        if (slot == FreightData.CARRIER) {
            return itemIs(stack, id("carrier_rocket")) || itemIs(stack, id("freight_module"));
        }
        return itemIs(stack, FUEL_BUCKET);
    }

    static ResourceLocation id(String path) { return ResourceLocation.fromNamespaceAndPath("expedition_space", path); }

    private static ResourceKey<Level> dimension(String address) {
        return ResourceKey.create(Registries.DIMENSION, ResourceLocation.parse(address));
    }

    static UUID team(ServerPlayer player) {
        var api = FTBTeamsAPI.api();
        if (api.isManagerLoaded()) {
            return api.getManager().getTeamForPlayer(player).map(value -> value.getId()).orElse(player.getUUID());
        }
        return player.getUUID();
    }

    static boolean operational(MinecraftServer server, Station station) {
        ServerLevel level = server.getLevel(station.key.dimension());
        return level != null && level.hasChunkAt(station.pos) && role(level, station.pos) == station.key.role()
            && (station.key.role() == Role.BEACON || machine(level, station.pos) != null);
    }

    private static Role role(Level level, BlockPos pos) {
        return Role.of(BuiltInRegistries.BLOCK.getKey(level.getBlockState(pos).getBlock()));
    }

    private static MBDMultiblockMachine machine(ServerLevel level, BlockPos pos) {
        return IMultiController.ofController(level, pos)
            .filter(controller -> controller instanceof MBDMultiblockMachine mbd && mbd.isFormedValid())
            .map(controller -> (MBDMultiblockMachine) controller).orElse(null);
    }

    private static boolean allowed(Role role, ResourceKey<Level> dim) {
        return switch (role) {
            case SATELLITE, LAUNCH, DROP -> orbit(dim);
            case LIFT -> surface(dim) || orbit(dim);
            case GATE -> dim.equals(MOON);
            case BEACON -> surface(dim);
        };
    }

    private static boolean orbit(ResourceKey<Level> dim) { return dim.equals(EARTH_ORBIT) || dim.equals(MOON_ORBIT); }
    private static boolean surface(ResourceKey<Level> dim) { return dim.equals(Level.OVERWORLD) || dim.equals(MOON); }
    private static ResourceKey<Level> ground(ResourceKey<Level> dim) { return dim.equals(EARTH_ORBIT) ? Level.OVERWORLD : MOON; }
    private static ResourceKey<Level> sky(ResourceKey<Level> dim) { return dim.equals(Level.OVERWORLD) ? EARTH_ORBIT : MOON_ORBIT; }

    private void clickBlock(PlayerInteractEvent.RightClickBlock event) {
        if (event.getHand() != InteractionHand.MAIN_HAND || !(event.getEntity() instanceof ServerPlayer player)) return;
        ServerLevel level = player.serverLevel();
        BlockPos pos = event.getPos();
        Role role = role(level, pos);
        if (role == null || (!event.getItemStack().isEmpty() && !itemIs(event.getItemStack(), id("freight_remote")))) return;
        if (role != Role.BEACON && machine(level, pos) == null) return;
        event.setCanceled(true);
        event.setCancellationResult(InteractionResult.SUCCESS);
        if (!allowed(role, level.dimension())) {
            tell(player, "wrong_dimension");
            return;
        }

        FreightData data = FreightData.get(player.server);
        UUID team = team(player);
        Key key = new Key(team, level.dimension(), role);
        for (Station endpoint : data.stations.values()) {
            if (endpoint.key.dimension().equals(level.dimension()) && endpoint.pos.equals(pos)
                && endpoint.key.role() == role && !endpoint.key.team().equals(team)) {
                tell(player, "owned");
                return;
            }
        }
        Station station = data.stations.get(key);
        if (station == null || !station.pos.equals(pos)) {
            if (station != null && (!level.hasChunkAt(station.pos) || role(level, station.pos) == role)) {
                tell(player, "already_bound");
                return;
            }
            if (station == null) {
                station = data.new Station(key, pos);
                data.stations.put(key, station);
            } else {
                station.pos = pos.immutable();
                station.registered = false;
            }
            data.setDirty();
            level.invalidateCapabilities(pos);
            tell(player, "bound");
        }

        boolean remote = itemIs(event.getItemStack(), id("freight_remote"));
        if (remote && player.isShiftKeyDown() && canSend(role)) {
            station.automatic = !station.automatic;
            data.setDirty();
            tell(player, station.automatic ? "automatic_on" : "automatic_off");
            return;
        }
        switch (role) {
            case SATELLITE -> satellite(player, data, station);
            case GATE -> enterOther(player, data, station);
            case LIFT -> {
                if (player.isShiftKeyDown() && !remote) ride(player, data, station);
                else if (remote) send(player.server, data, station, player);
                else open(player, station);
            }
            case LAUNCH, DROP -> {
                if (remote || player.isShiftKeyDown()) send(player.server, data, station, player);
                else open(player, station);
            }
            case BEACON -> open(player, station);
        }
    }

    private static boolean canSend(Role role) { return role == Role.LAUNCH || role == Role.LIFT || role == Role.DROP; }

    private static void open(ServerPlayer player, Station station) {
        player.openMenu(new SimpleMenuProvider((id, inv, who) -> ChestMenu.threeRows(id, inv, station),
            Component.translatable("block.expedition_space." + station.key.role().path)));
        if (canSend(station.key.role())) tell(player, station.key.role() == Role.LAUNCH ? "launch_slots" : "cargo_slots");
    }

    private static void satellite(ServerPlayer player, FreightData data, Station station) {
        ResourceKey<Level> dim = station.key.dimension();
        Station beacon = data.stations.get(new Key(station.key.team(), ground(dim), Role.BEACON));
        if (beacon == null) {
            tell(player, "no_beacon");
            return;
        }
        if (!power(player.server, station, 8_000)) {
            tell(player, "power");
            return;
        }
        beacon.registered = true;
        station.registered = true;
        data.setDirty();
        award(player, "satellite_registered");
        tell(player, "registered", beacon.pos.toShortString());
        if (!dim.equals(MOON_ORBIT)) return;
        BlockPos found = data.dungeons.get(station.key.team());
        ServerLevel moon = player.server.getLevel(MOON);
        if (found == null && moon != null) {
            found = moon.findNearestMapStructure(MOON_DUNGEON,
                new BlockPos(beacon.pos.getX(), 64, beacon.pos.getZ()), 64, false);
            if (found != null) {
                data.dungeons.put(station.key.team(), found.immutable());
                data.setDirty();
            }
        }
        if (found == null) tell(player, "dungeon_missing");
        else tell(player, "dungeon", found.toShortString());
    }

    private static Key target(Station station) {
        Key key = station.key;
        ResourceKey<Level> dim = key.dimension();
        return switch (key.role()) {
            case LAUNCH -> new Key(key.team(), dim.equals(EARTH_ORBIT) ? MOON_ORBIT : EARTH_ORBIT, Role.LAUNCH);
            case LIFT -> new Key(key.team(), orbit(dim) ? ground(dim) : sky(dim), Role.LIFT);
            case DROP -> new Key(key.team(), ground(dim), Role.BEACON);
            default -> throw new IllegalArgumentException("Station cannot dispatch freight");
        };
    }

    private static boolean hasRelay(FreightData data, Key key) {
        ResourceKey<Level> dim = key.dimension();
        Station relay = data.stations.get(new Key(key.team(), orbit(dim) ? dim : sky(dim), Role.SATELLITE));
        Station beacon = data.stations.get(new Key(key.team(), orbit(dim) ? ground(dim) : dim, Role.BEACON));
        return relay != null && relay.registered && beacon != null && beacon.registered;
    }

    private static void send(MinecraftServer server, FreightData data, Station station, ServerPlayer player) {
        Key source = station.key;
        Key target = target(station);
        long now = server.overworld().getGameTime();
        var cargo = station.input();
        if (now < station.nextLaunch || cargo.isEmpty()) {
            if (player != null) tell(player, "no_cargo");
            return;
        }
        if (!data.stations.containsKey(target) || !hasRelay(data, source) || !hasRelay(data, target)) {
            if (player != null) tell(player, "need_endpoints");
            return;
        }

        Role role = source.role();
        if (data.shipments.values().stream().anyMatch(shipment -> shipment.source().equals(source))) {
            if (player != null) tell(player, "active_shipment");
            return;
        }
        if (role == Role.LAUNCH && (!correctSupply(FreightData.CARRIER, station.getItem(FreightData.CARRIER))
                || !correctSupply(FreightData.FUEL, station.getItem(FreightData.FUEL)))) {
            if (player != null) tell(player, "fuel");
            return;
        }
        int cost = switch (role) {
            case LAUNCH -> 32_000;
            case DROP -> 12_000;
            default -> 4_000;
        };
        if (!power(server, station, cost)) {
            if (player != null) tell(player, "power");
            return;
        }
        if (role == Role.LAUNCH) station.setItem(FreightData.FUEL, new ItemStack(Items.BUCKET));
        UUID id = UUID.randomUUID();
        data.shipments.put(id, new Shipment(id, source, target, now + (role == Role.LAUNCH ? FLIGHT_TICKS : 60), cargo));
        for (int slot = 0; slot < FreightData.BATCH; slot++) station.setItem(slot, ItemStack.EMPTY);
        station.nextLaunch = now + 60;
        data.setDirty();
        if (player != null) tell(player, "dispatched");
    }

    private void tick(ServerTickEvent.Post event) {
        MinecraftServer server = event.getServer();
        long now = server.overworld().getGameTime();
        if (now % 20 != 0) return;
        FreightData data = FreightData.get(server);
        var pending = data.shipments.values().iterator();
        while (pending.hasNext()) {
            Shipment shipment = pending.next();
            Station destination = data.stations.get(shipment.target());
            if (now < shipment.due() || destination == null || !operational(server, destination)) continue;
            if (shipment.source().role() == Role.DROP && !clearDrop(server.getLevel(destination.key.dimension()), destination.pos)) continue;
            if (!destination.receive(shipment.cargo())) continue;
            pending.remove();
            data.setDirty();
            if (shipment.source().role() == Role.LAUNCH) {
                data.delivered(destination.key.team(), destination.key.dimension().equals(MOON_ORBIT));
                if (data.stable(destination.key.team())) {
                    for (ServerPlayer player : server.getPlayerList().getPlayers()) {
                        if (team(player).equals(destination.key.team())) award(player, "stable_freight");
                    }
                }
            }
        }
        for (Station station : data.stations.values()) {
            if (station.automatic && canSend(station.key.role()) && operational(server, station)) send(server, data, station, null);
        }
        for (ServerPlayer player : server.getPlayerList().getPlayers()) investigate(player, data);
    }

    private static boolean clearDrop(ServerLevel level, BlockPos pos) {
        int top = level.getHeight(Heightmap.Types.MOTION_BLOCKING, pos.getX(), pos.getZ());
        return top <= pos.getY() + 1;
    }

    private static void ride(ServerPlayer player, FreightData data, Station source) {
        Station destination = data.stations.get(target(source));
        ResourceKey<Level> dim = destination == null ? source.key.dimension() : destination.key.dimension();
        int visit = dim.equals(EARTH_ORBIT) ? FreightData.VISITED_EARTH_ORBIT
            : dim.equals(MOON_ORBIT) ? FreightData.VISITED_MOON_ORBIT
            : dim.equals(MOON) ? FreightData.VISITED_MOON : 0;
        if (destination == null || (visit != 0 && !data.flag(player.getUUID(), visit))
                || !hasRelay(data, source.key)) {
            tell(player, "need_visit");
            return;
        }
        ServerLevel world = player.server.getLevel(dim);
        if (world == null) return;
        world.getChunkAt(destination.pos);
        if (!operational(player.server, destination)) {
            tell(player, "need_visit");
            return;
        }
        BlockPos landing = nearbyLanding(world, destination.pos);
        if (landing == null) {
            tell(player, "blocked");
        } else if (!power(player.server, source, 4_000)) {
            tell(player, "power");
        } else {
            teleport(player, world, landing);
        }
    }

    private static void investigate(ServerPlayer player, FreightData data) {
        if (!player.level().dimension().equals(MOON) || player.isSpectator() || data.flag(player.getUUID(), FreightData.DUNGEON)) return;
        BlockPos coordinates = data.dungeons.get(team(player));
        if (coordinates == null || player.blockPosition().distSqr(coordinates) > 128L * 128L) return;
        ServerLevel level = player.serverLevel();
        var structure = level.registryAccess().registryOrThrow(Registries.STRUCTURE)
            .getHolderOrThrow(DUNGEON_STRUCTURE).value();
        var start = level.structureManager().getStructureWithPieceAt(player.blockPosition(), structure);
        if (!start.isValid() || !start.getBoundingBox().isInside(coordinates.atY(player.getBlockY()))) return;
        data.mark(player.getUUID(), FreightData.DUNGEON);
        player.getInventory().placeItemBackInInventory(new ItemStack(BuiltInRegistries.ITEM.get(id("lunar_signature"))));
        award(player, "lunar_survey");
        tell(player, "surveyed");
    }

    private static void enterOther(ServerPlayer player, FreightData data, Station gate) {
        UUID uuid = player.getUUID();
        if (!data.stable(gate.key.team()) || !data.flag(uuid, FreightData.DUNGEON)) {
            tell(player, "gate_locked");
            return;
        }
        ServerLevel other = player.server.getLevel(OTHER);
        if (other == null) {
            tell(player, "blocked");
            return;
        }
        BlockPos landing = surfaceLanding(other, gate.pos.getX(), gate.pos.getZ());
        if (landing == null) {
            tell(player, "blocked");
            return;
        }
        if (!power(player.server, gate, 16_000)) {
            tell(player, "power");
            return;
        }
        data.returnGates.put(uuid, gate.pos);
        data.setDirty();
        teleport(player, other, landing);
    }

    private void clickItem(PlayerInteractEvent.RightClickItem event) {
        if (!(event.getEntity() instanceof ServerPlayer player) || !player.level().dimension().equals(OTHER)
                || !itemIs(event.getItemStack(), id("lunar_signature"))) return;
        if (returnToMoon(player)) {
            event.setCancellationResult(InteractionResult.SUCCESS);
            event.setCanceled(true);
        }
    }

    private static boolean returnToMoon(ServerPlayer player) {
        if (!player.level().dimension().equals(OTHER)) return false;
        BlockPos gate = FreightData.get(player.server).returnGates.get(player.getUUID());
        ServerLevel moon = player.server.getLevel(MOON);
        if (gate == null || moon == null) return false;
        moon.getChunkAt(gate);
        BlockPos landing = nearbyLanding(moon, gate);
        if (landing == null) {
            tell(player, "return_pad");
            return false;
        }
        teleport(player, moon, landing);
        return true;
    }

    private static BlockPos nearbyLanding(ServerLevel level, BlockPos center) {
        for (BlockPos pos : BlockPos.withinManhattan(center, 4, 2, 4)) {
            if (level.hasChunkAt(pos) && safe(level, pos)) return pos.immutable();
        }
        return null;
    }

    private static BlockPos surfaceLanding(ServerLevel level, int x, int z) {
        for (BlockPos position : BlockPos.withinManhattan(new BlockPos(x, 0, z), 8, 0, 8)) {
            BlockPos top = level.getHeightmapPos(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, position);
            if (safe(level, top)) return top;
        }
        return null;
    }

    private static boolean safe(ServerLevel level, BlockPos pos) {
        return level.getWorldBorder().isWithinBounds(pos) && level.getBlockState(pos.below()).isFaceSturdy(
            level, pos.below(), net.minecraft.core.Direction.UP)
            && level.getFluidState(pos).isEmpty() && level.getFluidState(pos.above()).isEmpty()
            && level.getBlockState(pos).isAir() && level.getBlockState(pos.above()).isAir()
            && level.noCollision(new AABB(pos.getX() + .2, pos.getY(), pos.getZ() + .2,
                pos.getX() + .8, pos.getY() + 1.9, pos.getZ() + .8));
    }

    private static void teleport(ServerPlayer player, ServerLevel level, BlockPos pos) {
        player.teleportTo(level, pos.getX() + .5, pos.getY(), pos.getZ() + .5, player.getYRot(), player.getXRot());
        player.resetFallDistance();
    }

    private void dimensionChanged(PlayerEvent.PlayerChangedDimensionEvent event) {
        if (!(event.getEntity() instanceof ServerPlayer player)) return;
        recordLocation(player, event.getTo());
    }

    private void login(PlayerEvent.PlayerLoggedInEvent event) {
        if (!(event.getEntity() instanceof ServerPlayer player)) return;
        recordLocation(player, player.level().dimension());
        if (FreightData.get(player.server).stable(team(player))) award(player, "stable_freight");
    }

    private static void recordLocation(ServerPlayer player, ResourceKey<Level> dim) {
        FreightData data = FreightData.get(player.server);
        if (dim.equals(MOON)) data.mark(player.getUUID(), FreightData.VISITED_MOON);
        if (dim.equals(EARTH_ORBIT)) data.mark(player.getUUID(), FreightData.VISITED_EARTH_ORBIT);
        if (dim.equals(MOON_ORBIT)) data.mark(player.getUUID(), FreightData.VISITED_MOON_ORBIT);
        if (dim.equals(OTHER)) {
            data.mark(player.getUUID(), FreightData.VISITED_OTHER);
            award(player, "other_arrival");
        }
    }

    public static boolean isOther(ResourceKey<Level> level) { return OTHER.equals(level); }

    public static boolean mayUseOtherPad(ServerPlayer player) {
        return player.level().dimension().equals(OTHER) || FreightData.get(player.server).flag(player.getUUID(), FreightData.VISITED_OTHER)
           ;
    }

    private void commands(RegisterCommandsEvent event) {
        var dispatcher = event.getDispatcher();
        dispatcher.register(Commands.literal("spacefreight")
            .then(Commands.literal("return").executes(context -> returnToMoon(context.getSource().getPlayerOrException()) ? 1 : 0))
            .then(Commands.literal("recover").executes(context -> {
            ServerPlayer player = context.getSource().getPlayerOrException();
            FreightData data = FreightData.get(player.server);
            UUID team = team(player);
            var iterator = data.shipments.values().iterator();
            while (iterator.hasNext()) {
                Shipment shipment = iterator.next();
                if (!shipment.source().team().equals(team)) continue;
                Station source = data.stations.get(shipment.source());
                if (source != null && source.receive(shipment.cargo())) {
                    iterator.remove();
                    data.setDirty();
                    tell(player, "recovered", source.key.dimension().location().toString(), source.pos.toShortString());
                }
            }
            return 1;
        })));
    }

    private static boolean power(MinecraftServer server, Station station, int amount) {
        ServerLevel level = server.getLevel(station.key.dimension());
        if (level == null) return false;
        var machine = machine(level, station.pos);
        if (machine == null) return false;
        var trait = machine.getTraitByName(ForgeEnergyCapabilityTrait.class, "forge_energy_storage");
        if (trait == null) return false;
        var storage = trait.getStorage();
        if (storage.extractEnergy(amount, true) < amount) return false;
        storage.extractEnergy(amount, false);
        return true;
    }

    private static boolean itemIs(ItemStack stack, ResourceLocation id) {
        return !stack.isEmpty() && BuiltInRegistries.ITEM.getKey(stack.getItem()).equals(id);
    }

    static void tell(ServerPlayer player, String key, Object... args) {
        player.displayClientMessage(Component.translatable("expedition_space." + key, args), false);
    }

    static void award(ServerPlayer player, String path) {
        var advancement = player.server.getAdvancements().get(id(path));
        if (advancement != null) player.getAdvancements().award(advancement, "expedition");
    }
}
