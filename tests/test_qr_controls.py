import importlib
import json
import sys
import tempfile
import types
from pathlib import Path
from zipfile import ZipFile

base = Path(__file__).resolve().parents[1]
package = types.ModuleType('qr_fixture'); package.__path__=[str(base/'src/plugin.video.dexhub.tvos/resources/lib')]
sys.modules['qr_fixture'] = package
sys.modules['qr_fixture.i18n'] = types.SimpleNamespace(tr=lambda x:x)
class Image:
    def __init__(self,*args,**kwargs):self.args=args; self.kwargs=kwargs
with tempfile.TemporaryDirectory() as directory:
    temp = Path(directory)
    with ZipFile(base/'assets/script.module.qrcode-6.1.0+matrix.3.zip') as archive:archive.extractall(temp)
    with ZipFile(base/'assets/script.module.six-1.16.0+matrix.1.zip') as archive:archive.extractall(temp)
    sys.path[:0]=[str(temp/'script.module.qrcode/lib'),str(temp/'script.module.six/lib')]
    sys.modules['xbmc'] = types.SimpleNamespace(getCondVisibility=lambda _:True,log=lambda *a:None,LOGINFO=1,LOGWARNING=2)
    sys.modules['xbmcaddon'] = types.SimpleNamespace(Addon=lambda *a:types.SimpleNamespace(getAddonInfo=lambda _:str(temp)))
    sys.modules['xbmcgui'] = types.SimpleNamespace(ControlImage=Image,WindowDialog=object)
    sys.modules['xbmcvfs'] = types.SimpleNamespace(translatePath=lambda _:str(temp/'qr'))
    qr = importlib.import_module('qr_fixture.plex_qr')
    ui = importlib.import_module('qr_fixture.pairing_ui')
    first = qr.qr_png('http://192.168.1.2:1234/fixture/')
    second = qr.qr_png('http://192.168.1.2:1234/other/')
    assert first and second and Path(first).is_file() and Path(second).is_file()
    controls=[]
    window=types.SimpleNamespace(addControls=controls.extend,addControl=controls.append)
    ui.qr(window,first,0,0,380)
    matrix=json.loads(Path(first+'.matrix.json').read_text())
    size=len(matrix); unit=380//size; margin=(380-size*unit)//2
    painted=[[False]*size for _ in range(size)]
    for image in controls[1:]:
        assert image.kwargs['colorDiffuse']=='FF000000'
        x,y,width,height,_=image.args
        row=(y-margin)//unit; column=(x-margin)//unit
        for offset in range(width//unit):painted[row][column+offset]=True
    assert painted==matrix and len(controls)>1
    assert all(image.args[-1]!=first for image in controls)
print('PASS: bundled QR encoder; native-control rendering reproduces QR matrix without PNG texture; concurrent QR files retained')
