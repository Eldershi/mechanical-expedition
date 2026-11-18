package expedition.migration;

import com.mojang.datafixers.DSL;
import com.mojang.serialization.Dynamic;
import java.nio.file.Path;
import net.minecraft.SharedConstants;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.NbtAccounter;
import net.minecraft.nbt.NbtIo;
import net.minecraft.nbt.NbtOps;
import net.minecraft.nbt.Tag;
import net.minecraft.util.datafix.DataFixers;
import net.minecraft.util.datafix.fixes.References;

public final class PlayerDataFixer {
    private static final int LEGACY = 3465;
    private static final int CURRENT = 3955;

    public static void main(String[] arguments) throws Exception {
        SharedConstants.tryDetectVersion();
        if (SharedConstants.getCurrentVersion().getDataVersion().getVersion() != CURRENT) {
            throw new IllegalArgumentException("Expected Minecraft 1.21.1 data fixers");
        }
        var source = NbtIo.readCompressed(Path.of(arguments[0]), NbtAccounter.unlimitedHeap());
        var output = new CompoundTag();
        var players = new ListTag();
        for (Tag input : source.getList("Players", Tag.TAG_COMPOUND)) {
            var fixed = fix(References.PLAYER, (CompoundTag) input);
            fixed.putInt("DataVersion", CURRENT);
            players.add(fixed);
        }
        var stacks = new ListTag();
        for (Tag input : source.getList("Stacks", Tag.TAG_COMPOUND)) {
            var oldStack = (CompoundTag) input;
            var fixed = LegacyCreateFilters.hasLegacySettings(oldStack)
                ? LegacyCreateFilters.convert(oldStack, stack -> fix(References.ITEM_STACK, stack))
                : fix(References.ITEM_STACK, oldStack);
            if (fixed == null) fixed = new CompoundTag();
            stacks.add(fixed);
        }
        output.put("Players", players);
        output.put("Stacks", stacks);
        NbtIo.writeCompressed(output, Path.of(arguments[1]));
    }

    private static CompoundTag fix(DSL.TypeReference reference, CompoundTag source) {
        var dynamic = new Dynamic<Tag>(NbtOps.INSTANCE, source);
        return (CompoundTag) DataFixers.getDataFixer().update(reference, dynamic, LEGACY, CURRENT).getValue();
    }
}
