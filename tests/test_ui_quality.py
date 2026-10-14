import importlib.util,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
import xml.etree.ElementTree as ET
base=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as directory:
    root=Path(directory)
    def path(value):return root/value.replace('special://profile/','')
    class File:
        def __init__(self,value,mode='r'):
            target=path(value);target.parent.mkdir(parents=True,exist_ok=True);self.f=target.open(mode)
        def read(self):return self.f.read()
        def write(self,value):return self.f.write(value)
        def close(self):return self.f.close()
    sys.modules['xbmcvfs']=SimpleNamespace(File=File,exists=lambda x:path(x).exists(),mkdirs=lambda x:path(x).mkdir(parents=True,exist_ok=True))
    sys.modules['xbmc']=SimpleNamespace(log=lambda *x:None,LOGINFO=1)
    spec=importlib.util.spec_from_file_location('ui_quality',base/'script.dexhub.tvos.players/ui_quality.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    original='<advancedsettings><cache><memorysize>12345</memorysize></cache><imageres>720</imageres></advancedsettings>'
    (root/'advancedsettings.xml').write_text(original)
    assert module.install() and not module.install()
    xml=ET.parse(root/'advancedsettings.xml');assert xml.findtext('imageres')=='1080' and xml.findtext('fanartres')=='2160'
    assert xml.findtext('cache/memorysize')=='12345'
    assert (root/'advancedsettings.before-dexhub-quality.xml').read_text()==original
    (root/'advancedsettings.xml').write_text('<broken>')
    try:module.install(force=True);raise AssertionError('Malformed settings accepted')
    except ET.ParseError:pass
    assert (root/'advancedsettings.xml').read_text()=='<broken>'
print('PASS: artwork quality, preserved unrelated settings, first backup, idempotency and malformed-file protection.')
