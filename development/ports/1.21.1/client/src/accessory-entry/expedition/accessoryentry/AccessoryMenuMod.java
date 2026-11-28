package expedition.accessoryentry;

import net.minecraft.core.registries.Registries;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.MenuProvider;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.MenuType;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.extensions.IMenuTypeExtension;
import net.neoforged.neoforge.network.event.RegisterPayloadHandlersEvent;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;

@Mod(AccessoryMenuMod.ID)
public final class AccessoryMenuMod {
    public static final String ID = "expedition_accessory_entry";
    private static final DeferredRegister<MenuType<?>> MENUS = DeferredRegister.create(Registries.MENU, ID);
    static final DeferredHolder<MenuType<?>, MenuType<AccessoryMenu>> MENU = MENUS.register(
        "equipment", () -> IMenuTypeExtension.create(AccessoryMenu::fromServer));

    public AccessoryMenuMod(IEventBus bus) {
        MENUS.register(bus);
        bus.addListener(AccessoryMenuMod::registerPayload);
    }

    private static void registerPayload(RegisterPayloadHandlersEvent event) {
        event.registrar("2").playToServer(OpenMenu.TYPE, OpenMenu.CODEC, (payload, context) -> {
            if (context.player() instanceof ServerPlayer player && player.isAlive()
                    && player.containerMenu == player.inventoryMenu
                    && player.inventoryMenu.getCarried().isEmpty()) {
                var layout = AccessoryMenu.Layout.forPlayer(player);
                player.openMenu(new MenuProvider() {
                    @Override
                    public Component getDisplayName() {
                        return Component.translatable("expedition.accessory_entry.title");
                    }

                    @Override
                    public AccessoryMenu createMenu(int id, Inventory inventory, Player owner) {
                        return new AccessoryMenu(id, inventory, layout);
                    }
                }, buffer -> {
                    buffer.writeInt(layout.signature());
                    buffer.writeVarInt(layout.keys().size());
                });
            }
        });
    }

    public enum OpenMenu implements CustomPacketPayload {
        INSTANCE;

        public static final Type<OpenMenu> TYPE = new Type<>(ResourceLocation.fromNamespaceAndPath(ID, "open_equipment"));
        static final StreamCodec<RegistryFriendlyByteBuf, OpenMenu> CODEC = StreamCodec.unit(INSTANCE);

        @Override
        public Type<OpenMenu> type() {
            return TYPE;
        }
    }
}
