package expedition.factorycontroller.tests;

import com.google.gson.GsonBuilder;
import com.simibubi.create.api.packager.unpacking.UnpackingHandler;
import com.simibubi.create.content.kinetics.crafter.ConnectedInputHandler;
import com.simibubi.create.content.kinetics.crafter.MechanicalCrafterBlockEntity;
import com.simibubi.create.content.logistics.BigItemStack;
import com.simibubi.create.content.logistics.box.PackageItem;
import com.simibubi.create.content.logistics.packager.repackager.PackageRepackageHelper;
import com.simibubi.create.content.logistics.stockTicker.PackageOrder;
import com.simibubi.create.content.logistics.stockTicker.PackageOrderWithCrafts;
import com.simibubi.create.content.logistics.stockTicker.PackageOrderWithCrafts.CraftingEntry;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.registries.ForgeRegistries;

/** Disposable server probe for large-pattern repackaging and real crafter inventories. */
@Mod("expedition_factorycontroller_probe")
public final class FactoryControllerProbe {
    private int ticks;
    private boolean ran;
    private final List<String> passed = new ArrayList<>();

    public FactoryControllerProbe() {
        if (!Boolean.getBoolean("expedition.factorycontroller.probe"))
            throw new IllegalStateException("This probe requires an explicitly isolated test server");
        MinecraftForge.EVENT_BUS.addListener(this::tick);
    }

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    private static ItemStack item(String name, int count) {
        var value = ForgeRegistries.ITEMS.getValue(new ResourceLocation(name));
        check(value != null, "Missing item " + name);
        return new ItemStack(value, count);
    }

    private static String id(ItemStack stack) {
        return ForgeRegistries.ITEMS.getKey(stack.m_41720_()).toString();
    }

    private static Map<String, Integer> contents(List<ItemStack> stacks) {
        Map<String, Integer> result = new LinkedHashMap<>();
        for (ItemStack stack : stacks) if (!stack.m_41619_()) result.merge(id(stack), stack.m_41613_(), Integer::sum);
        return result;
    }

    private static List<ItemStack> packageContents(ItemStack box) {
        var inventory = PackageItem.getContents(box);
        List<ItemStack> stacks = new ArrayList<>();
        for (int i = 0; i < inventory.getSlots(); i++) stacks.add(inventory.getStackInSlot(i).m_41777_());
        return stacks;
    }

    private static List<BigItemStack> wheelPattern() {
        List<BigItemStack> pattern = new ArrayList<>();
        for (int y = 0; y < 5; y++) for (int x = 0; x < 5; x++) {
            ItemStack stack;
            if ((x == 0 || x == 4) && (y == 0 || y == 4)) stack = ItemStack.f_41583_;
            else if (x == 2 && y == 2) stack = item("minecraft:stone", 1);
            else if ((x == 2 && (y == 1 || y == 3)) || (y == 2 && (x == 1 || x == 3))) stack = item("minecraft:oak_planks", 1);
            else stack = item("create:andesite_alloy", 1);
            pattern.add(new BigItemStack(stack));
        }
        return pattern;
    }

    private static List<BigItemStack> chestPattern() {
        List<BigItemStack> pattern = new ArrayList<>();
        for (int i = 0; i < 9; i++) pattern.add(new BigItemStack(i == 4 ? ItemStack.f_41583_ : item("minecraft:oak_planks", 1)));
        return pattern;
    }

    private static PackageOrderWithCrafts order(List<BigItemStack> pattern, int crafts) {
        Map<String, Integer> totals = new LinkedHashMap<>();
        for (var cell : pattern) if (!cell.stack.m_41619_()) totals.merge(id(cell.stack), crafts, Integer::sum);
        List<BigItemStack> requested = new ArrayList<>();
        for (var e : totals.entrySet()) requested.add(new BigItemStack(item(e.getKey(), 1), e.getValue()));
        return new PackageOrderWithCrafts(new PackageOrder(requested), List.of(new CraftingEntry(new PackageOrder(pattern), crafts)));
    }

