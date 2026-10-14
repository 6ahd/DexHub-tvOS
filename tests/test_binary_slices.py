"""Exercise XCFramework slice selection and archive handling with tool substitutes."""
import importlib.util
import os
import plistlib
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

base = Path(__file__).resolve().parents[1]
names = ['AetherLibavcodec', 'AetherLibavformat', 'AetherLibavutil',
         'AetherLibswresample', 'AetherLibswscale', 'AetherLibdav1d',
         'AetherLibavfilter', 'AetherLibzimg', 'AetherLibzvbi']

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    packages = root / 'SourcePackages'
    for name, version in [(n, '16.0') for n in names] + [('libdovi', '27.0'), ('libtruehd', '26.0')]:
        package = packages / (name + '.xcframework')
        folder = package / 'tvos-arm64'
        folder.mkdir(parents=True)
        path = name + '.a' if name.startswith('lib') else name + '.framework'
        binary = folder / path
        if binary.suffix == '.framework':
            binary.mkdir()
            (binary / 'Info.plist').write_bytes(plistlib.dumps({'MinimumOSVersion': version}))
            binary = binary / name
        binary.write_bytes(b'fixture')
        (package / 'Info.plist').write_bytes(plistlib.dumps({'AvailableLibraries': [
            {'LibraryIdentifier': 'tvos-arm64', 'LibraryPath': path,
             'SupportedPlatform': 'tvos', 'SupportedArchitectures': ['arm64']},
            {'LibraryIdentifier': 'tvos-arm64-simulator', 'LibraryPath': path,
             'SupportedPlatform': 'tvos', 'SupportedPlatformVariant': 'simulator',
             'SupportedArchitectures': ['arm64']},
            {'LibraryIdentifier': 'ios-arm64', 'LibraryPath': path,
             'SupportedPlatform': 'ios', 'SupportedArchitectures': ['arm64']}]}))
    tools = root / 'tools'; tools.mkdir()
    xcrun = tools / 'xcrun'
    xcrun.write_text('#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\np=Path(sys.argv[-1])\nassert p.is_file(), str(p)\nprint("minos", "27.0" if p.name == "libdovi.a" else "16.0")\n')
    xcrun.chmod(0o755)
    output = root / 'deployment.txt'
    result = subprocess.run([sys.executable, str(base/'preflight.py'), str(packages), str(output)],
                            env={**os.environ, 'PATH': str(tools) + ':' + os.environ['PATH']},
                            check=True, capture_output=True, text=True)
    assert output.read_text() == '27.0'
    assert 'libdovi:' in result.stdout and 'libtruehd:' in result.stdout
    spec = importlib.util.spec_from_file_location('package_frameworks', base/'package_frameworks.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    app = root / 'Kodi.app'; frameworks = app/'Frameworks'; frameworks.mkdir(parents=True)
    for name in ('DexKSBridge', 'DexMPVBridge', 'libdvdnav-aarch64'):
        (frameworks/(name+'.framework')).mkdir()
    copies = []
    def kind(args, **kwargs):
        assert Path(args[-1]).is_file()
        assert not args[-1].endswith('.a')
        return 'Mach-O 64-bit dynamically linked shared library arm64'
    with patch.object(module.subprocess, 'check_output', side_effect=kind), \
         patch.object(module.subprocess, 'run', side_effect=lambda args, **kwargs: copies.append(args)):
        module.stage(packages, app)
    assert len(copies) == len(names)
    assert all(not any(str(arg).endswith('.a') for arg in call) for call in copies)
    assert (frameworks/'libdvdnav-aarch64.framework').is_dir()
    assert not (frameworks/'DexKSBridge.framework').exists()
    assert not (frameworks/'DexMPVBridge.framework').exists()
    archive = packages/'libdovi.xcframework/tvos-arm64/libdovi.a'
    archive.unlink()
    missing = subprocess.run([sys.executable, str(base/'preflight.py'), str(packages), str(output)],
                            env={**os.environ, 'PATH': str(tools) + ':' + os.environ['PATH']},
                            capture_output=True, text=True)
    assert missing.returncode and 'Missing binary:' in missing.stderr
print('PASS: static archives inspected, deployment floor raised, simulator/iOS skipped, only dynamic frameworks copied; missing archives rejected')
