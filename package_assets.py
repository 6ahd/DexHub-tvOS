#!/usr/bin/env python3
import plistlib
import shutil
import sys
import json
import os
import xml.etree.ElementTree as ET
from check_dependencies import validate
from pathlib import Path
from zipfile import ZipFile

base, app = map(Path, sys.argv[1:3])
minimum = sys.argv[3]
addons = app / 'AppData/AppHome/addons'
# Remove older bundled copies only from the temporary packaging stage.
for old in ('plugin.video.dexhub', 'skin.dexhub'):
    shutil.rmtree(addons / old, ignore_errors=True)
managed = set()
for asset in sorted((base / 'assets').glob('*.zip')):
    with ZipFile(asset) as archive:
        descriptors = [n for n in archive.namelist() if n.count('/') == 1 and n.endswith('/addon.xml')]
        if len(descriptors) != 1: raise SystemExit('Invalid bundled addon: ' + asset.name)
        expected = ET.fromstring(archive.read(descriptors[0])).get('id')
        if not expected or '/' in expected: raise SystemExit('Invalid addon identity')
        if expected in managed: raise SystemExit('Duplicate bundled addon: ' + expected)
        managed.add(expected)
        for member in archive.namelist():
            path = Path(member)
            if path.is_absolute() or '..' in path.parts or path.parts[0] != expected:
                raise SystemExit(f'Unexpected asset archive entry: {member}')
        archive.extractall(addons)
# v20: no overlays. The plugin and skin ZIPs in assets are built whole from src/
# (release_assets.py), so nothing older is copied over a newer release.
shutil.copytree(base / 'script.dexhub.tvos.players', addons / 'script.dexhub.tvos.players', dirs_exist_ok=True)
managed.add('script.dexhub.tvos.players')
if (base / 'script.dexhub.tvos.test').is_dir():
    shutil.copytree(base / 'script.dexhub.tvos.test', addons / 'script.dexhub.tvos.test', dirs_exist_ok=True)
    managed.add('script.dexhub.tvos.test')
if os.environ.get('DEX_REPO_URL'):
    import subprocess
    repo = base / 'repo-generated'
    subprocess.run([sys.executable, str(base/'prepare-repo.py'), '--url', os.environ['DEX_REPO_URL'], '--output', str(repo)], check=True)
    shutil.copytree(repo/'repository.dexworld.appletv', addons/'repository.dexworld.appletv', dirs_exist_ok=True)
    managed.add('repository.dexworld.appletv')
else:
    print('Apple TV repository URL not configured: bundle upgrades work; fork network updates await DEX_REPO_URL.')
descriptors = validate(addons)
manifest = {'revision': 20, 'addons': [{'id': identifier, 'version': descriptors[identifier].get('version')} for identifier in sorted(managed)]}
(app / 'AppData/DexHubBundle.json').write_text(json.dumps(manifest, indent=2))
font_source = addons / 'script.dexworld.fonts/resources/fonts'
if not list(font_source.glob('*.ttf')): raise SystemExit('Bundled subtitle fonts missing')
shutil.copytree(font_source, app/'AppData/DexHubFonts', dirs_exist_ok=True)
info = app / 'Info.plist'
data = plistlib.loads(info.read_bytes())
if not data.get('UIApplicationSceneManifest'):
    raise SystemExit('Kodi scene lifecycle manifest missing; rebuild with the updated source adapter.')
data['MinimumOSVersion'] = minimum
if not any('dexhub-player' in entry.get('CFBundleURLSchemes', []) for entry in data.get('CFBundleURLTypes', [])):
    data.setdefault('CFBundleURLTypes', []).append({'CFBundleURLName': 'DexHub Infuse return', 'CFBundleURLSchemes': ['dexhub-player']})
info.write_bytes(plistlib.dumps(data))
python_libraries = [path for path in (app / 'lib').glob('python3.*') if (path / 'urllib/request.py').is_file()]
if not python_libraries:
    raise SystemExit('Embedded Python library not found; cannot install tvOS proxy compatibility.')
for path in python_libraries:
    shutil.copy2(base / 'script.module.dexhub.tvos.compat/resources/system/_scproxy.py', path / '_scproxy.py')
print('Bundled DexHub %s, skin %s, player controls %s; Aether / Kodi / External.' % tuple(
    descriptors[i].get('version') for i in ('plugin.video.dexhub.tvos', 'skin.dexhub.tvos', 'script.dexhub.tvos.players')))
