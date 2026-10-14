#!/usr/bin/env bash
set -euo pipefail
BASE="$(cd "$(dirname "$0")" && pwd)"
WORK="${DEX_WORK:-$HOME/Developer/DexHub-tvOS}"
NATIVE="${DEX_NATIVE:-}"
if [ -z "$NATIVE" ]; then
  NATIVE="$(find /Users/Shared/xbmc-depends -maxdepth 1 -type d -name '*-native' | sort | tail -1)"
fi
[ -x "$NATIVE/bin/python3" ] || { echo "Set DEX_NATIVE to the native Kodi dependency directory."; exit 1; }
export PATH="$NATIVE/bin:/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"
PYTHON="$NATIVE/bin/python3"
CONFIG="${DEX_CONFIG:-Release}"
case "$CONFIG" in Release|Debug) ;; *) echo "DEX_CONFIG must be Release or Debug"; exit 1 ;; esac
FRAMEWORK="$WORK/aether-bridge-build/Products/Release-appletvos/DexAetherBridge.framework"
test -s "$FRAMEWORK/DexAetherBridge"
"$PYTHON" -c 'import plistlib,sys; p=plistlib.load(open(sys.argv[1],"rb")); sys.exit(0 if str(p.get("DexHubBridgeAPI")) == "2" and p.get("DexHubBridgeRevision") == 19 and p.get("DexHubAetherVersion") == "7.35.1" else "Old Swift bridge: run all.sh before packaging.")' "$FRAMEWORK/Info.plist"
MINIMUM="$(cat "$WORK/aether-bridge-build/deployment.txt")"
echo "Experimental IPA will require tvOS $MINIMUM or newer."
KODI_SRC="${KODI_SRC:-$WORK/kodi-rc1-source}"
KODI_BUILD="${KODI_BUILD:-$WORK/kodi-tvos17-build}"
"$PYTHON" "$BASE/apply_bridge.py" "$KODI_SRC" --check
"$PYTHON" "$BASE/apply_bridge.py" "$KODI_SRC"
git -C "$KODI_SRC" diff --check
if [ -x /opt/homebrew/opt/m4/bin/m4 ]; then export M4=/opt/homebrew/opt/m4/bin/m4; fi
"$PYTHON" "$BASE/prepare_toolchain.py" "$KODI_SRC" "$KODI_BUILD" "$MINIMUM"
make -C "$KODI_SRC/tools/depends/target/cmakebuildsys" BUILD_DIR="$KODI_BUILD" \
  CMAKE_EXTRA_ARGUMENTS="-DCMAKE_TOOLCHAIN_FILE=\"$KODI_BUILD/DexHubToolchain.cmake\""
cd "$KODI_BUILD"
xcodebuild -target kodi -configuration "$CONFIG" -jobs "$(sysctl -n hw.ncpu)" \
  TVOS_DEPLOYMENT_TARGET="$MINIMUM" \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY="" \
  build 2>&1 | tee "$WORK/aether-bridge-build/kodi-bridge-build.log"

STAGE="$(mktemp -d "$WORK/aether-ipa-stage.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT
APP="$STAGE/Payload/Kodi.app"
mkdir -p "$STAGE/Payload"
ditto "$KODI_BUILD/build/$CONFIG-appletvos/Kodi.app" "$APP"
ditto "$FRAMEWORK" "$APP/Frameworks/DexAetherBridge.framework"

# The resolved graph contains the reviewed binary slices. Copy these rather
# than stale products left by an earlier build of the bridge.
"$PYTHON" "$BASE/package_frameworks.py" "$WORK/aether-bridge-build/SourcePackages" "$APP"
"$PYTHON" "$BASE/package_assets.py" "$BASE" "$APP" "$MINIMUM"
xcrun swift-stdlib-tool --copy --platform appletvos \
  --scan-executable "$APP/Frameworks/DexAetherBridge.framework/DexAetherBridge" \
  --scan-folder "$APP/Frameworks" --destination "$APP/Frameworks"
bash "$BASE/normalize_frameworks.sh" "$APP"

OUT="$HOME/Downloads/Kodi-DexHub-AetherOnly-v21.7-TEST-unsigned-$(date +%Y%m%d-%H%M%S).ipa"
ditto -c -k --keepParent "$STAGE/Payload" "$OUT"
unzip -t "$OUT" >/dev/null
for ASSET in "$BASE"/assets/*.zip; do
  ditto "$ASSET" "$HOME/Downloads/$(basename "$ASSET")"
done
echo "$OUT"
echo "Sign the entire IPA, including embedded frameworks, before installing."
open -R "$OUT"
