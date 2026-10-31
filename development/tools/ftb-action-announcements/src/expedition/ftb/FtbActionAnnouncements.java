package expedition.ftb;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.storage.LevelData;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.CommandEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.fml.common.Mod;

/** Server-only announcements; no command replacement, gamerule change, packet, or mixin. */
@Mod(FtbActionAnnouncements.MOD_ID)
public final class FtbActionAnnouncements {
    public static final String MOD_ID="expedition_ftb_action_announcements";
    public FtbActionAnnouncements() {
        MinecraftForge.EVENT_BUS.addListener(EventPriority.LOWEST,false,CommandEvent.class,FtbActionAnnouncements::onCommand);
    }
    private static void onCommand(CommandEvent event) {
        if(event.isCanceled()) return;
        SuccessfulFtbAction.observe(event.getParseResults(),
            source -> source.m_81373_() instanceof ServerPlayer && source.m_6761_(2),
            FtbActionAnnouncements::snapshot,
            (source,state) -> source.m_81377_().m_6846_().m_240416_(
                Component.m_237113_("[FTB操作] "+source.m_81368_()+" "+state.description()),false));
    }
    private static SuccessfulFtbAction.State snapshot(CommandSourceStack source,SuccessfulFtbAction.Action action) {
        ServerLevel level=source.m_81372_();
        if(action==SuccessfulFtbAction.Action.GAMEMODE) {
            boolean creative=((ServerPlayer)source.m_81373_()).m_7500_();
            return new SuccessfulFtbAction.State(Boolean.toString(creative),
                "将自己的游戏模式切换为"+(creative?"创造模式。":"生存模式。"));
        }
        if(action==SuccessfulFtbAction.Action.RAIN) {
            // isRaining() is interpolated; persistent flags update immediately.
            LevelData data=level.m_6106_();
            boolean rain=data.m_6533_(),thunder=data.m_6534_();
            String dimension=level.m_46472_().m_135782_().toString();
            return new SuccessfulFtbAction.State(rain+":"+thunder,
                "将 "+dimension+" 的天气切换为"+(thunder?"雷雨":rain?"雨天":"晴天")+"。");
        }
        long time=level.m_46468_(),clock=Math.floorMod(time,24000L);
        return new SuccessfulFtbAction.State(Long.toString(time),
            "将服务器时间切换为"+(clock<12000?"白天":"夜晚")+"（"+clock+" 刻）。");
    }
}
