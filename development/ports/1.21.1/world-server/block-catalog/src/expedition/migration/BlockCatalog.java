package expedition.migration;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.serialization.Dynamic;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import net.minecraft.SharedConstants;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtOps;
import net.minecraft.nbt.NbtUtils;
import net.minecraft.nbt.Tag;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.datafix.DataFixers;
import net.minecraft.util.datafix.fixes.References;
import net.minecraft.world.level.block.EntityBlock;
import net.minecraft.world.level.block.state.properties.Property;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.server.ServerStartedEvent;

@Mod("expedition_block_catalog")
public final class BlockCatalog {
    public BlockCatalog() {
        NeoForge.EVENT_BUS.addListener(this::export);
    }

    private void export(ServerStartedEvent event) {
        try {
            var document = new JsonObject();
            var blocks = new JsonObject();
            for (var entry : BuiltInRegistries.BLOCK.entrySet()) {
                var block = entry.getValue();
                var row = new JsonObject();
                row.addProperty("air", block.defaultBlockState().isAir());
                row.addProperty("item", BuiltInRegistries.ITEM.getKey(block.asItem()).toString());
                row.addProperty("block_entity", block.defaultBlockState().hasBlockEntity());
                var properties = new JsonObject();
                for (var property : block.getStateDefinition().getProperties()) {
                    properties.add(property.getName(), values(property));
                }
                row.add("properties", properties);
                if (entry.getKey().location().toString().equals("modernfoundry:seared_bricks")
                    && block instanceof EntityBlock entityBlock) {
                    var stateless = new JsonArray();
                    for (var state : block.getStateDefinition().getPossibleStates()) {
                        if (entityBlock.newBlockEntity(BlockPos.ZERO, state) == null) {
                            var stateProperties = new JsonObject();
                            var tag = NbtUtils.writeBlockState(state).getCompound("Properties");
                            for (String key : tag.getAllKeys()) {
                                stateProperties.addProperty(key, tag.getString(key));
                            }
                            stateless.add(stateProperties);
                        }
                    }
                    row.add("states_without_entity", stateless);
                }
                blocks.add(entry.getKey().location().toString(), row);
            }
            var fixes = new JsonObject();
            var states = Path.of("legacy-block-states.jsonl");
            int version = SharedConstants.getCurrentVersion().getDataVersion().getVersion();
            if (Files.exists(states)) {
                for (String line : Files.readAllLines(states)) {
                    readLegacyState(fixes, JsonParser.parseString(line).getAsJsonArray(), version);
                }
            }
            document.add("blocks", blocks);
            document.add("fixes", fixes);
            Files.writeString(Path.of("block-catalog.json"), new Gson().toJson(document));
            System.out.println("EXPEDITION_BLOCK_CATALOG_PASS blocks=" + blocks.size() + " fixes=" + fixes.size());
        } catch (IOException error) {
            throw new IllegalStateException("Could not export the migration block catalog", error);
        }
    }

    private static <T extends Comparable<T>> JsonArray values(Property<T> property) {
        var values = new JsonArray();
        for (T value : property.getPossibleValues()) {
            values.add(property.getName(value));
        }
        return values;
    }

    private static void readLegacyState(JsonObject fixes, JsonArray input, int targetVersion) {
        int sourceVersion = input.get(0).getAsInt();
        String blockId = input.get(1).getAsString();
        String serialized = input.get(2).getAsString();
        var properties = new CompoundTag();
        for (var entry : JsonParser.parseString(serialized).getAsJsonObject().entrySet()) {
            properties.putString(entry.getKey(), entry.getValue().getAsString());
        }
        var state = new CompoundTag();
        state.putString("Name", blockId);
        if (!properties.isEmpty()) {
            state.put("Properties", properties);
        }
        var fixed = (CompoundTag) DataFixers.getDataFixer()
            .update(References.BLOCK_STATE, new Dynamic<Tag>(NbtOps.INSTANCE, state), sourceVersion, targetVersion)
            .getValue();
        var fixedId = fixed.getString("Name");
        var resolved = BuiltInRegistries.BLOCK.get(ResourceLocation.parse(fixedId));
        var result = new JsonObject();
        result.addProperty("fixed_id", fixedId);
        result.addProperty("resolved", BuiltInRegistries.BLOCK.getKey(resolved).toString());
        fixes.add(sourceVersion + "/" + blockId + "/" + serialized, result);
    }
}
