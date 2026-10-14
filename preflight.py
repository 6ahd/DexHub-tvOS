#!/usr/bin/env python3
import plistlib
import re
import subprocess
import sys
from pathlib import Path

root, output = map(Path, sys.argv[1:3])
minimum = (26, 0)
found = set()
frameworks = []
for package in sorted(root.rglob('*.xcframework')):
    metadata = plistlib.loads((package / 'Info.plist').read_bytes())
    for library in metadata.get('AvailableLibraries', []):
        if library.get('SupportedPlatform') == 'tvos' and not library.get('SupportedPlatformVariant') and 'arm64' in library.get('SupportedArchitectures', []):
            frameworks.append(package / library['LibraryIdentifier'] / library['LibraryPath'])
for framework in frameworks:
    name = framework.stem
    found.add(name)
    if framework.suffix == '.framework':
        binary = framework / name
        info = plistlib.loads((framework / 'Info.plist').read_bytes())
    elif framework.suffix == '.a':
        binary = framework
        info = {}
    else:
        raise SystemExit('Unexpected binary slice: ' + str(framework))
    if not binary.is_file():
        raise SystemExit(f'Missing binary: {binary}')
    with binary.open('rb') as stream:
        magic = stream.read(128)
    if magic.startswith(b'version https://git-lfs.github.com/spec/v1'):
        raise SystemExit('Resolved binary is a Git LFS pointer; package resolution is incomplete.')
    reported = info.get('MinimumOSVersion')
    if reported:
        minimum = max(minimum, tuple(map(int, reported.split('.')[:2])))
    result = subprocess.run(['xcrun', 'otool', '-l', str(binary)],
                            text=True, capture_output=True)
    if result.returncode:
        raise SystemExit(f'Cannot inspect {binary}: {result.stderr}')
    versions = re.findall(r'\bminos\s+(\d+(?:\.\d+){0,2})', result.stdout)
    legacy = re.findall(r'LC_VERSION_MIN_TVOS\s+cmdsize\s+\d+\s+version\s+(\d+(?:\.\d+){0,2})', result.stdout)
    for version in versions + legacy:
        minimum = max(minimum, tuple(map(int, version.split('.')[:2])))
    print(f'{name}: plist={reported or "not supplied"}, binary minimum={sorted(set(versions + legacy))}')
required = {'AetherLibavcodec', 'AetherLibavformat', 'AetherLibavutil',
            'AetherLibswresample', 'AetherLibswscale', 'AetherLibdav1d',
            'AetherLibavfilter', 'AetherLibzimg', 'AetherLibzvbi'}
if not required <= found: raise SystemExit('Unresolved Aether binaries: ' + str(sorted(required - found)))
output.write_text('.'.join(map(str, minimum)))
print('Required tvOS:', output.read_text())
