package expedition.curserules;

import auviotre.enigmatic.legacy.handlers.EnigmaticHandler;
import auviotre.enigmatic.legacy.registries.EnigmaticItems;
import java.util.Set;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.MobSpawnType;
import net.minecraft.world.entity.monster.Evoker;
import net.minecraft.world.entity.monster.Vex;
import net.minecraft.world.item.ItemStack;
import net.neoforged.bus.api.EventPriority;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.entity.EntityJoinLevelEvent;
import net.neoforged.neoforge.event.entity.living.FinalizeSpawnEvent;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;
import top.theillusivec4.curios.api.CuriosApi;
import top.theillusivec4.curios.api.SlotContext;
import top.theillusivec4.curios.api.type.capability.ICuriosItemHandler;

@Mod("expedition_curse_rules")
public final class CurseRules {
    private static final Set<ResourceLocation> BLOCKED_NATURAL_SPAWNS = Set.of(
        ResourceLocation.parse("born_in_chaos_v1:maggot"),
        ResourceLocation.parse("born_in_chaos_v1:corpse_fly"),
        ResourceLocation.parse("born_in_chaos_v1:bloody_gadfly"),
        ResourceLocation.parse("spawn:stickbug")
    );

    public CurseRules() {
        NeoForge.EVENT_BUS.addListener(EventPriority.LOWEST, CurseRules::equipDefaultRing);
        NeoForge.EVENT_BUS.addListener(CurseRules::blockEvokerVex);
        NeoForge.EVENT_BUS.addListener(CurseRules::blockNaturalPests);
    }

    private static void equipDefaultRing(PlayerEvent.PlayerLoggedInEvent event) {
        if (!(event.getEntity() instanceof ServerPlayer player)) {
            return;
        }
        var ring = EnigmaticItems.CURSED_RING.get();
        var curios = CuriosApi.getCuriosInventory(player).orElse(null);
        if (curios == null || EnigmaticHandler.isTheBlessedOne(player)) {
            return;
        }
        for (var handler : curios.getCurios().values()) {
            var stacks = handler.getStacks();
            for (int index = 0; index < stacks.getSlots(); index++) {
                if (stacks.getStackInSlot(index).is(ring)) {
                    return;
                }
            }
        }
        var inventory = player.getInventory();
        for (int slot = 0; slot < inventory.getContainerSize(); slot++) {
            ItemStack stack = inventory.getItem(slot);
            if (stack.is(ring)) {
                if (equipInRingSlot(player, curios, stack.copyWithCount(1))) {
                    stack.shrink(1);
                }
                return;
            }
        }
        equipInRingSlot(player, curios, new ItemStack(ring));
    }

    private static boolean equipInRingSlot(ServerPlayer player, ICuriosItemHandler curios, ItemStack stack) {
        var handler = curios.getStacksHandler("ring").orElse(null);
        if (handler == null) {
            return false;
        }
        var slots = handler.getStacks();
        var ring = EnigmaticItems.CURSED_RING.get();
        for (int index = 0; index < slots.getSlots(); index++) {
            var context = new SlotContext("ring", player, index, false, handler.isVisible());
            if (slots.getStackInSlot(index).isEmpty() && ring.canEquip(context, stack)) {
                curios.setEquippedCurio("ring", index, stack);
                return true;
            }
        }
        return false;
    }

    private static void blockEvokerVex(EntityJoinLevelEvent event) {
        if (!event.getLevel().isClientSide() && !event.loadedFromDisk()
                && event.getEntity() instanceof Vex vex && vex.getOwner() instanceof Evoker) {
            event.setCanceled(true);
        }
    }

    private static void blockNaturalPests(FinalizeSpawnEvent event) {
        var reason = event.getSpawnType();
        if ((reason == MobSpawnType.NATURAL || reason == MobSpawnType.CHUNK_GENERATION)
                && BLOCKED_NATURAL_SPAWNS.contains(BuiltInRegistries.ENTITY_TYPE.getKey(event.getEntity().getType()))) {
            event.setSpawnCancelled(true);
        }
    }
}
