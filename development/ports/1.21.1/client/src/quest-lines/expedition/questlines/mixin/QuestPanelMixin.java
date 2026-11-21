package expedition.questlines.mixin;

import org.spongepowered.asm.mixin.Mixin;

@Mixin(targets = "dev.ftb.mods.ftbquests.client.gui.quests.QuestPanel", priority = 500, remap = false)
abstract class QuestPanelMixin {
}
