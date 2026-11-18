package expedition.choice;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.components.Tooltip;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.CommonComponents;
import net.minecraft.network.chat.Component;

public final class ChoiceScreen extends Screen {
    public record Option(Component label, String id, Runnable select) {}

    private final Screen parent;
    private final List<Option> options;
    private final List<Button> rows = new ArrayList<>();
    private EditBox queryField;
    private Button previous;
    private Button next;
    private List<Option> matches = List.of();
    private String query = "";
    private int page;

    public ChoiceScreen(Screen parent, Component title, List<Option> options) {
        super(title);
        this.parent = parent;
        this.options = options.stream().sorted(
            Comparator.comparing((Option option) -> option.label().getString(), String.CASE_INSENSITIVE_ORDER)
                .thenComparing(Option::id)).toList();
    }

    @Override
    protected void init() {
        int rowWidth = Math.min(width - 22, 330);
        int left = (width - rowWidth) / 2;
        int bottom = height - 28;
        queryField = addRenderableWidget(new EditBox(font, left, 28, rowWidth, 18,
            Component.translatable("expedition.client.search")));
        queryField.setHint(Component.translatable("expedition.client.search"));
        queryField.setValue(query);
        queryField.setResponder(value -> {
            query = value;
            page = 0;
            refresh();
        });
        rows.clear();
        for (int top = 52; top + 20 < bottom; top += 22) {
            int index = rows.size();
            rows.add(addRenderableWidget(Button.builder(CommonComponents.EMPTY,
                button -> matches.get(page * rows.size() + index).select().run())
                .bounds(left, top, rowWidth, 20).build()));
        }
        int center = width / 2;
        previous = addRenderableWidget(Button.builder(Component.literal("‹"), button -> changePage(-1))
            .bounds(center - 100, bottom, 48, 20).build());
        addRenderableWidget(Button.builder(CommonComponents.GUI_BACK, button -> onClose())
            .bounds(center - 40, bottom, 80, 20).build());
        next = addRenderableWidget(Button.builder(Component.literal("›"), button -> changePage(1))
            .bounds(center + 52, bottom, 48, 20).build());
        refresh();
    }

    private void changePage(int delta) {
        page += delta;
        refresh();
    }

    private void refresh() {
        String search = query.strip().toLowerCase(Locale.ROOT);
        matches = options.stream().filter(option -> option.label().getString().toLowerCase(Locale.ROOT)
            .contains(search) || option.id().toLowerCase(Locale.ROOT).contains(search)).toList();
        int size = Math.max(rows.size(), 1);
        page = Math.min(page, Math.max(0, (matches.size() - 1) / size));
        for (int index = 0; index < rows.size(); index++) {
            Button button = rows.get(index);
            int matchIndex = page * size + index;
            boolean visible = matchIndex < matches.size();
            button.visible = visible;
            button.active = visible;
            if (visible) {
                Option option = matches.get(matchIndex);
                button.setMessage(option.label());
                button.setTooltip(Tooltip.create(Component.literal(option.id())));
            }
        }
        previous.active = page > 0;
        next.active = (page + 1) * size < matches.size();
    }

    @Override
    public void render(GuiGraphics graphics, int mouseX, int mouseY, float partialTick) {
        super.render(graphics, mouseX, mouseY, partialTick);
        graphics.drawCenteredString(font, title, width / 2, 12, 0xFFFFFF);
        if (matches.isEmpty()) {
            graphics.drawCenteredString(font, Component.translatable("expedition.client.no_matches"),
                width / 2, 64, 0xA0A0A0);
        }
    }

    @Override
    public boolean isPauseScreen() {
        return false;
    }

    @Override
    public void onClose() {
        minecraft.setScreen(parent);
    }
}
