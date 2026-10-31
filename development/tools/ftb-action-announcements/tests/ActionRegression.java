import com.mojang.brigadier.*;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.exceptions.*;
import expedition.ftb.SuccessfulFtbAction;
import java.util.*;

/** Actual Brigadier parsing/authorization/callbacks with isolated world state. */
public final class ActionRegression {
    static final class Source {
        int permission=2,calls,result=1;
        boolean player=true,rain,visualRain,creative;
        long time;
        CommandSyntaxException failure;
        final List<String> announcements=new ArrayList<>();
    }
    private static int assertions;
    private static void check(boolean value,String message) { assertions++;if(!value)throw new AssertionError(message); }
    private static LiteralArgumentBuilder<Source> literal(String name) {return LiteralArgumentBuilder.literal(name);}
    private static CommandDispatcher<Source> dispatcher() {
        CommandDispatcher<Source> dispatcher=new CommandDispatcher<>();
        LiteralArgumentBuilder<Source> root=literal("ftblibrary").requires(s->s.permission>=2);
        for(String action:List.of("gamemode","rain","day","night","nbtedit","clientconfig"))
            root.then(literal(action).executes(context->{
                Source s=context.getSource();s.calls++;
                if(s.failure!=null)throw s.failure;
                switch(action) {
                    case "gamemode" -> s.creative=!s.creative;
                    case "rain" -> s.rain=!s.visualRain;
                    case "day","night" -> s.time+=Math.floorMod(24000-s.time%24000+(action.equals("day")?6000:18000),24000);
                }
                return s.result;
            }));
        dispatcher.register(root);
        dispatcher.register(literal("gamemode").executes(c->{c.getSource().creative=true;c.getSource().calls++;return 1;}));
        dispatcher.register(literal("msg").then(com.mojang.brigadier.builder.RequiredArgumentBuilder.<Source,String>argument("private",com.mojang.brigadier.arguments.StringArgumentType.greedyString()).executes(c->{c.getSource().calls++;return 1;})));
        return dispatcher;
    }
    private static boolean observe(ParseResults<Source> parse) {
        return SuccessfulFtbAction.observe(parse,s->s.player&&s.permission>=2,
            (s,a)->switch(a) {
                case GAMEMODE -> new SuccessfulFtbAction.State(""+s.creative,"mode="+s.creative);
                case RAIN -> new SuccessfulFtbAction.State(""+s.rain,"rain="+s.rain);
                case DAY,NIGHT -> new SuccessfulFtbAction.State(""+s.time,"time="+s.time);
            },(s,state)->s.announcements.add("Actor: "+state.description()));
    }
    public static void main(String[] args)throws Exception {
        CommandDispatcher<Source> dispatcher=dispatcher();
        int[] completed={0};dispatcher.setConsumer((context,success,result)->completed[0]++);
        for(String action:List.of("gamemode","rain","day","night")) {
            Source s=new Source();ParseResults<Source> parse=dispatcher.parse("ftblibrary "+action,s);
            check(observe(parse),"Allowed FTB action observed");
            check(!observe(parse),"Same parse not wrapped twice");
            int before=completed[0];
            check(dispatcher.execute(parse)==1,"Original result preserved");
            check(s.calls==1&&s.announcements.size()==1,"One execution, one broadcast");
            check(completed[0]==before+1,"Original result consumer preserved");
        }
        Source day=new Source();day.time=6000;
        ParseResults<Source> noop=dispatcher.parse("ftblibrary day",day);observe(noop);dispatcher.execute(noop);
        check(day.calls==1&&day.announcements.isEmpty(),"Already-day no-op silent");
        Source transition=new Source();transition.rain=true;transition.visualRain=false;
        ParseResults<Source> repeat=dispatcher.parse("ftblibrary rain",transition);observe(repeat);dispatcher.execute(repeat);
        check(transition.announcements.isEmpty(),"Rain interpolation repeat silent");
        Source failed=new Source();failed.failure=new SimpleCommandExceptionType(new LiteralMessage("original failure")).create();
        ParseResults<Source> failure=dispatcher.parse("ftblibrary day",failed);observe(failure);
        try{dispatcher.execute(failure);throw new AssertionError("Exception lost");}
        catch(CommandSyntaxException e){check(e==failed.failure,"Original exception identity preserved");}
        check(failed.announcements.isEmpty(),"Failure silent");
        Source zero=new Source();zero.result=0;
        ParseResults<Source> zeroParse=dispatcher.parse("ftblibrary night",zero);observe(zeroParse);
        check(dispatcher.execute(zeroParse)==0&&zero.announcements.isEmpty(),"Zero result preserved/silent");
        Source denied=new Source();denied.permission=0;
        ParseResults<Source> unauthorized=dispatcher.parse("ftblibrary rain",denied);
        check(!observe(unauthorized),"Unauthorized parse untouched");
        try{dispatcher.execute(unauthorized);}catch(CommandSyntaxException expected){}
        check(denied.calls==0&&denied.announcements.isEmpty(),"OP gate preserved");
        for(String input:List.of("ftblibrary nbtedit","ftblibrary clientconfig","gamemode","msg Secret message","ftblibrary day extra")) {
            Source other=new Source();ParseResults<Source> parse=dispatcher.parse(input,other);
            check(!observe(parse),"Unrelated/malformed untouched: "+input);
            check(other.announcements.isEmpty(),"Private/unrelated never broadcast");
        }
        Source console=new Source();console.player=false;
        check(!observe(dispatcher.parse("ftblibrary day",console)),"Non-player outside sidebar scope");
        System.out.println("BRIGADIER_ACTION_REGRESSION_OK: "+assertions+" assertions; success exactly once; no-op/failure/unauthorized/private/unrelated silent; original callbacks and exceptions preserved");
    }
}
