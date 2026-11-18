package expedition.space.travel;

import com.mojang.authlib.GameProfile;
import earth.terrarium.adastra.api.planets.Planet;
import earth.terrarium.adastra.api.planets.PlanetApi;
import earth.terrarium.adastra.common.config.AdAstraConfig;
import earth.terrarium.adastra.common.entities.vehicles.Lander;
import earth.terrarium.adastra.common.entities.vehicles.Rocket;
import earth.terrarium.adastra.common.items.vehicles.RocketItem;
import earth.terrarium.adastra.common.menus.PlanetsMenu;
import earth.terrarium.adastra.common.network.packets.ServerboundLandPacket;
import earth.terrarium.adastra.common.utils.ModUtils;
import io.netty.channel.embedded.EmbeddedChannel;
import java.util.UUID;
import net.minecraft.commands.Commands;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.Connection;
import net.minecraft.network.PacketSendListener;
import net.minecraft.network.protocol.Packet;
import net.minecraft.network.protocol.PacketFlow;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ClientInformation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.network.CommonListenerCookie;
import net.minecraft.server.network.ServerGamePacketListenerImpl;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.phys.AABB;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;

@Mod("expedition_space_round_trip_probe")
public final class SpaceRoundTripProbe {
    private static final int EARTH_X = 8;
    private static final int LANDING_Z = 8;
    private ServerLevel earth;
    private ServerLevel moon;
    private ServerPlayer pilot;
    private EmbeddedChannel channel;
    private Rocket rocket;
    private Lander lander;
    private int ticks;
    private boolean returning;

    public SpaceRoundTripProbe() {
        NeoForge.EVENT_BUS.addListener(this::register);
        NeoForge.EVENT_BUS.addListener(this::tick);
    }

