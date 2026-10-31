import java.lang.invoke.MethodHandle;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.MethodType;
import java.util.List;
import net.minecraft.core.BlockPos;

public final class QueueStubTest {
    public static void main(String[] args) throws Throwable {
        String prefix = args[1];
        Class<?> type = Class.forName(args[0]);
        Object chunk = type.getConstructor().newInstance();
        var getter = type.getMethod(prefix + "$getScheduledRandomTicks");
        Object queue = getter.invoke(chunk);
        if (!(queue instanceof List<?>) || !((List<?>) queue).isEmpty()) throw new AssertionError("Queue not empty");
        MethodHandle schedule = MethodHandles.publicLookup().findVirtual(type, prefix + "$scheduleRandomTick",
                MethodType.methodType(void.class, BlockPos.class)).bindTo(chunk);
        BlockPos position = new BlockPos();
        for (int i = 0; i < 1_000_000; i++) schedule.invokeExact(position);
        schedule.invokeExact((BlockPos) null);
        if (queue != getter.invoke(chunk)) throw new AssertionError("Getter identity changed");
        if (!((List<?>) queue).isEmpty()) throw new AssertionError("Queue grew");
        if (BlockPos.immutableCalls != 0) throw new AssertionError("Scheduler still allocates positions");
        System.out.println("QUEUE_STUB_OK " + args[0]
                + "; scheduleCalls=1000001; queueSize=0; immutableCopies=0; getterIdentityPreserved=true");
    }
}
