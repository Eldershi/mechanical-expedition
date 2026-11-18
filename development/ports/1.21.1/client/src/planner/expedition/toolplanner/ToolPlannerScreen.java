package expedition.toolplanner;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import modernmods.modernfoundry.library.client.materials.MaterialRenderInfoLoader;
import modernmods.modernfoundry.library.client.materials.MaterialTooltipCache;
import modernmods.modernfoundry.library.materials.MaterialRegistry;
import modernmods.modernfoundry.library.materials.definition.IMaterial;
import modernmods.modernfoundry.library.materials.definition.MaterialVariant;
import modernmods.modernfoundry.library.materials.definition.MaterialVariantId;
import modernmods.modernfoundry.library.materials.stats.MaterialStatsId;
import modernmods.modernfoundry.library.tools.definition.ToolDefinition;
import modernmods.modernfoundry.library.tools.definition.module.material.ToolMaterialHook;
import modernmods.modernfoundry.library.tools.definition.module.material.ToolPartsHook;
import modernmods.modernfoundry.library.tools.item.IModifiable;
import modernmods.modernfoundry.library.tools.nbt.MaterialNBT;
import modernmods.modernfoundry.library.tools.nbt.StatsNBT;
import modernmods.modernfoundry.library.tools.nbt.ToolStack;
import modernmods.modernfoundry.library.tools.part.IToolPart;
import modernmods.modernfoundry.library.tools.stat.IToolStat;
import modernmods.modernfoundry.tables.client.inventory.TinkerStationScreen;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.CommonComponents;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;

public final class ToolPlannerScreen extends Screen {
    private record Tool(Item item, ToolDefinition definition, List<MaterialStatsId> stats,
                        List<IToolPart> parts) {
        Component name() {
            return Component.translatable(item.getDescriptionId());
        }
    }

    private final TinkerStationScreen station;
    private final List<Tool> tools;
    private final Set<MaterialVariantId> materials = new LinkedHashSet<>();
    private final List<List<MaterialVariantId>> choices = new ArrayList<>();
    private final List<MaterialVariantId> selected = new ArrayList<>();
    private Tool tool;
    private ItemStack preview = ItemStack.EMPTY;
    private List<Component> previewStats = List.of();

    public ToolPlannerScreen(TinkerStationScreen station) {
        super(Component.translatable("expedition.planner.title"));
        this.station = station;
        tools = BuiltInRegistries.ITEM.stream().filter(IModifiable.class::isInstance)
            .map(item -> {
                ToolDefinition definition = IModifiable.getToolDefinition(item);
                return new Tool(item, definition, ToolMaterialHook.stats(definition), ToolPartsHook.parts(definition));
            }).filter(entry -> entry.definition().isDataLoaded() && !entry.stats().isEmpty()).toList();
        MaterialRegistry.getInstance().getVisibleMaterials().stream().sorted()
            .map(IMaterial::getIdentifier).forEach(materials::add);
        MaterialRenderInfoLoader.INSTANCE.getAllRenderInfos().stream()
            .map(info -> info.id().normalizeVariant()).filter(id -> id.hasVariant() && materials.contains(id.getId()))
            .toList().forEach(materials::add);
        ItemStack stationItem = station.getCurrentLayout().getIcon().getValue(ItemStack.class);
        if (!tools.isEmpty()) {
            setTool(tools.stream().filter(entry -> stationItem != null && stationItem.is(entry.item()))
                .findFirst().orElse(tools.getFirst()));
        }
    }

    private void setTool(Tool next) {
        tool = next;
        selected.clear();
        choices.clear();
        for (int index = 0; index < tool.stats().size(); index++) {
            MaterialStatsId stat = tool.stats().get(index);
            IToolPart part = index < tool.parts().size() ? tool.parts().get(index) : null;
            List<MaterialVariantId> accepted = materials.stream().filter(material -> part != null
                ? part.canUseMaterial(material.getId())
                : MaterialRegistry.getInstance().getMaterialStats(material.getId(), stat).isPresent()).toList();
            choices.add(accepted);
            selected.add(accepted.isEmpty() ? null : accepted.getFirst());
        }
        updatePreview();
    }

