package expedition.space;

import earth.terrarium.adastra.api.events.AdAstraEvents;
import earth.terrarium.adastra.api.systems.OxygenApi;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.CustomData;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;
import net.neoforged.neoforge.event.entity.player.PlayerInteractEvent;
import net.ty.createcraftedbeginning.api.canister.CanisterCapabilities;
import net.ty.createcraftedbeginning.api.canister.GasCanisterContainer;
import net.ty.createcraftedbeginning.api.gas.GasAction;
import net.ty.createcraftedbeginning.api.gas.GasStack;

public final class LifeSupport {
    private static final ResourceLocation NATURAL_AIR = ResourceLocation.parse("createcraftedbeginning:natural_air");
    private static final ResourceLocation MODULE = SpaceLogistics.id("life_support_module");
    private static final ResourceLocation THERMAL = SpaceLogistics.id("thermal_lining");
    private static final String SUPPORT_MARK = "expedition_life_support";
    private static final String HEAT_MARK = "expedition_thermal_lining";
    private static final String RESERVE_MARK = "expedition_air_reserve";
    private static final int RESERVE = 0;
    private static final int INTERVAL = 30;
    private static final int FULL_INTERVALS = 500;
    private static final int LOW_INTERVALS = 80;

    private record Payment(long until, ItemStack pack, int remaining) {}
    private record Air(ItemStack pack, GasCanisterContainer container, GasStack gas, long cost) {}
    private static final Map<UUID, Payment> paid = new HashMap<>();

    private LifeSupport() {}

    static void install() {
        AdAstraEvents.EntityOxygenEvent.register((entity, existing) ->
            existing || entity instanceof ServerPlayer player && breathe(player));
        AdAstraEvents.ColdTemperatureTickEvent.register((level, entity) ->
            !(entity instanceof ServerPlayer player && (ambient(player) ? hasGear(player) : breathe(player))));
        AdAstraEvents.HotTemperatureTickEvent.register((level, entity) ->
            !(entity instanceof ServerPlayer player && marked(player.getItemBySlot(EquipmentSlot.CHEST), HEAT_MARK)
                && (ambient(player) ? hasGear(player) : breathe(player))));
        NeoForge.EVENT_BUS.addListener(LifeSupport::attach);
        NeoForge.EVENT_BUS.addListener((PlayerEvent.PlayerLoggedOutEvent event) -> paid.remove(event.getEntity().getUUID()));
        NeoForge.EVENT_BUS.addListener((PlayerEvent.PlayerRespawnEvent event) -> paid.remove(event.getEntity().getUUID()));
    }

    private static void attach(PlayerInteractEvent.RightClickItem event) {
        if (event.getHand() != InteractionHand.MAIN_HAND || !(event.getEntity() instanceof ServerPlayer player)) return;
        ItemStack hand = event.getItemStack();
        ResourceLocation item = BuiltInRegistries.ITEM.getKey(hand.getItem());
        if (!item.equals(MODULE) && !item.equals(THERMAL)) return;
        ItemStack target = player.getOffhandItem();
        String mark;
        if (item.equals(THERMAL) && item(target, "airtight_chestplate")) mark = HEAT_MARK;
        else if (item.equals(MODULE) && item(target, "airtight_helmet")) mark = SUPPORT_MARK;
        else if (item.equals(MODULE) && item(target, "gas_canister_pack")) mark = RESERVE_MARK;
        else {
            SpaceLogistics.tell(player, "upgrade_offhand");
            return;
        }
        event.setCanceled(true);
        event.setCancellationResult(InteractionResult.SUCCESS);
        if (marked(target, mark)) {
            SpaceLogistics.tell(player, "already_upgraded");
            return;
        }
        CustomData.update(DataComponents.CUSTOM_DATA, target, tag -> tag.putBoolean(mark, true));
        if (!player.getAbilities().instabuild && !mark.equals(RESERVE_MARK)) hand.shrink(1);
        SpaceLogistics.tell(player, mark.equals(RESERVE_MARK) ? "reserve_set" : "upgrade_set");
    }

    private static boolean ambient(ServerPlayer player) {
        return OxygenApi.API.hasOxygen(player.level(), player.blockPosition());
    }

    private static boolean hasGear(ServerPlayer player) {
        ItemStack head = player.getItemBySlot(EquipmentSlot.HEAD);
        return item(head, "airtight_helmet") && marked(head, SUPPORT_MARK)
            && item(player.getItemBySlot(EquipmentSlot.CHEST), "airtight_chestplate")
            && item(player.getItemBySlot(EquipmentSlot.LEGS), "airtight_leggings")
            && item(player.getItemBySlot(EquipmentSlot.FEET), "airtight_boots");
    }

    private static boolean breathe(ServerPlayer player) {
        if (!hasGear(player)) return false;
        if (ambient(player)) return true;
        Air air = findAir(player);
        if (air == null) return false;
        long tick = player.server.overworld().getGameTime();
        Payment previous = paid.get(player.getUUID());
        if (previous != null && previous.until() > tick && previous.pack() == air.pack()) return true;
        if (air.gas().getAmount() < air.cost() || air.container().getTankPressurePa(RESERVE) <= 0) return false;

        GasStack removed = air.container().drain(RESERVE, air.cost(), GasAction.EXECUTE);
        if (removed.getAmount() != air.cost()) {
            if (!removed.isEmpty()) air.container().restoreDrainedGas(RESERVE, removed, GasAction.EXECUTE);
            air.container().save();
            return false;
        }
        air.container().save();
        int left = (int) Math.min(Integer.MAX_VALUE, (air.gas().getAmount() - air.cost()) / air.cost());
        if (left <= LOW_INTERVALS && (previous == null || previous.remaining() > LOW_INTERVALS || left % 20 == 0)) {
            SpaceLogistics.tell(player, "air_low", left * INTERVAL / 20);
        }
        paid.put(player.getUUID(), new Payment(tick + INTERVAL, air.pack(), left));
        return true;
    }

    private static Air findAir(ServerPlayer player) {
        Air empty = null;
        for (int index = 0; index < player.getInventory().getContainerSize(); index++) {
            ItemStack candidate = player.getInventory().getItem(index);
            if (!reserve(candidate, RESERVE)) continue;
            GasCanisterContainer container = candidate.getCapability(CanisterCapabilities.ITEM);
            if (container == null || container.getTanks() <= RESERVE) continue;
            GasStack gas = container.getGasInTank(RESERVE);
            long capacity = container.getTankMaxAmount(RESERVE);
            if (capacity < FULL_INTERVALS) continue;
            if (gas.getGasHolder().unwrapKey().map(key -> key.location().equals(NATURAL_AIR)).orElse(false)) {
                return new Air(candidate, container, gas, capacity / FULL_INTERVALS);
            }
            Payment previous = paid.get(player.getUUID());
            if (gas.isEmpty() && previous != null && previous.pack() == candidate) {
                empty = new Air(candidate, container, gas, capacity / FULL_INTERVALS);
            }
        }
        return empty;
    }

    public static boolean reserve(ItemStack pack, int tank) {
        return tank == RESERVE && item(pack, "gas_canister_pack") && marked(pack, RESERVE_MARK);
    }

    private static boolean marked(ItemStack stack, String name) {
        return stack.getOrDefault(DataComponents.CUSTOM_DATA, CustomData.EMPTY).contains(name);
    }

    private static boolean item(ItemStack stack, String path) {
        return BuiltInRegistries.ITEM.getKey(stack.getItem()).equals(ResourceLocation.fromNamespaceAndPath("createcraftedbeginning", path));
    }
}
