#!/usr/bin/env bash
# Repair an already built v20 IPA (no rebuild): writes <name>-fixed.ipa next to it.
set -euo pipefail
BASE="$(cd "$(dirname "$0")" && pwd)"
IPA="${1:-$(ls -t "$HOME"/Downloads/Kodi-DexHub-AetherOnly-v20-TEST-unsigned-*.ipa 2>/dev/null | grep -v -- '-fixed.ipa$' | head -1)}"
[ -f "$IPA" ] || { echo "IPA not found. Pass its path: bash FIX-SIGNING.command /path/to/file.ipa"; exit 1; }
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
ditto -x -k "$IPA" "$WORK"
bash "$BASE/normalize_frameworks.sh" "$WORK/Payload/Kodi.app"
OUT="${IPA%.ipa}-fixed.ipa"
rm -f "$OUT"
(cd "$WORK" && ditto -c -k --keepParent Payload "$OUT")
unzip -t "$OUT" >/dev/null
echo "$OUT"
echo "Sign this -fixed.ipa (with its frameworks) and install it."
open -R "$OUT"
