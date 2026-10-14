#!/usr/bin/env bash
# v20.1: make every embedded framework easy for any IPA signer to re-sign.
# FFmpegBuild ships its tvOS frameworks as universal (fat) wrappers holding one
# arm64 slice, pre-signed ad hoc, with Headers/Modules inside. Some signers leave
# such a binary with a broken signature, and installd then refuses the IPA:
#   ApplicationVerificationFailed ... AetherLibzimg.framework ... invalid signature
# Here: thin to plain arm64, drop build-only folders and the old signature, and
# sign each framework ad hoc again. The final signer replaces these signatures.
set -euo pipefail
APP="$1"
[ -d "$APP/Frameworks" ] || { echo "No Frameworks folder in $APP"; exit 1; }
for FW in "$APP"/Frameworks/*.framework; do
  NAME="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$FW/Info.plist" 2>/dev/null || basename "$FW" .framework)"
  BIN="$FW/$NAME"
  [ -f "$BIN" ] || { echo "Skip (no binary): $FW"; continue; }
  if lipo -info "$BIN" 2>/dev/null | grep -q 'Architectures in the fat file'; then
    lipo "$BIN" -thin arm64 -output "$BIN.thin"
    chmod u+w "$BIN" "$BIN.thin"
    mv -f "$BIN.thin" "$BIN"
    echo "Thinned to arm64: $(basename "$FW")"
  fi
  chmod -R u+w "$FW"
  rm -rf "$FW/Headers" "$FW/PrivateHeaders" "$FW/Modules" "$FW/_CodeSignature"
  codesign --remove-signature "$BIN" 2>/dev/null || true
  codesign --force --sign - --timestamp=none "$FW" >/dev/null
done
for DYLIB in "$APP"/Frameworks/*.dylib; do
  [ -f "$DYLIB" ] || continue
  codesign --force --sign - --timestamp=none "$DYLIB" >/dev/null
done
for FW in "$APP"/Frameworks/*.framework; do
  codesign --verify --strict "$FW" || { echo "Signature check failed: $FW"; exit 1; }
done
echo "Frameworks normalized and signed ad hoc: $(ls -d "$APP"/Frameworks/*.framework | wc -l | tr -d ' ')"