    private void updatePreview() {
        preview = ItemStack.EMPTY;
        previewStats = List.of();
        if (selected.contains(null)) return;
        MaterialNBT parts = new MaterialNBT(selected.stream().map(MaterialVariant::of).toList());
        ToolStack assembled = ToolStack.createTool(tool.item(), tool.definition(), parts);
        preview = assembled.createStack();
        List<Component> lines = new ArrayList<>();
        lines.add(preview.getHoverName());
        StatsNBT stats = assembled.getStats();
        stats.getContainedStats().stream().sorted(Comparator.comparing(stat -> stat.getName().toString()))
            .map(stat -> statLine(stats, stat)).forEach(lines::add);
        assembled.getModifiers().forEach(modifier -> lines.add(modifier.getDisplayName()));
        previewStats = List.copyOf(lines);
    }

    private static <T> Component statLine(StatsNBT stats, IToolStat<T> stat) {
        return stat.formatValue(stats.get(stat));
    }

    @Override
    protected void init() {
        int controlsWidth = Math.min(width - 28, 330);
        int left = (width - controlsWidth) / 2;
        addRenderableWidget(Button.builder(CommonComponents.GUI_BACK, button -> onClose())
            .bounds(width / 2 - 55, height - 28, 110, 20).build());
        if (tool == null) return;
        addRenderableWidget(Button.builder(Component.translatable("expedition.planner.tool", tool.name()),
            button -> openTools()).bounds(left, 29, controlsWidth, 20).build());
        addRenderableWidget(Button.builder(Component.translatable("expedition.planner.materials"),
            button -> openParts()).bounds(left, 55, controlsWidth, 20).build());
    }

    private void openTools() {
        List<ChoiceScreen.Option> options = tools.stream().map(entry -> new ChoiceScreen.Option(entry.name(),
            BuiltInRegistries.ITEM.getKey(entry.item()).toString(), () -> {
                setTool(entry);
                minecraft.setScreen(this);
            })).toList();
        minecraft.setScreen(new ChoiceScreen(this, Component.translatable("expedition.planner.choose_tool"), options));
    }

    private Component partName(int index) {
        if (index < tool.parts().size()) {
            return Component.translatable(tool.parts().get(index).asItem().getDescriptionId());
        }
        return Component.translatable("expedition.planner.part", index + 1);
    }

    private void openParts() {
        List<ChoiceScreen.Option> options = new ArrayList<>();
        for (int index = 0; index < selected.size(); index++) {
            int slot = index;
            MaterialVariantId material = selected.get(index);
            Component label = Component.translatable("expedition.planner.slot", index + 1, partName(index),
                material == null ? Component.translatable("expedition.planner.no_material")
                    : MaterialTooltipCache.getDisplayName(material));
            options.add(new ChoiceScreen.Option(label, tool.stats().get(index).toString(), () -> openMaterials(slot)));
        }
        minecraft.setScreen(new ChoiceScreen(this, Component.translatable("expedition.planner.materials"), options));
    }

    private void openMaterials(int index) {
        Screen partsScreen = minecraft.screen;
        List<ChoiceScreen.Option> options = choices.get(index).stream().map(material -> new ChoiceScreen.Option(
            MaterialTooltipCache.getDisplayName(material), material.toString(), () -> {
                selected.set(index, material);
                updatePreview();
                minecraft.setScreen(this);
            })).toList();
        minecraft.setScreen(new ChoiceScreen(partsScreen, partName(index), options));
    }

    @Override
    public void render(GuiGraphics graphics, int mouseX, int mouseY, float partialTick) {
        super.render(graphics, mouseX, mouseY, partialTick);
        graphics.drawCenteredString(font, title, width / 2, 12, 0xFFFFFF);
        int x = width / 2 - 8;
        int y = 85;
        if (preview.isEmpty()) {
            graphics.drawCenteredString(font, Component.translatable("expedition.planner.unavailable"),
                width / 2, y + 5, 0xA0A0A0);
            return;
        }
        graphics.fill(x - 2, y - 2, x + 18, y + 18, 0xCC323232);
        graphics.renderItem(preview, x, y);
        graphics.drawCenteredString(font, Component.translatable("expedition.planner.hover_stats"),
            width / 2, y + 23, 0xD0D0D0);
        if (mouseX >= x - 2 && mouseX < x + 18 && mouseY >= y - 2 && mouseY < y + 18) {
            graphics.renderTooltip(font, previewStats, java.util.Optional.empty(), mouseX, mouseY);
        }
    }

    @Override
    public boolean isPauseScreen() {
        return false;
    }

    @Override
    public void onClose() {
        minecraft.setScreen(minecraft.player != null && minecraft.player.containerMenu == station.getMenu()
            ? station : null);
    }
}
