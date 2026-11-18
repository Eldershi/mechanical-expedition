package expedition.ftb;

import net.minecraft.commands.CommandSourceStack;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.storage.LevelData;
import net.neoforged.bus.api.EventPriority;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.CommandEvent;

@Mod(FtbActionAnnouncements.MOD_ID)
public final class FtbActionAnnouncements {
    public static final String MOD_ID = "expedition_ftb_action_announcements";

    public FtbActionAnnouncements() {
        NeoForge.EVENT_BUS.addListener(
            EventPriority.LOWEST, false, CommandEvent.class, FtbActionAnnouncements::onCommand
        );
    }

    private static void onCommand(CommandEvent event) {
        if (event.isCanceled()) {
            return;
        }
        SuccessfulFtbAction.observe(
            event.getParseResults(),
            source -> source.getEntity() instanceof ServerPlayer && source.hasPermission(2),
            FtbActionAnnouncements::snapshot,
            (source, state) -> source.getServer().getPlayerList().broadcastSystemMessage(
                Component.literal("[FTB操作] " + source.getTextName() + " " + state.description()), false
            )
        );
    }

    private static SuccessfulFtbAction.State snapshot(
        CommandSourceStack source, SuccessfulFtbAction.Action action
    ) {
        ServerLevel level = source.getLevel();
        switch (action) {
            case GAMEMODE -> {
                boolean creative = ((ServerPlayer) source.getEntity()).isCreative();
                return new SuccessfulFtbAction.State(
                    Boolean.toString(creative), "将自己的游戏模式切换为" + (creative ? "创造模式。" : "生存模式。")
                );
            }
            case RAIN -> {
                LevelData data = level.getLevelData();
                boolean rain = data.isRaining();
                boolean thunder = data.isThundering();
                String weather = thunder ? "雷雨" : rain ? "雨天" : "晴天";
                return new SuccessfulFtbAction.State(
                    rain + ":" + thunder, "将 " + level.dimension().location() + " 的天气切换为" + weather + "。"
                );
            }
            default -> {
                long time = level.getDayTime();
                long clock = Math.floorMod(time, 24000L);
                return new SuccessfulFtbAction.State(
                    Long.toString(time), "将服务器时间切换为" + (clock < 12000 ? "白天" : "夜晚") + "（" + clock + " 刻）。"
                );
            }
        }
    }
}
