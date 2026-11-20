package expedition.backup.mixin;

import de.melanx.simplebackups.BackupThread;
import de.melanx.simplebackups.config.BackupType;
import de.melanx.simplebackups.config.CommonConfig;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.util.Comparator;
import java.util.regex.Pattern;
import java.util.zip.CRC32;
import java.util.zip.CheckedInputStream;
import java.util.zip.ZipFile;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

@Mixin(value = BackupThread.class, remap = false)
abstract class BackupThreadMixin {
    @Unique
    private static final String EXPEDITION_ARCHIVE_DATE =
        "\\d{4}-\\d{2}-\\d{2}_\\d{2}-\\d{2}-\\d{2}(?: \\(\\d+\\))?\\.zip";

    @Redirect(method = "run", at = @At(value = "INVOKE",
        target = "Lde/melanx/simplebackups/BackupThread;deleteFiles()V"))
    private void expedition$deferFullBackupCleanup(BackupThread backup) {
        if (CommonConfig.backupType() != BackupType.FULL_BACKUPS) backup.deleteFiles();
    }

    @Redirect(method = "run", at = @At(value = "INVOKE",
        target = "Lde/melanx/simplebackups/BackupThread;saveStorageSize()V"))
    private void expedition$preserveLastFullBackup(BackupThread backup) {
        if (CommonConfig.backupType() != BackupType.FULL_BACKUPS) backup.saveStorageSize();
    }

    @Redirect(method = "makeWorldBackup", at = @At(value = "INVOKE",
        target = "Ljava/nio/file/Files;size(Ljava/nio/file/Path;)J"))
    private long expedition$rotateVerifiedFullBackup(Path archive) throws IOException {
        long size = Files.size(archive);
        if (CommonConfig.backupType() == BackupType.FULL_BACKUPS && size > 0) {
            try {
                expedition$prune(archive);
            } catch (IOException problem) {
                BackupThread.LOGGER.warn("Could not finish rotating full world backups", problem);
            }
        }
        return size;
    }

    @Unique
    private static void expedition$prune(Path archive) throws IOException {
        var name = archive.getFileName().toString();
        var match = Pattern.compile("^(.+)_" + EXPEDITION_ARCHIVE_DATE + "$").matcher(name);
        if (!match.matches()) return;
        var world = match.group(1);
        if (!expedition$readableWorld(archive, world)) return;
        var sameWorld = Pattern.compile("^" + Pattern.quote(world) + "_" + EXPEDITION_ARCHIVE_DATE + "$");
        try (var paths = Files.list(archive.getParent())) {
            var older = paths.filter(path -> !path.equals(archive))
                .filter(path -> sameWorld.matcher(path.getFileName().toString()).matches())
                .filter(path -> Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS))
                .sorted(Comparator.comparingLong((Path path) -> path.toFile().lastModified()).reversed()
                    .thenComparing(Path::toString))
                .skip(CommonConfig.getBackupsToKeep() - 1L)
                .toList();
            for (var path : older) {
                Files.deleteIfExists(path);
                BackupThread.LOGGER.info("Rotated old world backup after verifying {}", name);
            }
        }
    }

    @Unique
    private static boolean expedition$readableWorld(Path archive, String world) throws IOException {
        try (var zip = new ZipFile(archive.toFile())) {
            var level = zip.getEntry("level.dat");
            if (level == null) level = zip.getEntry(world + "/level.dat");
            if (level == null || level.isDirectory()) return false;
            try (var input = new CheckedInputStream(zip.getInputStream(level), new CRC32())) {
                return input.transferTo(OutputStream.nullOutputStream()) == level.getSize()
                    && input.getChecksum().getValue() == level.getCrc();
            }
        }
    }
}
