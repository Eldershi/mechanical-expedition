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
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.tick.PlayerTickEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;
import net.neoforged.neoforge.event.entity.living.LivingDamageEvent;
import net.neoforged.neoforge.event.entity.living.LivingDeathEvent;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;
import net.neoforged.neoforge.event.entity.player.PlayerContainerEvent;
import net.neoforged.neoforge.event.entity.player.ItemEntityPickupEvent;
import net.neoforged.neoforge.event.entity.item.ItemTossEvent;
import net.neoforged.neoforge.event.level.BlockEvent;
import net.minecraft.core.registries.BuiltInRegistries;
import net.neoforged.neoforge.event.server.*;
import net.neoforged.fml.common.Mod;

@Mod("expedition_player_motion_guard")
public final class PlayerMotionGuard {
    public PlayerMotionGuard() {
        var bus=NeoForge.EVENT_BUS;
        bus.addListener(this::started);bus.addListener(this::serverTick);bus.addListener(this::playerTick);
        bus.addListener(this::login);bus.addListener(this::logout);bus.addListener(this::dimension);
        bus.addListener(this::hurt);bus.addListener(this::death);bus.addListener(this::respawn);
        bus.addListener(this::commands);bus.addListener(this::stopping);bus.addListener(this::stopped);
        bus.addListener(this::blockBreak);bus.addListener(this::blockPlace);
        bus.addListener(this::toss);bus.addListener(this::pickup);
        bus.addListener(this::containerOpen);bus.addListener(this::containerClose);
    }
    private void started(ServerStartedEvent event) { DiagnosticsService.start(); }
    private void serverTick(ServerTickEvent.Pre event) { var service=DiagnosticsService.get();if(service!=null)service.serverTick(event.getServer()); }
    private void playerTick(PlayerTickEvent.Pre event) { var service=DiagnosticsService.get();if(service!=null && event.getEntity() instanceof ServerPlayer player)service.playerTick(player); }
    private static void event(String name,net.minecraft.world.entity.Entity entity,Map<String,Object> details) {
        var service=DiagnosticsService.get();if(service!=null && entity instanceof ServerPlayer player)service.playerEvent(name,player,details);
    }
    private void login(PlayerEvent.PlayerLoggedInEvent e) { event("player_login",e.getEntity(),Map.of()); }
    private void logout(PlayerEvent.PlayerLoggedOutEvent e) { event("player_logout",e.getEntity(),Map.of()); }
    private void dimension(PlayerEvent.PlayerChangedDimensionEvent e) { event("dimension_changed",e.getEntity(),Map.of("from",e.getFrom().location().toString(),"to",e.getTo().location().toString())); }
    private void respawn(PlayerEvent.PlayerRespawnEvent e) { event("player_respawn",e.getEntity(),Map.of("endConquered",e.isEndConquered())); }
    private void hurt(LivingDamageEvent.Post e) { event("player_hurt",e.getEntity(),Map.of("amount",e.getNewDamage(),"damageType",e.getSource().getMsgId())); }
    private void death(LivingDeathEvent e) {
        event("player_death",e.getEntity(),Map.of("damageType",e.getSource().getMsgId()));
        if(e.getSource().getEntity() instanceof ServerPlayer player && e.getEntity()!=player) {
            var service=DiagnosticsService.get();
            if(service!=null)service.playerAction("player_kill",player,Map.of("targetType",text(String.valueOf(BuiltInRegistries.ENTITY_TYPE.getKey(e.getEntity().getType()))),
                    "targetX",e.getEntity().getX(),"targetY",e.getEntity().getY(),"targetZ",e.getEntity().getZ()),false);
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
    private void toss(ItemTossEvent e) { action("item_toss_observed",e.getPlayer(),item(e.getEntity().getItem()),false); }
    private void pickup(ItemEntityPickupEvent.Post e) { action("item_pickup_observed",e.getPlayer(),item(e.getOriginalStack()),false); }
    private void containerOpen(PlayerContainerEvent.Open e) { action("container_open",e.getEntity(),Map.of("menuClass",text(e.getContainer().getClass().getName()),"menuId",e.getContainer().containerId),false); }
    private void containerClose(PlayerContainerEvent.Close e) { action("container_close",e.getEntity(),Map.of("menuClass",text(e.getContainer().getClass().getName()),"menuId",e.getContainer().containerId),false); }
    private static void action(String name,net.minecraft.world.entity.Entity entity,Map<String,Object> details,boolean carry) {
        var service=DiagnosticsService.get();if(service!=null && entity instanceof ServerPlayer player)service.playerAction(name,player,details,carry);
    }
    private static Map<String,Object> item(ItemStack stack) {return Map.of("item",text(String.valueOf(BuiltInRegistries.ITEM.getKey(stack.getItem()))),"count",stack.getCount());}
    private static Map<String,Integer> position(BlockPos position) {return Map.of("x",position.getX(),"y",position.getY(),"z",position.getZ());}
    private static String block(BlockState state) {return text(String.valueOf(BuiltInRegistries.BLOCK.getKey(state.getBlock())));}
    private static String text(String text) {return text.length()>192?text.substring(0,192):text;}
    private void stopping(ServerStoppingEvent event) { var service=DiagnosticsService.get();if(service!=null)service.shutdownSnapshot("server_stopping"); }
    private void stopped(ServerStoppedEvent event) { var service=DiagnosticsService.get();if(service!=null){service.shutdownSnapshot("server_stopped");service.close();} }
    private void commands(RegisterCommandsEvent event) {
        event.getDispatcher().register(LiteralArgumentBuilder.<CommandSourceStack>literal("expeditiondiagnostics")
                .requires(source->source.hasPermission(2))
                .then(LiteralArgumentBuilder.<CommandSourceStack>literal("status").executes(context->{
                    var service=DiagnosticsService.get();String status=service==null?"diagnostics not started":new Gson().toJson(service.status());
                    context.getSource().sendSuccess(() -> Component.literal(status),false);return 1;}))
                .then(LiteralArgumentBuilder.<CommandSourceStack>literal("flush").executes(context->{
                    var service=DiagnosticsService.get();long target=service==null?0:service.requestForce();
                    context.getSource().sendSuccess(() -> Component.literal("Force requested through sequence "+target+"; verify lastContiguousForcedSequence and loss counters with status/state.json."),false);return 1;}))
                .then(LiteralArgumentBuilder.<CommandSourceStack>literal("sparkpause").executes(context->{
                    var service=DiagnosticsService.get();if(service!=null)service.pauseSpark(10);
                    context.getSource().sendSuccess(() -> Component.literal("Automatic spark exports paused for 10 minutes."),false);return 1;}))
                .then(LiteralArgumentBuilder.<CommandSourceStack>literal("sparkresume").executes(context->{
                    var service=DiagnosticsService.get();if(service!=null)service.pauseSpark(0);
                    context.getSource().sendSuccess(() -> Component.literal("Automatic spark export resume requested; source budget preflight must pass before the 45-second startup buffer."),false);return 1;}))
                .then(LiteralArgumentBuilder.<CommandSourceStack>literal("incident").executes(context->{
                    var service=DiagnosticsService.get();boolean accepted=service!=null&&service.incident("manual",Map.of());
                    context.getSource().sendSuccess(() -> Component.literal("Incident accepted="+accepted),false);return accepted?1:0;})));
    }
}
