package expedition.motionguard.diagnostics;

import java.lang.reflect.Method;
import java.util.*;
import java.util.concurrent.atomic.AtomicLong;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.core.Holder;
import net.minecraft.core.component.DataComponents;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.ItemAttributeModifiers;
import net.neoforged.neoforge.items.IItemHandler;
import net.minecraft.core.registries.BuiltInRegistries;

/** Bounded selected metadata; never serializes an inventory or complete item/entity NBT. */
public final class EquipmentCapture {
    private Method curiosInventory, equippedCurios;
    private Method carryData, carrying, carryContent;
    private Object carryBlock, carryEntity, carryPlayer;
    public final AtomicLong errors = new AtomicLong();
    public EquipmentCapture() {
        try {
            Class<?> api=Class.forName("top.theillusivec4.curios.api.CuriosApi");
            curiosInventory=api.getMethod("getCuriosInventory",net.minecraft.world.entity.LivingEntity.class);
            equippedCurios=Class.forName("top.theillusivec4.curios.api.type.capability.ICuriosItemHandler")
                    .getMethod("getEquippedCurios");
        } catch(ReflectiveOperationException|LinkageError ignored) { curiosInventory=null; }
        try {
            Class<?> manager = Class.forName("tschipp.carryon.common.carry.CarryOnDataManager");
            Class<?> data = Class.forName("tschipp.carryon.common.carry.CarryOnData");
            Class<?> type = Class.forName("tschipp.carryon.common.carry.CarryOnData$CarryType");
            carryData = manager.getMethod("getCarryData", net.minecraft.world.entity.player.Player.class);
            carrying = data.getMethod("isCarrying", type);
            carryContent = data.getMethod("getContentNbt");
            carryBlock = type.getField("BLOCK").get(null);
            carryEntity = type.getField("ENTITY").get(null);
            carryPlayer = type.getField("PLAYER").get(null);
        } catch(ReflectiveOperationException|LinkageError ignored) { carryData = null; }
    }
    public Map<String,Object> capture(ServerPlayer player) {
        Map<String,Object> result=new LinkedHashMap<>();
        List<Object> gear=new ArrayList<>();
        for(EquipmentSlot slot:EquipmentSlot.values()) gear.add(item(slot.name(),player.getItemBySlot(slot)));
        result.put("equipment",List.copyOf(gear));
        result.put("movementSpeed",player.getAttributeValue(Attributes.MOVEMENT_SPEED));
        if(curiosInventory==null) result.put("curios","unavailable");
        else try {
            Optional<?> optional=(Optional<?>)curiosInventory.invoke(null,player);
            Object handler=optional.orElse(null);
            List<Object> curios=new ArrayList<>();
            if(handler!=null) {
                IItemHandler items=(IItemHandler)equippedCurios.invoke(handler);
                int count=Math.min(64,items.getSlots());
                for(int i=0;i<count;i++) curios.add(item("curio/"+i,items.getStackInSlot(i)));
                result.put("curioSlotsTruncated",items.getSlots()>64);
            }
            result.put("curios",List.copyOf(curios));
        } catch(ReflectiveOperationException|RuntimeException|LinkageError problem) { errors.incrementAndGet(); result.put("curios","read_error"); }
        result.put("carryOn",captureCarry(player));
        return Collections.unmodifiableMap(result);
    }
    public Object captureCarry(ServerPlayer player) {
        if (carryData == null) return "unavailable";
        try {
            Object data = carryData.invoke(null, player);
            if (data == null) return Map.of("type", "NONE", "contentId", "");
            // The public content getter returns only the selected compound without serializing it.
            if (Boolean.TRUE.equals(carrying.invoke(data, carryBlock))) {
                CompoundTag content = (CompoundTag) carryContent.invoke(data);
                return Map.of("type", "BLOCK", "contentId", shortText(content.getString("Name")));
            }
            if (Boolean.TRUE.equals(carrying.invoke(data, carryEntity))) {
                CompoundTag content = (CompoundTag) carryContent.invoke(data);
                return Map.of("type", "ENTITY", "contentId", shortText(content.getString("id")));
            }
            String type = Boolean.TRUE.equals(carrying.invoke(data, carryPlayer)) ? "PLAYER" : "NONE";
            return Map.of("type", type, "contentId", "");
        } catch (ReflectiveOperationException | RuntimeException | LinkageError problem) {
            errors.incrementAndGet();
            return "read_error";
        }
    }
    private static Map<String,Object> item(String slot,ItemStack stack) {
        if(stack.isEmpty()) return Map.of("slot",slot,"item","minecraft:air");
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("slot",slot); result.put("item",shortText(String.valueOf(BuiltInRegistries.ITEM.getKey(stack.getItem()))));
        result.put("count",stack.getCount()); result.put("damage",stack.getDamageValue());
        var enchantments = stack.getEnchantments();
        List<Object> enchants = enchantments.entrySet().stream().limit(16)
                .<Object>map(entry -> Map.of("id", holderId(entry.getKey()), "level", entry.getIntValue()))
                .toList();
        var modifiers = stack.getOrDefault(DataComponents.ATTRIBUTE_MODIFIERS, ItemAttributeModifiers.EMPTY)
                .modifiers();
        List<Object> attributes = modifiers.stream().limit(16)
                .<Object>map(entry -> Map.of("attribute", holderId(entry.attribute()),
                        "name", shortText(entry.modifier().id().toString()), "amount", entry.modifier().amount(),
                        "operation", entry.modifier().operation().id(), "slot", entry.slot().getSerializedName()))
                .toList();
        result.put("enchantments", enchants);
        result.put("attributeModifiers", attributes);
        result.put("metadataTruncated", enchantments.size() > 16 || modifiers.size() > 16);
        return Collections.unmodifiableMap(result);
    }
    private static String holderId(Holder<?> holder) {
        return shortText(holder.unwrapKey().map(ResourceKey::location).map(Object::toString).orElse("unregistered"));
    }
    private static String shortText(String value) { return value.length()>192?value.substring(0,192):value; }
}
