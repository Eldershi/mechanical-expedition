package expedition.motionguard;

import com.google.gson.Gson;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import expedition.motionguard.diagnostics.DiagnosticsService;
import java.util.Map;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.core.BlockPos;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingHurtEvent;
import net.minecraftforge.event.entity.living.LivingDeathEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.entity.player.PlayerContainerEvent;
import net.minecraftforge.event.entity.player.EntityItemPickupEvent;
import net.minecraftforge.event.entity.item.ItemTossEvent;
import net.minecraftforge.event.level.BlockEvent;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.event.server.*;
import net.minecraftforge.fml.common.Mod;

@Mod("expedition_player_motion_guard")
public final class PlayerMotionGuard {
    public PlayerMotionGuard() {
        var bus=MinecraftForge.EVENT_BUS;
        bus.addListener(this::started);bus.addListener(this::serverTick);bus.addListener(this::playerTick);
        bus.addListener(this::login);bus.addListener(this::logout);bus.addListener(this::dimension);
        bus.addListener(this::hurt);bus.addListener(this::death);bus.addListener(this::respawn);
        bus.addListener(this::commands);bus.addListener(this::stopping);bus.addListener(this::stopped);
        bus.addListener(this::blockBreak);bus.addListener(this::blockPlace);
        bus.addListener(this::toss);bus.addListener(this::pickup);
        bus.addListener(this::containerOpen);bus.addListener(this::containerClose);
    }
    private void started(ServerStartedEvent event) { DiagnosticsService.start(); }
    private void serverTick(TickEvent.ServerTickEvent event) { var service=DiagnosticsService.get();if(service!=null && event.phase==TickEvent.Phase.START)service.serverTick(event.getServer()); }
    private void playerTick(TickEvent.PlayerTickEvent event) { var service=DiagnosticsService.get();if(service!=null && event.phase==TickEvent.Phase.START && event.player instanceof ServerPlayer player)service.playerTick(player); }
    private static void event(String name,net.minecraft.world.entity.Entity entity,Map<String,Object> details) {
        var service=DiagnosticsService.get();if(service!=null && entity instanceof ServerPlayer player)service.playerEvent(name,player,details);
    }
    private void login(PlayerEvent.PlayerLoggedInEvent e) { event("player_login",e.getEntity(),Map.of()); }
    private void logout(PlayerEvent.PlayerLoggedOutEvent e) { event("player_logout",e.getEntity(),Map.of()); }
    private void dimension(PlayerEvent.PlayerChangedDimensionEvent e) { event("dimension_changed",e.getEntity(),Map.of("from",e.getFrom().m_135782_().toString(),"to",e.getTo().m_135782_().toString())); }
    private void respawn(PlayerEvent.PlayerRespawnEvent e) { event("player_respawn",e.getEntity(),Map.of("endConquered",e.isEndConquered())); }
    private void hurt(LivingHurtEvent e) { event("player_hurt",e.getEntity(),Map.of("amount",e.getAmount(),"damageType",e.getSource().m_19385_())); }
    private void death(LivingDeathEvent e) {
        event("player_death",e.getEntity(),Map.of("damageType",e.getSource().m_19385_()));
        if(e.getSource().m_7639_() instanceof ServerPlayer player && e.getEntity()!=player) {
            var service=DiagnosticsService.get();
            if(service!=null)service.playerAction("player_kill",player,Map.of("targetType",text(String.valueOf(ForgeRegistries.ENTITY_TYPES.getKey(e.getEntity().m_6095_()))),
                    "targetX",e.getEntity().m_20185_(),"targetY",e.getEntity().m_20186_(),"targetZ",e.getEntity().m_20189_()),false);
        }
    }
    private void blockBreak(BlockEvent.BreakEvent e) {
        if(e.getPlayer() instanceof ServerPlayer player)action("block_break_observed",player,
                Map.of("position",position(e.getPos()),"block",block(e.getState()),"cancelled",e.isCanceled()),false);
    }
    private void blockPlace(BlockEvent.EntityPlaceEvent e) {
        if(e.getEntity() instanceof ServerPlayer player)action("block_place_observed",player,
                Map.of("position",position(e.getPos()),"observedPlacedBlock",block(e.getPlacedBlock()),"cancelled",e.isCanceled()),true);
    }
    private void toss(ItemTossEvent e) { action("item_toss_observed",e.getPlayer(),item(e.getEntity().m_32055_()),false); }
    private void pickup(EntityItemPickupEvent e) { action("item_pickup_observed",e.getEntity(),item(e.getItem().m_32055_()),false); }
    private void containerOpen(PlayerContainerEvent.Open e) { action("container_open",e.getEntity(),Map.of("menuClass",text(e.getContainer().getClass().getName()),"menuId",e.getContainer().f_38840_),false); }
    private void containerClose(PlayerContainerEvent.Close e) { action("container_close",e.getEntity(),Map.of("menuClass",text(e.getContainer().getClass().getName()),"menuId",e.getContainer().f_38840_),false); }
    private static void action(String name,net.minecraft.world.entity.Entity entity,Map<String,Object> details,boolean carry) {
        var service=DiagnosticsService.get();if(service!=null && entity instanceof ServerPlayer player)service.playerAction(name,player,details,carry);
    }
    private static Map<String,Object> item(ItemStack stack) {return Map.of("item",text(String.valueOf(ForgeRegistries.ITEMS.getKey(stack.m_41720_()))),"count",stack.m_41613_());}
    private static Map<String,Integer> position(BlockPos position) {return Map.of("x",position.m_123341_(),"y",position.m_123342_(),"z",position.m_123343_());}
    private static String block(BlockState state) {return text(String.valueOf(ForgeRegistries.BLOCKS.getKey(state.m_60734_())));}
    private static String text(String text) {return text.length()>192?text.substring(0,192):text;}
    private void stopping(ServerStoppingEvent event) { var service=DiagnosticsService.get();if(service!=null)service.shutdownSnapshot("server_stopping"); }
    private void stopped(ServerStoppedEvent event) { var service=DiagnosticsService.get();if(service!=null){service.shutdownSnapshot("server_stopped");service.close();} }
    private void commands(RegisterCommandsEvent event) {
        event.getDispatcher().register(LiteralArgumentBuilder.<CommandSourceStack>literal("expeditiondiagnostics")
                .requires(source->source.m_6761_(2))
                .then(LiteralArgumentBuilder.<CommandSourceStack>literal("status").executes(context->{
                    var service=DiagnosticsService.get();String status=service==null?"diagnostics not started":new Gson().toJson(service.status());
                    context.getSource().m_288197_(() -> Component.m_237113_(status),false);return 1;}))
                .then(LiteralArgumentBuilder.<CommandSourceStack>literal("flush").executes(context->{
                    var service=DiagnosticsService.get();long target=service==null?0:service.requestForce();
                    context.getSource().m_288197_(() -> Component.m_237113_("Force requested through sequence "+target+"; verify lastContiguousForcedSequence and loss counters with status/state.json."),false);return 1;}))
                .then(LiteralArgumentBuilder.<CommandSourceStack>literal("sparkpause").executes(context->{
                    var service=DiagnosticsService.get();if(service!=null)service.pauseSpark(10);
                    context.getSource().m_288197_(() -> Component.m_237113_("Automatic spark exports paused for 10 minutes."),false);return 1;}))
                .then(LiteralArgumentBuilder.<CommandSourceStack>literal("sparkresume").executes(context->{
                    var service=DiagnosticsService.get();if(service!=null)service.pauseSpark(0);
                    context.getSource().m_288197_(() -> Component.m_237113_("Automatic spark export resume requested; source budget preflight must pass before the 45-second startup buffer."),false);return 1;}))
                .then(LiteralArgumentBuilder.<CommandSourceStack>literal("incident").executes(context->{
                    var service=DiagnosticsService.get();boolean accepted=service!=null&&service.incident("manual",Map.of());
                    context.getSource().m_288197_(() -> Component.m_237113_("Incident accepted="+accepted),false);return accepted?1:0;})));
    }
}
