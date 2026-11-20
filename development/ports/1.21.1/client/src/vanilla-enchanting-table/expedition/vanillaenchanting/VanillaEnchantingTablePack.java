package expedition.vanillaenchanting;

import java.io.InputStream;
import java.util.Optional;
import java.util.Set;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.AbstractPackResources;
import net.minecraft.server.packs.PackLocationInfo;
import net.minecraft.server.packs.PackType;
import net.minecraft.server.packs.VanillaPackResources;
import net.minecraft.server.packs.repository.PackSource;
import net.minecraft.server.packs.resources.IoSupplier;

public final class VanillaEnchantingTablePack extends AbstractPackResources {
    private static final Set<ResourceLocation> ASSETS = Set.of(
        ResourceLocation.withDefaultNamespace("blockstates/enchanting_table.json"),
        ResourceLocation.withDefaultNamespace("models/block/enchanting_table.json"),
        ResourceLocation.withDefaultNamespace("models/item/enchanting_table.json"),
        ResourceLocation.withDefaultNamespace("textures/block/enchanting_table_bottom.png"),
        ResourceLocation.withDefaultNamespace("textures/block/enchanting_table_side.png"),
        ResourceLocation.withDefaultNamespace("textures/block/enchanting_table_top.png"),
        ResourceLocation.withDefaultNamespace("textures/entity/enchanting_table_book.png")
    );

    private final VanillaPackResources vanilla;

    public VanillaEnchantingTablePack(VanillaPackResources vanilla) {
        super(new PackLocationInfo("expedition:vanilla_enchanting_table",
            Component.literal("Vanilla Enchanting Table"), PackSource.BUILT_IN, Optional.empty()));
        this.vanilla = vanilla;
    }

    @Override
    public IoSupplier<InputStream> getRootResource(String... path) {
        return null;
    }

    @Override
    public IoSupplier<InputStream> getResource(PackType type, ResourceLocation id) {
        return type == PackType.CLIENT_RESOURCES && ASSETS.contains(id) ? vanilla.getResource(type, id) : null;
    }

    @Override
    public void listResources(PackType type, String namespace, String prefix, ResourceOutput output) {
        if (type != PackType.CLIENT_RESOURCES || !namespace.equals("minecraft")) return;
        for (var id : ASSETS) {
            if (prefix.isEmpty() || id.getPath().startsWith(prefix + "/")) {
                var resource = vanilla.getResource(type, id);
                if (resource != null) output.accept(id, resource);
            }
        }
    }

    @Override
    public Set<String> getNamespaces(PackType type) {
        return type == PackType.CLIENT_RESOURCES ? Set.of("minecraft") : Set.of();
    }

    @Override
    public void close() {
        // Minecraft owns the underlying vanilla pack.
    }
}