    private List<ItemStack> repack(ServerLevel level, String label, List<BigItemStack> pattern, int crafts) {
        var context = order(pattern, crafts);
        var helper = new PackageRepackageHelper();
        List<ItemStack> first = new ArrayList<>(), second = new ArrayList<>(), expectedStacks = new ArrayList<>();
        int i = 0;
        for (var row : context.stacks()) {
            ItemStack stack = row.stack.m_255036_(row.count);
            expectedStacks.add(stack.m_41777_());
            (i++ % 2 == 0 ? first : second).add(stack);
        }
        // A recipe with one item type still gets two independently sourced fragments.
        if (second.isEmpty()) {
            var stack = first.get(0);
            int split = stack.m_41613_() / 2;
            second.add(stack.m_255036_(split));
            stack.m_41764_(stack.m_41613_() - split);
        }
        int orderId = 17304 + passed.size();
        ItemStack partA = PackageItem.containing(first);
        ItemStack partB = PackageItem.containing(second);
        PackageItem.addAddress(partA, "FactoryControllerProbe");
        PackageItem.addAddress(partB, "FactoryControllerProbe");
        PackageItem.setOrder(partA, orderId, 0, false, 0, true, context);
        PackageItem.setOrder(partB, orderId, 1, true, 0, true, context);
        check(helper.addPackageFragment(partA) == -1, label + " incomplete order must wait");
        check(helper.addPackageFragment(partB) == orderId, label + " second source completes order");
        var packed = helper.repack(orderId, level.m_213780_());
        List<ItemStack> boxes = new ArrayList<>(), actualStacks = new ArrayList<>();
        for (var row : packed) for (int n = 0; n < row.count; n++) {
            check(PackageItem.isPackage(row.stack), label + " output is a package");
            boxes.add(row.stack.m_41777_());
            actualStacks.addAll(packageContents(row.stack));
            var recipe = PackageItem.getOrderContext(row.stack).getCraftingInformation();
            check(recipe.size() == pattern.size(), label + " pattern retains all cells");
            for (int cell = 0; cell < pattern.size(); cell++)
                check(ItemStack.m_150942_(recipe.get(cell).stack, pattern.get(cell).stack), label + " pattern slot " + cell);
        }
        check(boxes.size() == crafts, label + " exactly one output package per craft, got " + boxes.size());
        check(contents(actualStacks).equals(contents(expectedStacks)), label + " ingredient conservation: " + contents(actualStacks));
        helper.clear();
        passed.add(label + ":repack-conservation-pattern");
        return boxes;
    }