    private void register(RegisterCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("expeditionroundtripproof").requires(source -> source.hasPermission(4))
            .executes(context -> {
                var server = context.getSource().getServer();
                earth = server.overworld();
                moon = server.getLevel(Planet.MOON);
                return 1;
            }));
    }

    private void tick(ServerTickEvent.Post event) {
        if (earth == null) return;
        try {
            if (pilot == null) prepare();
            else if (lander != null) approachGround();
            else if (pilot.containerMenu instanceof PlanetsMenu menu) selectDestination(menu);
            require(++ticks < 3400, "round trip timed out in " + pilot.level().dimension().location()
                + " at y=" + pilot.getY());
        } catch (Exception error) {
            error.printStackTrace();
            System.out.println("EXPEDITION_SPACE_ROUND_TRIP_FAILED " + error);
            stop();
        }
    }

    private void prepare() {
        require(moon != null, "Moon level unavailable");
        for (var level : new ServerLevel[] {earth, moon}) {
            level.getChunk(0, 0);
            level.setChunkForced(0, 0, true);
        }
        var profile = new GameProfile(UUID.randomUUID(), "RoundTripProbe");
        pilot = new ServerPlayer(earth.getServer(), earth, profile, ClientInformation.createDefault()) {
            @Override
            public boolean isLocalPlayer() {
                return true;
            }
        };
        var connection = new Connection(PacketFlow.SERVERBOUND);
        channel = new EmbeddedChannel(connection);
        pilot.connection = new ServerGamePacketListenerImpl(earth.getServer(), connection, pilot,
                CommonListenerCookie.createInitial(profile, false)) {
            @Override
            public void send(Packet<?> packet) {}

            @Override
            public void send(Packet<?> packet, PacketSendListener listener) {}
        };
        pilot.setGameMode(GameType.SURVIVAL);
        require(!pilot.isCreative() && !pilot.isSpectator() && !pilot.hasPermissions(2), "pilot must be non-operator survival");
        pilot.setItemSlot(EquipmentSlot.HEAD, stack("ad_astra:netherite_space_helmet"));
        pilot.setItemSlot(EquipmentSlot.CHEST, stack("ad_astra:netherite_space_suit"));
        pilot.setItemSlot(EquipmentSlot.LEGS, stack("ad_astra:netherite_space_pants"));
        pilot.setItemSlot(EquipmentSlot.FEET, stack("ad_astra:netherite_space_boots"));
        approachPlanetMenu(earth, EARTH_X, stack("ad_astra:tier_1_rocket"), new ItemStack(Items.PAPER, 7));
    }

    private void approachPlanetMenu(ServerLevel origin, int x, ItemStack item, ItemStack cargo) {
        require(item.getItem() instanceof RocketItem, "could not recover the rocket");
        rocket = (Rocket) ((RocketItem) item.getItem()).type().create(origin);
        require(rocket != null && rocket.tier() == 1, "wrong rocket tier");
        rocket.setPos(x + .5, AdAstraConfig.atmosphereLeave - 1, LANDING_Z + .5);
        for (var leftover : origin.getEntitiesOfClass(Rocket.class, new AABB(rocket.blockPosition()).inflate(3))) {
            leftover.discard();
        }
        rocket.inventory().setItem(2, cargo);
        require(origin.addFreshEntity(rocket), "rocket not added");
        pilot.setPos(rocket.position());
        require(pilot.startRiding(rocket), "pilot could not mount the rocket");
        // Test the end of the launch separately from the ground-level countdown.
        rocket.launch();
        System.out.println("EXPEDITION_SPACE_ROUND_TRIP_ASCENT world=" + origin.dimension().location()
            + " y=" + rocket.getY());
    }

    private void selectDestination(PlanetsMenu menu) {
        ResourceKey<Level> destination = returning ? Level.OVERWORLD : Planet.MOON;
        require(menu.tier() == 1 && rocket.getY() >= AdAstraConfig.atmosphereLeave, "wrong atmosphere flight state");
        require(!ModUtils.canTeleportToPlanet(pilot, PlanetApi.API.getPlanet(Planet.MARS)), "tier one accepted Mars");
        require(ModUtils.canTeleportToPlanet(pilot, PlanetApi.API.getPlanet(destination)), "native flight checks reject destination");
        var packet = new ServerboundLandPacket(destination, returning);
        ServerboundLandPacket.TYPE.handle(packet).accept(pilot);
        require(pilot.level().dimension().equals(destination), "selection entered " + pilot.level().dimension().location());
        require(pilot.getVehicle() instanceof Lander && rocket.isRemoved(), "official trip did not exchange rocket for lander");
        lander = (Lander) pilot.getVehicle();
        require(lander.inventory().getItem(0).is(stack("ad_astra:tier_1_rocket").getItem())
            && lander.inventory().getItem(3).is(Items.PAPER) && lander.inventory().getItem(3).getCount() == 7,
            "rocket and cargo were not transferred");
        System.out.println("EXPEDITION_SPACE_ROUND_TRIP_ARRIVAL world=" + destination.location()
            + " y=" + lander.getY() + " x=" + lander.getX() + " cargo=7");
    }

    private void approachGround() {
        require(!lander.isRemoved() && pilot.getVehicle() == lander, "lander or rider was lost in descent");
        var level = (ServerLevel) lander.level();
        int ground = level.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, lander.getBlockX(), lander.getBlockZ());
        pilot.setJumping(lander.getY() - ground < 95 && lander.getDeltaMovement().y < -.38);
        if (!lander.onGround()) return;
        require(lander.isSafeToDismount(pilot), "landed but cannot exit the vehicle");
        var item = lander.inventory().removeItemNoUpdate(0);
        var cargo = lander.inventory().removeItemNoUpdate(3);
        pilot.stopRiding();
        pilot.containerMenu = pilot.inventoryMenu;
        System.out.println("EXPEDITION_SPACE_ROUND_TRIP_SURFACE world=" + level.dimension().location()
            + " y=" + lander.getY() + " ground=" + ground + " recovered=" + item + " cargo=" + cargo.getCount());
        if (!returning) {
            lander = null;
            returning = true;
            approachPlanetMenu(moon, EARTH_X + 5, item, cargo);
        } else {
            require(lander.getBlockX() == EARTH_X && lander.getBlockZ() == LANDING_Z, "return missed saved Earth location");
            require(item.is(stack("ad_astra:tier_1_rocket").getItem()) && cargo.getCount() == 7, "missing return cargo");
            System.out.println("EXPEDITION_SPACE_ROUND_TRIP_PASS");
            stop();
        }
    }

    private void stop() {
        earth.setChunkForced(0, 0, false);
        if (moon != null) moon.setChunkForced(0, 0, false);
        if (channel != null) channel.finishAndReleaseAll();
        earth = null;
    }

    private static ItemStack stack(String item) {
        return new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse(item)));
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalStateException(message);
    }
}
