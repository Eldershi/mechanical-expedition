package expedition.ftbteamscompat.mixin;

import dev.ftb.mods.ftbteams.api.client.KnownClientPlayer;
import java.util.Comparator;
import java.util.stream.Stream;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

@Mixin(targets = "dev.ftb.mods.ftbteams.client.gui.CreatePartyScreen$InvitePanel", remap = false)
abstract class InvitationSortMixin {
    @Redirect(method = "addWidgets()V",
        at = @At(value = "INVOKE", target = "Ljava/util/stream/Stream;sorted()Ljava/util/stream/Stream;"),
        require = 1, allow = 1)
    private Stream<KnownClientPlayer> expedition$sortInvitations(Stream<KnownClientPlayer> players) {
        return players.sorted(Comparator.comparing(KnownClientPlayer::name, String.CASE_INSENSITIVE_ORDER)
            .thenComparing(KnownClientPlayer::id));
    }
}
