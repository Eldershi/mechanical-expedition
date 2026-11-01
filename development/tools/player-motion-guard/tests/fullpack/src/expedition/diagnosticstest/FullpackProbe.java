package expedition.diagnosticstest;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import java.util.Map;
import java.util.concurrent.locks.LockSupport;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.common.util.FakePlayerFactory;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.server.ServerLifecycleHooks;

/** Test-only command used exclusively in a disposable loopback server. */
@Mod("expedition_diagnostics_test")
public final class FullpackProbe {
    public FullpackProbe() { MinecraftForge.EVENT_BUS.addListener(this::commands); }
    private void commands(RegisterCommandsEvent event) {
        event.getDispatcher().register(LiteralArgumentBuilder.<CommandSourceStack>literal("monitorprobe")
            .requires(source -> source.m_6761_(4))
            .then(LiteralArgumentBuilder.<CommandSourceStack>literal("integrations").executes(context -> {
                try { integrations(); System.out.println("MONITOR_RUNTIME_INTEGRATIONS_PASS"); return 1; }
                catch(Exception problem) {
                    System.out.println("MONITOR_RUNTIME_INTEGRATIONS_FAIL"); problem.printStackTrace(); return 0;
                }
            }))
            .then(LiteralArgumentBuilder.<CommandSourceStack>literal("stall").executes(context -> {
                System.out.println("MONITOR_RUNTIME_STALL_BEGIN");
                long until=System.nanoTime()+15_000_000_000L;
                while(System.nanoTime()<until) LockSupport.parkNanos(until-System.nanoTime());
                System.out.println("MONITOR_RUNTIME_STALL_END");
                return 1;
            })));
    }
    private void integrations() throws Exception {
        ServerPlayer player=FakePlayerFactory.getMinecraft(ServerLifecycleHooks.getCurrentServer().m_129783_());
        Class<?> captureClass=Class.forName("expedition.motionguard.diagnostics.EquipmentCapture");
        Object capture=captureClass.getConstructor().newInstance();
        @SuppressWarnings("unchecked")
        EntityDataAccessor<CompoundTag> key=(EntityDataAccessor<CompoundTag>)Class.forName(
            "tschipp.carryon.common.carry.CarryOnDataManager").getField("CARRY_DATA_KEY").get(null);
        CompoundTag previous=player.m_20088_().m_135370_(key), carried=new CompoundTag(), block=new CompoundTag();
        carried.m_128359_("type","BLOCK"); block.m_128359_("Name","minecraft:copper_ore");
        carried.m_128365_("block",block); player.m_20088_().m_135381_(key,carried);
        try {
            Map<?,?> result=(Map<?,?>)captureClass.getMethod("capture",ServerPlayer.class).invoke(capture,player);
            if(!(result.get("carryOn") instanceof Map<?,?> state)
                    || !"BLOCK".equals(state.get("type")) || !"minecraft:copper_ore".equals(state.get("contentId"))
                    || !(result.get("curios") instanceof java.util.List<?>))
                throw new IllegalStateException("CarryOn/Curios selected metadata integration failed");
            if(((java.util.concurrent.atomic.AtomicLong)captureClass.getField("errors").get(capture)).get()!=0)
                throw new IllegalStateException("Equipment capture reported errors");
        } finally { player.m_20088_().m_135381_(key,previous); }
    }
}
