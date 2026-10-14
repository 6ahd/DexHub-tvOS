#!/usr/bin/env python3
"""v20: build the plugin, skin and player-control ZIPs whole from src/ and the
players folder. There are no overlays: edit src/ and run this file again."""
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

base = Path(__file__).resolve().parent
sources = [base / 'src' / 'plugin.video.dexhub.tvos', base / 'src' / 'skin.dexhub.tvos',
           base / 'script.dexhub.tvos.players']
built = []
for root in sources:
    identifier = root.name
    version = ET.parse(root / 'addon.xml').getroot().get('version')
    for old in (base / 'assets').glob(identifier + '-*.zip'):
        old.unlink()
    target = base / 'assets' / f'{identifier}-{version}.zip'
    temporary = target.with_suffix('.zip.tmp')
    with ZipFile(temporary, 'w', ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc' and path.name != '.DS_Store':
                archive.write(path, path.relative_to(root.parent))
    with ZipFile(temporary) as archive:
        if archive.testzip():
            raise RuntimeError('Generated addon ZIP failed integrity: ' + target.name)
    temporary.replace(target)
    built.append(f'{identifier} {version}')
print('Built: ' + ', '.join(built))
