package expedition.motionguard.diagnostics;

import java.lang.reflect.Method;
import java.util.*;
import java.util.concurrent.atomic.AtomicLong;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraftforge.common.util.LazyOptional;
import net.minecraftforge.items.IItemHandler;
import net.minecraftforge.registries.ForgeRegistries;

/** Bounded selected metadata; never serializes an inventory or complete item/entity NBT. */
public final class EquipmentCapture {
    private Method curiosInventory, equippedCurios;
    private EntityDataAccessor<CompoundTag> carryKey;
    public final AtomicLong errors = new AtomicLong();
    public EquipmentCapture() {
        try {
            Class<?> api=Class.forName("top.theillusivec4.curios.api.CuriosApi");
            curiosInventory=api.getMethod("getCuriosInventory",net.minecraft.world.entity.LivingEntity.class);
            equippedCurios=Class.forName("top.theillusivec4.curios.api.type.capability.ICuriosItemHandler")
                    .getMethod("getEquippedCurios");
        } catch(ReflectiveOperationException|LinkageError ignored) { curiosInventory=null; }
        try {
            @SuppressWarnings("unchecked")
            EntityDataAccessor<CompoundTag> key=(EntityDataAccessor<CompoundTag>)Class.forName(
                    "tschipp.carryon.common.carry.CarryOnDataManager").getField("CARRY_DATA_KEY").get(null);
            carryKey=key;
        } catch(ReflectiveOperationException|LinkageError ignored) { carryKey=null; }
    }
    public Map<String,Object> capture(ServerPlayer player) {
        Map<String,Object> result=new LinkedHashMap<>();
        List<Object> gear=new ArrayList<>();
        for(EquipmentSlot slot:EquipmentSlot.values()) gear.add(item(slot.name(),player.m_6844_(slot)));
        result.put("equipment",List.copyOf(gear));
        result.put("movementSpeed",player.m_21133_(Attributes.f_22279_));
        if(curiosInventory==null) result.put("curios","unavailable");
        else try {
            LazyOptional<?> optional=(LazyOptional<?>)curiosInventory.invoke(null,player);
            Object handler=optional.resolve().orElse(null);
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
        if(carryKey==null)return "unavailable";
        try {
            // Read selected fields directly; CarryOn getCarryData() copies complete container/entity NBT.
            CompoundTag data=player.m_20088_().m_135370_(carryKey);
            String type=data.m_128461_("type"),content="";
            if(type.equals("BLOCK"))content=shortText(data.m_128469_("block").m_128461_("Name"));
            else if(type.equals("ENTITY"))content=shortText(data.m_128469_("entity").m_128461_("id"));
            else if(type.equals("INVALID")||type.isEmpty())type="NONE";
            return Map.of("type",shortText(type),"contentId",content);
        } catch(RuntimeException|LinkageError problem){errors.incrementAndGet();return "read_error";}
    }
    private static Map<String,Object> item(String slot,ItemStack stack) {
        if(stack.m_41619_()) return Map.of("slot",slot,"item","minecraft:air");
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("slot",slot); result.put("item",shortText(String.valueOf(ForgeRegistries.ITEMS.getKey(stack.m_41720_()))));
        result.put("count",stack.m_41613_()); result.put("damage",stack.m_41773_());
        CompoundTag tag=stack.m_41783_();
        if(tag!=null) {
            ListTag enchantments=tag.m_128437_("Enchantments",10); List<Object> enchants=new ArrayList<>();
            for(int i=0;i<Math.min(16,enchantments.size());i++) {
                CompoundTag enchantment=enchantments.m_128728_(i);
                enchants.add(Map.of("id",shortText(enchantment.m_128461_("id")),"level",enchantment.m_128448_("lvl")));
            }
            result.put("enchantments",List.copyOf(enchants));
            ListTag modifiers=tag.m_128437_("AttributeModifiers",10); List<Object> attributes=new ArrayList<>();
            for(int i=0;i<Math.min(16,modifiers.size());i++) {
                CompoundTag modifier=modifiers.m_128728_(i);
                attributes.add(Map.of("attribute",shortText(modifier.m_128461_("AttributeName")),
                        "name",shortText(modifier.m_128461_("Name")),"amount",modifier.m_128459_("Amount"),
                        "operation",modifier.m_128451_("Operation"),"slot",shortText(modifier.m_128461_("Slot"))));
            }
            result.put("attributeModifiers",List.copyOf(attributes));
            result.put("metadataTruncated",enchantments.size()>16||modifiers.size()>16);
        }
        return Collections.unmodifiableMap(result);
    }
    private static String shortText(String value) { return value.length()>192?value.substring(0,192):value; }
}
