#!/usr/bin/env bash
set -euo pipefail
BASE="$(cd "$(dirname "$0")" && pwd)"
WORK="${DEX_WORK:-$HOME/Developer/DexHub-tvOS}"
if [ "$(uname -s)" != Darwin ]; then
  echo "This build requires your prepared Mac with Xcode."
  exit 1
fi
KODI_SRC="${KODI_SRC:-$WORK/kodi-rc1-source}"
if [ ! -d "$KODI_SRC" ]; then
  echo "Kodi source not found: $KODI_SRC"
  echo "First build on this Mac: bash \"$(dirname "$0")/update-kodi.sh\" 22.0rc1-Piers"
  echo "It downloads Kodi, builds its dependencies once, then builds the app."
  exit 1
fi
export KODI_SRC
AVAILABLE_KB="$(df -Pk "$WORK" | awk 'END {print $4}')"
case "$AVAILABLE_KB" in
  ''|*[!0-9]*) echo "Could not determine free disk space."; exit 1 ;;
esac
# v20.1: once the Aether 7.35.1 bridge and its packages are on this Mac, a rebuild is
# incremental (Kodi objects already exist), so 10 GiB is enough. A first build needs 20.
NEED_KB=20971520
PLIST="$WORK/aether-bridge-build/Products/Release-appletvos/DexAetherBridge.framework/Info.plist"
if [ -f "$PLIST" ] && [ -d "$WORK/aether-bridge-build/SourcePackages/checkouts/FFmpegBuild" ] && \
   [ "$(/usr/libexec/PlistBuddy -c 'Print :DexHubAetherVersion' "$PLIST" 2>/dev/null)" = "7.35.1" ]; then
  NEED_KB=10485760
fi
if [ "$AVAILABLE_KB" -lt "$NEED_KB" ]; then
  echo "Less than $((NEED_KB / 1048576)) GiB free. Aether's updated binary dependencies need space."
  echo "Free space safely first; required space varies with the existing build."
  df -h "$WORK"
  exit 1
fi
echo "Kodi AetherOnly v21.13 TEST: Aether 7.35.1 / DexHub 5.10.306 / Skin 3.28.51 / Players 1.0.14 / Release / idle GUI while playing"
echo "The Apple TV addon does not need to be running to build on this Mac."
cd "$BASE"
if [ -d "$BASE/src/plugin.video.dexhub.tvos" ] && [ -d "$BASE/src/skin.dexhub.tvos" ]; then
  python3 "$BASE/release_assets.py"
else
  bash "$BASE/get-dexhub.sh"
fi
bash "$BASE/all.sh"
