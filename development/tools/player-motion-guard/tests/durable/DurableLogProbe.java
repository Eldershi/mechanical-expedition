import com.google.gson.Gson;
import expedition.motionguard.diagnostics.*;
import java.nio.file.*;
import java.util.*;

/** Real FileChannel writer subprocess used by the SIGKILL verifier. */
public final class DurableLogProbe {
    public static void main(String[] args) throws Exception {
        Path root=Path.of(args[0]);String mode=args.length>1?args[1]:"kill";
        DiagnosticsConfig config=new DiagnosticsConfig();config.queueCapacity=64;config.flushIntervalMillis=50;
        config.forceIntervalMillis=200;config.eventFileBytes=4096;config.totalLogBytes=16384;config.maxLogFiles=4;
        boolean abandoned=mode.equals("unforcedfailure") || mode.equals("unforcedprefixfailure");
        if(abandoned)config.forceIntervalMillis=60000;
        DurableJsonLog writer=new DurableJsonLog(root,config,UUID.randomUUID().toString());
        if(abandoned) {
            await(writer,"forceCount",1);
            long prefix=mode.equals("unforcedprefixfailure")?1:0;
            if(prefix!=0) {
                writer.offer("confirmed_prefix",Map.of("value",1));writer.requestForce();
                await(writer,"lastContiguousForcedSequence",prefix);
            }
            String previousFile=(String)writer.status().get("lastForcedFile");
            writer.offer("unforced_old_file",Map.of("value",prefix+1));
            await(writer,"lastProcessedSequence",prefix+1);
            if(value(writer.status(),"lastForcedSequence")!=prefix)throw new AssertionError("old data unexpectedly forced");
            var field=DurableJsonLog.class.getDeclaredField("channel");field.setAccessible(true);
            ((java.nio.channels.FileChannel)field.get(writer)).close();
            writer.offer("failed_old_file",Map.of("value",prefix+2));
            await(writer,"lastProcessedSequence",prefix+2);
            writer.requestForce();await(writer,"lastForceRequestProcessedSequence",prefix+2);
            Map<String,Object> emptyAck=writer.status();
            if(value(emptyAck,"lastForcedSequence")!=prefix
                    || value(emptyAck,"lastContiguousForcedSequence")!=prefix
                    || value(emptyAck,"firstLostSequence")!=prefix+2
                    || value(emptyAck,"firstUnconfirmedClosedFileSequence")!=prefix+1
                    || value(emptyAck,"unconfirmedClosedFileRecords")!=1
                    || !previousFile.equals(emptyAck.get("lastForcedFile")))
                throw new AssertionError("empty new file acknowledged abandoned prefix: "+emptyAck);
            Map<?,?> receipt=new Gson().fromJson(Files.readString(root.resolve("state.json")),Map.class);
            if(((Number)receipt.get("lastForcedSequence")).longValue()!=prefix
                    || ((Number)receipt.get("lastContiguousForcedSequence")).longValue()!=prefix
                    || !previousFile.equals(receipt.get("lastForcedFile")))throw new AssertionError("false disk receipt: "+receipt);
            System.out.println("EMPTY_FILE_ACK "+new Gson().toJson(emptyAck));
            writer.offer("new_file_after_failure",Map.of("value",prefix+3));
        } else if(mode.equals("writefailure")) {
            writer.offer("before_failure",Map.of("value",1));
            long until=System.nanoTime()+3_000_000_000L;
            while(((Number)writer.status().get("lastContiguousForcedSequence")).longValue()<1 && System.nanoTime()<until)Thread.sleep(10);
            var field=DurableJsonLog.class.getDeclaredField("channel");field.setAccessible(true);
            ((java.nio.channels.FileChannel)field.get(writer)).close();
            writer.offer("closed_channel_failure",Map.of("value",2));
            until=System.nanoTime()+3_000_000_000L;
            while(((Number)writer.status().get("lastProcessedSequence")).longValue()<2 && System.nanoTime()<until)Thread.sleep(10);
            writer.offer("after_failure",Map.of("value",3));
        } else if(mode.equals("receiptfailure")) {
            Files.createDirectory(root.resolve("state.json"));
            writer.offer("data_without_receipt",Map.of("value",1));
            long until=System.nanoTime()+3_000_000_000L;
            while(((Number)writer.status().get("markerFailures")).longValue()==0 && System.nanoTime()<until)Thread.sleep(10);
            if(((Number)writer.status().get("lastForcedSequence")).longValue()!=0)throw new AssertionError("false receipt ACK");
            System.out.println("FAILURE_BLOCKED "+new Gson().toJson(writer.status()));
            Files.delete(root.resolve("state.json"));
        } else if(mode.equals("rotation")) {
            for(int i=0;i<250;i++){writer.offer("bounded",Map.of("index",i,"text","x".repeat(500)));Thread.sleep(1);}
        } else if(mode.equals("oversize")) {
            writer.offer("valid",Map.of("value",1));
            if(writer.offer("oversize",Map.of("value","x".repeat(40000))))throw new AssertionError("oversize admitted");
            writer.offer("after_oversize",Map.of("value",2));
        } else {
            for(int i=0;i<12;i++)writer.offer("state",Map.of("index",i,"number",i==0?Double.NaN:(double)i));
        }
        long target=writer.requestForce(),deadline=System.nanoTime()+5_000_000_000L;
        while(System.nanoTime()<deadline) {
            Map<String,Object> status=writer.status();
            boolean confirmed=mode.equals("writefailure") || abandoned
                    ? ((Number)status.get("lastForceRequestProcessedSequence")).longValue()>=target
                    : ((Number)status.get("lastContiguousForcedSequence")).longValue()>=target;
            if(confirmed
                    && ((Number)status.get("forceCount")).longValue()>0) {
                if(mode.equals("writefailure") && (((Number)status.get("firstLostSequence")).longValue()!=2
                        || ((Number)status.get("lastContiguousForcedSequence")).longValue()!=1
                        || ((Number)status.get("lastForcedSequence")).longValue()!=3))throw new AssertionError("lost record acknowledged");
                if(abandoned) {
                    long prefix=mode.equals("unforcedprefixfailure")?1:0;
                    if(value(status,"lastForcedSequence")!=prefix+3
                            || value(status,"lastContiguousForcedSequence")!=prefix
                            || value(status,"firstLostSequence")!=prefix+2
                            || value(status,"firstUnconfirmedClosedFileSequence")!=prefix+1)
                        throw new AssertionError("new successful record concealed unforced old file: "+status);
                }
                System.out.println("FORCED_ACK "+new Gson().toJson(status));System.out.flush();
                if(mode.equals("kill")||mode.equals("recover")) {while(true)Thread.sleep(1000);}
                writer.close();System.out.println("COMPLETE "+new Gson().toJson(writer.status()));return;
            }
            Thread.sleep(10);
        }
        writer.close();throw new AssertionError("No forced acknowledgement: "+writer.status());
    }
    private static long value(Map<String,Object> status,String key) {return ((Number)status.get(key)).longValue();}
    private static void await(DurableJsonLog writer,String key,long target) throws Exception {
        long deadline=System.nanoTime()+3_000_000_000L;
        while(value(writer.status(),key)<target && System.nanoTime()<deadline)Thread.sleep(10);
        if(value(writer.status(),key)<target)throw new AssertionError("No "+key+" >= "+target+": "+writer.status());
    }
}
