#!/usr/bin/env python3
"""Fetch one reviewed release into its own checkout, preserving Nuvio's vendor."""
import json
import subprocess
import sys
from pathlib import Path

TAG = '7.38.1'
COMMIT = 'ce1670f8c6c4b8b11a8020e9c40a10c0d6da9823'
DEPENDENCIES = {'FFmpegBuild': '3.7.1', 'SMBClient': '0.3.1',
                'LibDovi': '2.1.0', 'LibTrueHD': '2.3.1', 'LibDTSX': '2.0.0'}


def prepare(work):
    root = Path(work) / 'dexhub-engine-sources' / ('AetherEngine-' + TAG)
    if not root.exists():
        root.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', 'clone', '--depth', '1', '--branch', TAG,
                        'https://github.com/superuser404notfound/AetherEngine.git', str(root)], check=True)
    actual = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != COMMIT:
        raise SystemExit('Aether checkout has another commit; use a new DEX_WORK directory.')
    manifest = root / 'Package.swift'
    original = subprocess.check_output(['git', '-C', str(root), 'show', 'HEAD:Package.swift'], text=True)
    pinned = original
    for name, version in DEPENDENCIES.items():
        old = '.upToNextMinor(from: "' + version + '")'
        if pinned.count(old) != 1: raise SystemExit('Dependency pin anchor changed: ' + name)
        pinned = pinned.replace(old, 'exact: "' + version + '"')
    if manifest.read_text() not in (original, pinned):
        raise SystemExit('Aether manifest has local edits; refusing to overwrite them.')
    manifest.write_text(pinned)
    (root / 'DexHubEngine.json').write_text(json.dumps({'version': TAG, 'commit': COMMIT, 'dependencies': DEPENDENCIES}, indent=2))
    return root


if __name__ == '__main__':
    print(prepare(sys.argv[1]))
