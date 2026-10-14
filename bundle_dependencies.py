#!/usr/bin/env python3
"""Prepare Python dependencies using the official Kodi mirror and pinned sources."""
import gzip
import hashlib
import json
import re
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from check_dependencies import version

base = Path(__file__).resolve().parent
assets = base / 'assets'
cache = Path(sys.argv[1])
cache.mkdir(parents=True, exist_ok=True)
mirror = 'https://mirrors.kodi.tv/addons/piers/'
index_path = cache / 'addons.xml.gz'
if not index_path.is_file():
    with urllib.request.urlopen(mirror + 'addons.xml.gz', timeout=45) as response:
        index_path.write_bytes(response.read())
index = ET.fromstring(gzip.decompress(index_path.read_bytes()))
origins = {}
for identifier, revision in [('script.module.jurialmunkey', '8f42fb5f4698f3e4552f38955964b2f3843dba69'),
                             ('script.module.infotagger', 'c6272475996215648d19fd030dd12b3cadc1bd23')]:
    source = cache / identifier
    if not (source / '.git').is_dir(): subprocess.run(['git','clone','--filter=blob:none','--no-checkout','https://github.com/jurialmunkey/'+identifier+'.git',str(source)],check=True)
    subprocess.run(['git','-C',str(source),'fetch','--depth','1','origin',revision],check=True)
    subprocess.run(['git','-C',str(source),'checkout','--detach',revision],check=True)
    node = ET.parse(source/'addon.xml').getroot()
    destination = assets / f'{identifier}-{node.get("version")}.zip'
    with ZipFile(destination,'w',ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob('*')):
            if path.is_file() and '.git' not in path.relative_to(source).parts:
                archive.write(path,identifier+'/'+str(path.relative_to(source)))
    origins[destination.name] = {'source':'https://github.com/jurialmunkey/'+identifier,'commit':revision}

def read_assets():
    result = {}
    for path in assets.glob('*.zip'):
        with ZipFile(path) as archive:
            names=[n for n in archive.namelist() if n.count('/')==1 and n.endswith('/addon.xml')]
            if len(names)!=1: raise RuntimeError('Invalid addon ZIP: '+path.name)
            node=ET.fromstring(archive.read(names[0]));result[node.get('id')]=node
    return result

while True:
    bundled = read_assets(); missing = {}
    for node in bundled.values():
        for dependency in node.findall('requires/import'):
            identifier=dependency.get('addon')
            if dependency.get('optional')=='true' or identifier.startswith(('xbmc.','kodi.')) or identifier=='script.module.pil':continue
            if identifier not in bundled:missing[identifier]=dependency.get('version')
            elif version(bundled[identifier].get('version')) < version(dependency.get('version')):
                raise RuntimeError('Bundled dependency too old: '+identifier)
    if not missing:break
    for identifier, minimum in sorted(missing.items()):
        candidates=[n for n in index if n.get('id')==identifier and version(n.get('version'))>=version(minimum)]
        if not candidates:raise RuntimeError('Official mirror lacks required dependency: '+identifier+' '+str(minimum))
        node=max(candidates,key=lambda n:version(n.get('version')))
        filename=f'{identifier}-{node.get("version")}.zip';url=mirror+identifier+'/'+filename
        with urllib.request.urlopen(url,timeout=45) as response:payload=response.read()
        with urllib.request.urlopen(url+'.md5',timeout=45) as response:checksum=response.read().decode().strip().split()[0]
        if hashlib.md5(payload).hexdigest()!=checksum:raise RuntimeError('Mirror checksum mismatch: '+filename)
        destination=assets/filename;destination.write_bytes(payload)
        with ZipFile(destination) as archive:
            if archive.testzip() is not None:raise RuntimeError('Damaged dependency: '+filename)
            root=ET.fromstring(archive.read(identifier+'/addon.xml'))
            if root.get('id')!=identifier or root.get('version')!=node.get('version'):raise RuntimeError('Dependency descriptor mismatch: '+filename)
        origins[filename]={'source':url,'mirror_md5':checksum}
for path in assets.glob('*.zip'):
    origins.setdefault(path.name,{})['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
(base/'DEPENDENCY-SOURCES.json').write_text(json.dumps(origins,indent=2)+'\n')
print('Python dependency assets ready:',len(read_assets()))
