#!/usr/bin/env bash
# Download the Dex Hub add-on and skin ZIPs (release files, not source) into assets/.
# They are published on this repository's Releases page. Skips files already present.
set -euo pipefail
BASE="$(cd "$(dirname "$0")" && pwd)"
REPO="${DEX_GITHUB_REPO:-6ahd/DexHub-tvOS}"
TAG="${DEX_RELEASE_TAG:-latest}"
if ls "$BASE"/assets/plugin.video.dexhub.tvos-*.zip >/dev/null 2>&1 && ls "$BASE"/assets/skin.dexhub.tvos-*.zip >/dev/null 2>&1; then
  echo "Dex Hub add-on and skin already in assets/."
  exit 0
fi
if [ "$TAG" = latest ]; then API="https://api.github.com/repos/$REPO/releases/latest"; else API="https://api.github.com/repos/$REPO/releases/tags/$TAG"; fi
URLS="$(curl -fsSL "$API" | python3 -c '
import json, sys
for asset in json.load(sys.stdin).get("assets", []):
    name = asset["name"]
    if name.endswith(".zip") and name.startswith(("plugin.video.dexhub.tvos-", "skin.dexhub.tvos-")):
        print(asset["browser_download_url"])')"
[ -n "$URLS" ] || { echo "No Dex Hub add-on or skin ZIP found in release $TAG of $REPO."; exit 1; }
for URL in $URLS; do
  echo "Downloading $(basename "$URL")"
  curl -fL --retry 3 -o "$BASE/assets/$(basename "$URL")" "$URL"
done
