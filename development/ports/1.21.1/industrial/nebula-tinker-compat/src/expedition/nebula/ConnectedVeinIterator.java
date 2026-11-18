package expedition.nebula;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashSet;
import modernmods.hilt.data.loadable.primitive.IntLoadable;
import modernmods.hilt.data.loadable.record.RecordLoadable;
import modernmods.modernfoundry.library.tools.definition.module.aoe.AreaOfEffectIterator;
import modernmods.modernfoundry.library.tools.item.IModifiable;
import modernmods.modernfoundry.library.tools.nbt.IToolStackView;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.block.state.BlockState;

record ConnectedVeinIterator(int maxBlocks) implements AreaOfEffectIterator.Loadable {
    static final RecordLoadable<ConnectedVeinIterator> LOADER = RecordLoadable.create(
            IntLoadable.FROM_ZERO.defaultField("max_blocks", 16, true, ConnectedVeinIterator::maxBlocks),
            ConnectedVeinIterator::new);

    ConnectedVeinIterator {
        maxBlocks = Math.clamp(maxBlocks, 1, 16);
    }

    @Override
    public RecordLoadable<ConnectedVeinIterator> getLoader() {
        return LOADER;
    }

    @Override
    public Iterable<BlockPos> getBlocks(IToolStackView tool, UseOnContext context, BlockState state,
                                        AreaOfEffectIterator.AOEMatchType matchType) {
        int expansion = Math.clamp(tool.getVolatileData().getInt(IModifiable.EXPANDED), 0, 30);
        int extraBlocks = maxBlocks + 8 * expansion - 1;
        var level = context.getLevel();
        var block = state.getBlock();
        var eligible = AreaOfEffectIterator.defaultBlockPredicate(tool, context, matchType);
        var pending = new ArrayDeque<BlockPos>();
        var checked = new HashSet<BlockPos>();
        var result = new ArrayList<BlockPos>(extraBlocks);
        var origin = context.getClickedPos();
        pending.add(origin);
        checked.add(origin);

        while (!pending.isEmpty() && result.size() < extraBlocks) {
            var current = pending.removeFirst();
            for (Direction direction : Direction.values()) {
                var next = current.relative(direction);
                if (checked.add(next) && level.getChunkSource().hasChunk(next.getX() >> 4, next.getZ() >> 4)
                        && level.getBlockState(next).is(block)
                        && eligible.test(next)) {
                    pending.addLast(next);
                    result.add(next);
                    if (result.size() == extraBlocks) {
                        break;
                    }
                }
            }
        }
        return result;
    }
}
