"""Wrap Kodi's generated dependency toolchain for this app's deployment target."""
from pathlib import Path
import re,sys
source,build=map(Path,sys.argv[1:3]);minimum=sys.argv[3]
if not re.fullmatch(r'\d+(?:\.\d+){0,2}',minimum):raise SystemExit('Invalid deployment target')
text=(source/'tools/depends/Makefile.include').read_text()
match=re.search(r'^PREFIX\s*=\s*(.+)$',text,re.M)
if not match:raise SystemExit('Kodi dependency prefix missing')
prefix=match.group(1).strip()
if not Path(prefix).is_absolute() or '$' in prefix:raise SystemExit('Expected configured absolute Kodi dependency prefix')
toolchain=Path(prefix)/'share/Toolchain.cmake'
if not toolchain.is_file():raise SystemExit('Configured Kodi dependency toolchain missing')
build.mkdir(parents=True,exist_ok=True)
escaped=str(toolchain).replace('\\','/').replace('"','\\"')
wrapper=build/'DexHubToolchain.cmake'
wrapper.write_text(f'include("{escaped}")\nset(CMAKE_OSX_DEPLOYMENT_TARGET "{minimum}")\nset(CMAKE_XCODE_ATTRIBUTE_TVOS_DEPLOYMENT_TARGET "{minimum}")\n')
print(wrapper)