    private void unpack(ServerLevel level, String label, List<BigItemStack> pattern, ItemStack box, int grid, int offset) {
        var spawn = level.m_220360_();
        BlockPos origin = new BlockPos(spawn.m_123341_() + offset, Math.min(250, spawn.m_123342_() + 10), spawn.m_123343_());
        var block = ForgeRegistries.BLOCKS.getValue(new ResourceLocation("create:mechanical_crafter"));
        check(block != null, "Mechanical crafter registered");
        BlockState state = block.m_49966_();
        List<BlockPos> positions = new ArrayList<>();
        for (int y = 0; y < grid; y++) for (int x = 0; x < grid; x++) {
            BlockPos position = new BlockPos(origin.m_123341_() + x, origin.m_123342_() - y, origin.m_123343_());
            check(level.m_7731_(position, state, 3), label + " fixture block " + position);
            positions.add(position);
        }
        try {
            var controller = (MechanicalCrafterBlockEntity) level.m_7702_(origin);
            check(controller != null, label + " fixture block entity");
            ConnectedInputHandler.initAndAddAll(level, controller, positions.subList(1, positions.size()));
            var inventories = controller.getInput().getInventories(level, origin);
            check(inventories.size() == grid * grid, label + " connected grid slots " + inventories.size());
            var handler = UnpackingHandler.REGISTRY.get(block);
            check(handler != null, label + " registered unpacking handler");
            var context = PackageItem.getOrderContext(box);
            // Create consumes the supplied working-list copies in both simulation and insertion.
            // Simulation must preserve world inventories and the original package NBT instead.
            var originalContents = contents(packageContents(box));
            check(handler.unpack(level, origin, state, Direction.NORTH, packageContents(box), context, true), label + " simulated insertion");
            check(originalContents.equals(contents(packageContents(box))), label + " simulation preserves original package");
            for (var inventory : inventories) check(inventory.getStackInSlot(0).m_41619_(), label + " simulation preserves empty grid");
            List<ItemStack> payload = packageContents(box);
            check(handler.unpack(level, origin, state, Direction.NORTH, payload, context, false), label + " real insertion");
            check(contents(payload).isEmpty(), label + " all package materials consumed");
            for (int cell = 0; cell < pattern.size(); cell++) {
                ItemStack actual = inventories.get(cell).getStackInSlot(0);
                ItemStack expected = pattern.get(cell).stack;
                check(ItemStack.m_150942_(actual, expected), label + " real pattern slot " + cell);
                check(actual.m_41619_() || actual.m_41613_() == 1, label + " exactly one ingredient per filled slot");
            }
            passed.add(label + ":simulate-and-real-grid-insertion");
        } finally {
            // A disposable fixture only: clear contents first so cleanup cannot drop test ingredients.
            for (var position : positions) {
                if (level.m_7702_(position) instanceof MechanicalCrafterBlockEntity crafter)
                    crafter.getInventory().setStackInSlot(0, ItemStack.f_41583_);
                level.m_7471_(position, false);
            }
        }
    }

    private void tick(TickEvent.ServerTickEvent event) {
        if (event.phase != TickEvent.Phase.END || ran || ++ticks < 5) return;
        ran = true;
        Map<String, Object> report = new LinkedHashMap<>();
        try {
            try {
                ResourceLocation.class.getDeclaredMethod("fromNamespaceAndPath", String.class, String.class);
                report.put("resourceLocationFromNamespaceAndPath", true);
            } catch (NoSuchMethodException missing) {
                report.put("resourceLocationFromNamespaceAndPath", false);
            }
            ServerLevel level = event.getServer().m_129783_();
            var wheel = wheelPattern();
            check(contents(wheel.stream().map(s -> s.stack).toList()).equals(Map.of("create:andesite_alloy", 16, "minecraft:oak_planks", 4, "minecraft:stone", 1)), "21 ingredient crushing-wheel fixture");
            var single = repack(level, "wheel5x5-single", wheel, 1);
            unpack(level, "wheel5x5-single", wheel, single.get(0), 5, 0);
            var batch = repack(level, "wheel5x5-batch2", wheel, 2);
            for (int i = 0; i < batch.size(); i++) unpack(level, "wheel5x5-batch2-" + i, wheel, batch.get(i), 5, 8);
            var chest = chestPattern();
            var small = repack(level, "chest3x3-regression", chest, 1);
            unpack(level, "chest3x3-regression", chest, small.get(0), 3, 16);
            report.put("passed", true);
            System.out.println("FACTORY_CONTROLLER_PROBE_OK " + passed);
        } catch (Throwable error) {
            report.put("passed", false);
            report.put("error", error.toString());
            System.out.println("FACTORY_CONTROLLER_PROBE_FAILED " + error);
            error.printStackTrace();
        } finally {
            report.put("checks", passed);
            try {
                Path output = Path.of(System.getProperty("expedition.factorycontroller.probe.result", "factorycontroller-probe-result.json"));
                Files.writeString(output, new GsonBuilder().setPrettyPrinting().create().toJson(report) + "\n");
            } catch (Exception error) { error.printStackTrace(); }
        }
    }
}
