#!/usr/bin/env python3
"""Stage resolved Aether dependencies and remove owned legacy engine bundles."""
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path


def stage(root, app):
    app = Path(app)
    frameworks = app / 'Frameworks'
    frameworks.mkdir(exist_ok=True)
    legacy = {'DexKSBridge', 'DexMPVBridge', 'KSPlayer', 'MPVKit',
              'Libmpv', 'Libavcodec', 'Libavformat', 'Libavutil',
              'Libavfilter', 'Libswresample', 'Libswscale',
              'Libdav1d', 'Libdovi', 'Libuchardet', 'Libunibreak',
              'Libass', 'Libbluray', 'Libshaderc_combined', 'Libplacebo',
              'MoltenVK', 'Libcrypto', 'Libssl', 'Libsmbclient', 'Libgmp',
              'Libgnutls', 'Libhogweed', 'Libnettle'}
    for name in legacy:
        shutil.rmtree(frameworks / (name + '.framework'), ignore_errors=True)
    for name in ('KSPlayer_KSPlayer.bundle', 'MPVKit_MPVKit.bundle'):
        shutil.rmtree(app / name, ignore_errors=True)
    staged = {}
    for package in sorted(Path(root).rglob('*.xcframework')):
        info = plistlib.loads((package / 'Info.plist').read_bytes())
        for library in info.get('AvailableLibraries', []):
            if library.get('SupportedPlatform') != 'tvos' or library.get('SupportedPlatformVariant'):
                continue
            if 'arm64' not in library.get('SupportedArchitectures', []): continue
            source = package / library['LibraryIdentifier'] / library['LibraryPath']
            if source.suffix == '.a':
                if not source.is_file(): raise SystemExit('Missing static archive: ' + str(source))
                # SwiftPM links archives into the bridge; they are not embedded.
                continue
            if source.suffix != '.framework':
                raise SystemExit('Unexpected binary slice: ' + str(source))
            name = source.stem
            binary = source / name
            if not binary.is_file(): raise SystemExit('Missing framework binary: ' + str(binary))
            kind = subprocess.check_output(['file', str(binary)], text=True)
            if 'dynamically linked shared library' not in kind: continue
            if name in staged and staged[name].read_bytes() != binary.read_bytes():
                raise SystemExit('Conflicting resolved framework: ' + name)
            staged[name] = binary
            destination = frameworks / source.name
            if destination.exists(): shutil.rmtree(destination)
            subprocess.run(['ditto', str(source), str(destination)], check=True)
    if not any(name.startswith('AetherLibav') for name in staged):
        raise SystemExit('No resolved Aether FFmpeg frameworks staged')
    if any((frameworks / (name + '.framework')).exists() for name in ('DexKSBridge', 'DexMPVBridge')):
        raise SystemExit('Legacy player framework remains in IPA')
    print('Resolved Aether frameworks:', ', '.join(sorted(staged)))


if __name__ == '__main__': stage(*map(Path, sys.argv[1:3]))
