#!/usr/bin/env bash
# Mechanical Expedition updater. Works with macOS Bash 3.2 and Git for Windows.
# The Git checkout is a cache; player files are never a Git working tree.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="$ROOT/updater/expedition.conf"
STATE="$ROOT/.expedition"
MODE="${1:---apply}"
case "$MODE" in --apply|--check) ;; *) echo "Usage: update.sh [--check|--apply]" >&2; exit 2 ;; esac

say() {
  printf '%s\n' "$*"
  if [ -n "${LOG:-}" ]; then printf '%s\n' "$*" >> "$LOG"; fi
}
fail() { say "[ERROR] $*" >&2; exit 1; }
read_setting() {
  local wanted="$1" file="$2"
  awk -F= -v key="$wanted" '$1 == key {sub(/^[^=]*=/, ""); sub(/\r$/, ""); print; exit}' "$file"
}
sha256_file() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | awk '{print $1}'
  else openssl dgst -sha256 "$1" | awk '{print $NF}'; fi
}
safe_path() {
  local rel="$1" part walk="$ROOT"
  case "$rel" in ""|/*|*\\*|*:*|../*|*/../*|*/..|..|*//*|*$'\t'*|*$'\r'*|*$'\n'*) return 1 ;; esac
  case "$rel" in
    mods/*.jar|config/*|kubejs/*|defaultconfigs/*|resourcepacks/*|hotai/*|ldlib/*|updater/*|LICENSE|License.md|README.md|UPSTREAM.md|SOURCE.json|pack-info.json|icon.png|optional_jvm.txt) ;;
    *) return 1 ;;
  esac
  case "$rel" in kubejs/exported/*|kubejs/logs/*|config/ftbquests/quests/chapters/control*) return 1 ;; esac
  local rest="$rel"
  while [ -n "$rest" ]; do
    part="${rest%%/*}"
    [ "$part" != "." ] || return 1
    walk="$walk/$part"
    [ ! -L "$walk" ] || return 1
    case "$rest" in */*) rest="${rest#*/}" ;; *) rest="" ;; esac
  done
}
valid_remote() {
  case "$1" in https://*) return 0 ;; file://*) [ "${EXPEDITION_ALLOW_LOCAL_TEST:-0}" = "1" ] ;; *) return 1 ;; esac
}

[ -f "$CONFIG" ] || fail "Missing updater/expedition.conf"
PACK_ID="$(read_setting PACK_ID "$CONFIG")"
REMOTE="$(read_setting REMOTE_URL "$CONFIG")"
REF="$(read_setting REF "$CONFIG")"
[ "$PACK_ID" = "mechanical-expedition" ] || fail "Unexpected pack identity"
[ -n "$REMOTE" ] || fail "Release repository is not configured yet. No player files were changed."
valid_remote "$REMOTE" || fail "Expected an HTTPS release repository"
case "$REF" in ""|-*|*[!A-Za-z0-9._/-]*) fail "Invalid release ref" ;; esac
for tool in git curl awk sort cmp; do command -v "$tool" >/dev/null 2>&1 || fail "Missing tool: $tool"; done
[ ! -L "$STATE" ] || fail ".expedition must not be a symlink"
mkdir -p "$STATE/logs" "$STATE/backups"
mkdir "$STATE/update.lock" 2>/dev/null || fail "Another update is running, or update.lock needs checking after an interrupted run."
STAMP="$(date +%Y%m%d-%H%M%S)-$$"
LOG="$STATE/logs/$STAMP.log"
TXN="$STATE/transaction-$STAMP"
BACKUP="$STATE/backups/$STAMP"
APPLYING=0
COMMITTED=0
mkdir -p "$TXN/files" "$BACKUP"
: > "$TXN/applied.tsv"

