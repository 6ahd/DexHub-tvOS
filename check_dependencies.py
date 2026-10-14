#!/usr/bin/env python3
"""Reject an IPA whose bundled Python addons lack required dependencies."""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

def version(value):
    return tuple(int(part) for part in re.findall(r'\d+', value or '0'))

def validate(addons):
    descriptors = {}
    for path in Path(addons).glob('*/addon.xml'):
        node = ET.parse(path).getroot()
        descriptors[node.get('id')] = node
    failures = []
    for identifier, node in descriptors.items():
        for dependency in node.findall('requires/import'):
            if dependency.get('optional') == 'true': continue
            name = dependency.get('addon')
            target = descriptors.get(name)
            if target is None:
                failures.append(f'{identifier}: missing {name}')
            elif version(target.get('version')) < version(dependency.get('version')):
                failures.append(f'{identifier}: {name} {target.get("version")} < {dependency.get("version")}')
    if failures: raise RuntimeError('\n'.join(failures))
    return descriptors

if __name__ == '__main__':
    import sys
    print('Validated addon dependency closure:', len(validate(sys.argv[1])))
