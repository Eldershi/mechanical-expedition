package expedition.rockgen;

import net.minecraft.core.registries.Registries;
import net.minecraft.world.item.BlockItem;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.capabilities.Capabilities;
import net.neoforged.neoforge.capabilities.RegisterCapabilitiesEvent;
import net.neoforged.neoforge.event.BuildCreativeModeTabContentsEvent;
import net.neoforged.neoforge.registries.DeferredRegister;

import java.util.List;
import java.util.function.Supplier;

@Mod(RockGeneratorMod.ID)
public final class RockGeneratorMod {
    static final String ID = "expedition_rock_generator";
    private static final DeferredRegister<Block> BLOCKS = DeferredRegister.create(Registries.BLOCK, ID);
    private static final DeferredRegister<Item> ITEMS = DeferredRegister.create(Registries.ITEM, ID);
    private static final DeferredRegister<BlockEntityType<?>> ENTITIES =
        DeferredRegister.create(Registries.BLOCK_ENTITY_TYPE, ID);
    static final Supplier<RockGeneratorBlock> BLOCK = BLOCKS.register("rock_generator", RockGeneratorBlock::new);
    static final Supplier<BlockItem> ITEM = ITEMS.register("rock_generator",
        () -> new BlockItem(BLOCK.get(), new Item.Properties()) {
            @Override
            public void appendHoverText(ItemStack stack, Item.TooltipContext context,
                                        List<Component> tooltip, TooltipFlag flag) {
                tooltip.add(Component.translatable("block.expedition_rock_generator.controls"));
            }
        });
    static final Supplier<BlockEntityType<RockGeneratorEntity>> ENTITY = ENTITIES.register("rock_generator",
        () -> BlockEntityType.Builder.of(RockGeneratorEntity::new, BLOCK.get()).build(null));

    public RockGeneratorMod(IEventBus bus) {
        BLOCKS.register(bus);
        ITEMS.register(bus);
        ENTITIES.register(bus);
        bus.addListener(this::registerCapabilities);
        bus.addListener(this::addCreativeItem);
    }

    private void registerCapabilities(RegisterCapabilitiesEvent event) {
        event.registerBlockEntity(Capabilities.ItemHandler.BLOCK, ENTITY.get(), (entity, side) -> entity.output());
    }

    private void addCreativeItem(BuildCreativeModeTabContentsEvent event) {
        if (event.getTabKey() == ResourceKey.create(Registries.CREATIVE_MODE_TAB, ResourceLocation.withDefaultNamespace("redstone_blocks"))) {
            event.accept(ITEM.get());
        }
    }
}