rollback() {
  local existed rel
  say "[rollback] Restoring this update batch"
  while IFS=$'\t' read -r existed rel; do
    [ -n "$rel" ] || continue
    if [ "$existed" = "1" ] && [ -f "$BACKUP/files/$rel" ]; then
      mkdir -p "$(dirname "$ROOT/$rel")"
      cp -p "$BACKUP/files/$rel" "$ROOT/$rel.rollback-tmp"
      mv -f "$ROOT/$rel.rollback-tmp" "$ROOT/$rel"
    elif [ "$existed" = "0" ]; then
      rm -f "$ROOT/$rel"
    fi
    rm -f "$ROOT/$rel.expedition-tmp"
  done < "$TXN/applied.tsv"
  if [ -f "$BACKUP/previous-state.tsv" ]; then cp -p "$BACKUP/previous-state.tsv" "$STATE/state.tsv"; fi
  if [ -f "$BACKUP/previous-installed.env" ]; then cp -p "$BACKUP/previous-installed.env" "$STATE/installed.env"; fi
}
finish() {
  local rc=$?
  trap - EXIT INT TERM
  if [ "$APPLYING" = "1" ] && [ "$COMMITTED" = "0" ]; then rollback || true; fi
  rm -rf "$STATE/update.lock"
  [ "$COMMITTED" = "0" ] || rm -rf "$TXN"
  exit "$rc"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
say "Mechanical Expedition: checking $REF"
CACHE="$STATE/repository"
[ ! -L "$CACHE" ] || fail "Repository cache must not be a symlink"
if [ ! -d "$CACHE/.git" ]; then git init -q "$CACHE" >> "$LOG" 2>&1; fi
git -C "$CACHE" config core.autocrlf false
git -C "$CACHE" config core.eol lf
git -C "$CACHE" fetch --quiet --depth 1 "$REMOTE" "$REF" >> "$LOG" 2>&1 || fail "Repository download failed. See $LOG"
git -C "$CACHE" -c core.autocrlf=false checkout --quiet --detach --force FETCH_HEAD >> "$LOG" 2>&1 || fail "Cannot prepare the release checkout"
RELEASE="$CACHE/release.env"
[ -f "$RELEASE" ] || fail "This is not an Expedition release repository"
[ "$(read_setting PACK_ID "$RELEASE")" = "$PACK_ID" ] || fail "Remote pack identity mismatch"
for key in MINECRAFT FORGE; do
  [ "$(read_setting "$key" "$RELEASE")" = "$(read_setting "$key" "$CONFIG")" ] || fail "Loader/game change requires a fresh launcher installation"
done
VERSION="$(read_setting VERSION "$RELEASE")"
[ -n "$VERSION" ] || fail "Release version is missing"
[ -f "$CACHE/files.tsv" ] && [ -f "$CACHE/mods.tsv" ] || fail "Release manifests are missing"
[ -z "$(find "$CACHE/pack" -type l -print -quit)" ] || fail "Release contains symlinks"

: > "$TXN/new-state.tsv"
: > "$TXN/desired.tsv"
for manifest in files mods; do
  while IFS=$'\t' read -r hash rel url extra; do
    [ -n "$hash" ] || continue
    [ -z "${extra:-}" ] || fail "Unexpected manifest columns"
    printf '%s' "$hash" | grep -Eq '^[a-f0-9]{64}$' || fail "Invalid SHA-256"
    safe_path "$rel" || fail "Protected or unsafe path: $rel"
    if [ "$manifest" = "mods" ]; then
      case "$rel" in mods/*.jar) ;; *) fail "Invalid mod path" ;; esac
      valid_remote "$url" || fail "Invalid download URL"
    else
      case "$rel" in mods/*) fail "JARs belong in mods.tsv" ;; esac
      [ -f "$CACHE/pack/$rel" ] || fail "Missing release file: $rel"
      [ "$(sha256_file "$CACHE/pack/$rel")" = "$hash" ] || fail "Release file checksum mismatch: $rel"
      url="-"
    fi
    printf '%s\t%s\n' "$hash" "$rel" >> "$TXN/new-state.tsv"
    printf '%s\t%s\t%s\t%s\n' "$manifest" "$hash" "$rel" "$url" >> "$TXN/desired.tsv"
  done < "$CACHE/$manifest.tsv"
done
[ -z "$(cut -f2 "$TXN/new-state.tsv" | sort | uniq -d)" ] || fail "Duplicate managed paths"
[ -f "$STATE/state.tsv" ] || fail "Managed-file baseline is missing. Reinstall the published pack before updating."
sort "$TXN/new-state.tsv" -o "$TXN/new-state.tsv"
: > "$TXN/plan.tsv"

while IFS=$'\t' read -r kind hash rel url; do
  current="-"
  [ ! -e "$ROOT/$rel" ] || [ -f "$ROOT/$rel" ] || fail "Expected a regular file: $rel"
  if [ -f "$ROOT/$rel" ]; then current="$(sha256_file "$ROOT/$rel")"; fi
  [ "$current" != "$hash" ] || continue
  previous="$(awk -F '\t' -v p="$rel" '$2 == p {print $1; exit}' "$STATE/state.tsv")"
  if [ "$current" != "-" ] && { [ -z "$previous" ] || [ "$current" != "$previous" ]; }; then
    fail "Local modification would be overwritten: $rel. Keep your change or restore the published version first."
  fi
  printf '%s\t%s\t%s\t%s\t%s\n' "$kind" "$hash" "$rel" "$url" "$current" >> "$TXN/plan.tsv"
done < "$TXN/desired.tsv"
while IFS=$'\t' read -r previous rel; do
  [ -n "$rel" ] || continue
  safe_path "$rel" || fail "Unsafe old managed path: $rel"
  if awk -F '\t' -v p="$rel" '$2 == p {found=1} END {exit !found}' "$TXN/new-state.tsv"; then continue; fi
  [ -e "$ROOT/$rel" ] || continue
  [ -f "$ROOT/$rel" ] && [ "$(sha256_file "$ROOT/$rel")" = "$previous" ] || fail "Locally modified retired file: $rel"
  printf 'remove\t-\t%s\t-\t%s\n' "$rel" "$previous" >> "$TXN/plan.tsv"
done < "$STATE/state.tsv"
COUNT="$(wc -l < "$TXN/plan.tsv" | tr -d ' ')"
say "Version: $VERSION; changed/removed files: $COUNT"
[ "$MODE" != "--check" ] || { say "Check complete; player files are unchanged."; exit 0; }

# Download and verify every changed file before mutating the installation.
while IFS=$'\t' read -r kind hash rel url previous; do
  [ "$kind" != "remove" ] || continue
  mkdir -p "$(dirname "$TXN/files/$rel")"
  if [ "$kind" = "files" ]; then cp -p "$CACHE/pack/$rel" "$TXN/files/$rel"
  else
    say "Downloading: $rel"
    curl --fail --location --retry 2 --connect-timeout 20 --max-time 300 --output "$TXN/files/$rel" "$url" >> "$LOG" 2>&1 || fail "Download failed: $rel"
  fi
  [ "$(sha256_file "$TXN/files/$rel")" = "$hash" ] || fail "Download checksum mismatch: $rel"
done < "$TXN/plan.tsv"
cp -p "$STATE/state.tsv" "$BACKUP/previous-state.tsv"
if [ -f "$STATE/installed.env" ]; then cp -p "$STATE/installed.env" "$BACKUP/previous-installed.env"; fi
APPLYING=1
APPLIED=0
while IFS=$'\t' read -r kind hash rel url previous; do
  safe_path "$rel" || fail "Path changed during update: $rel"
  if [ "$previous" != "-" ]; then
    [ -f "$ROOT/$rel" ] && [ "$(sha256_file "$ROOT/$rel")" = "$previous" ] || fail "File changed during update: $rel"
    mkdir -p "$(dirname "$BACKUP/files/$rel")"
    cp -p "$ROOT/$rel" "$BACKUP/files/$rel"
    printf '1\t%s\n' "$rel" >> "$TXN/applied.tsv"
  else
    [ ! -e "$ROOT/$rel" ] || fail "File appeared during update: $rel"
    printf '0\t%s\n' "$rel" >> "$TXN/applied.tsv"
  fi
  if [ "$kind" = "remove" ]; then rm -f "$ROOT/$rel"
  else
    mkdir -p "$(dirname "$ROOT/$rel")"
    cp -p "$TXN/files/$rel" "$ROOT/$rel.expedition-tmp"
    mv -f "$ROOT/$rel.expedition-tmp" "$ROOT/$rel"
  fi
  APPLIED=$((APPLIED + 1))
  if [ "${EXPEDITION_ALLOW_LOCAL_TEST:-0}" = "1" ] && [ "${EXPEDITION_TEST_FAIL_AFTER:-0}" = "$APPLIED" ]; then fail "Injected test failure"; fi
done < "$TXN/plan.tsv"
cp "$TXN/new-state.tsv" "$STATE/state.tsv.tmp"
cp "$RELEASE" "$STATE/installed.env.tmp"
mv -f "$STATE/state.tsv.tmp" "$STATE/state.tsv"
mv -f "$STATE/installed.env.tmp" "$STATE/installed.env"
COMMITTED=1
say "Update complete: $VERSION. Backup: .expedition/backups/$STAMP"
