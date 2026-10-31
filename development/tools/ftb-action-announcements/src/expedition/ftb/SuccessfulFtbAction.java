package expedition.ftb;
import com.mojang.brigadier.Command;
import com.mojang.brigadier.ParseResults;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.context.CommandContextBuilder;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import java.util.function.BiConsumer;
import java.util.function.Predicate;

/** Observe four exact FTB sidebar command leaves after their original execution. */
public final class SuccessfulFtbAction {
    public enum Action { GAMEMODE, RAIN, DAY, NIGHT }
    public record State(String identity, String description) {}
    @FunctionalInterface public interface Snapshot<S> { State capture(S source, Action action); }
    private SuccessfulFtbAction() {}
    public static <S> boolean observe(ParseResults<S> parse, Predicate<S> allowed,
            Snapshot<S> snapshot, BiConsumer<S,State> broadcast) {
        CommandContextBuilder<S> builder=parse.getContext();
        if (parse.getReader().canRead() || !parse.getExceptions().isEmpty() || builder.getChild()!=null
                || builder.getNodes().size()!=2 || !builder.getArguments().isEmpty()
                || builder.getCommand()==null || builder.getCommand() instanceof ObservedCommand<?>
                || !allowed.test(builder.getSource())) return false;
        if (!builder.getNodes().get(0).getNode().getName().equals("ftblibrary")) return false;
        Action action=switch(builder.getNodes().get(1).getNode().getName()) {
            case "gamemode" -> Action.GAMEMODE;
            case "rain" -> Action.RAIN;
            case "day" -> Action.DAY;
            case "night" -> Action.NIGHT;
            default -> null;
        };
        if (action==null) return false;
        builder.withCommand(new ObservedCommand<>(builder.getCommand(),action,snapshot,broadcast));
        return true;
    }
    private record ObservedCommand<S>(Command<S> original,Action action,Snapshot<S> snapshot,
            BiConsumer<S,State> broadcast) implements Command<S> {
        public int run(CommandContext<S> context) throws CommandSyntaxException {
            S source=context.getSource();
            State before=snapshot.capture(source,action);
            int result=original.run(context);
            State after=snapshot.capture(source,action);
            if(result>0 && !before.identity().equals(after.identity())) broadcast.accept(source,after);
            return result;
        }
    }
}
