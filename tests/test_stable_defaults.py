import importlib.util
import json
import sys
import tempfile
import types
from pathlib import Path

base = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('stable_defaults', base/'script.dexhub.tvos.players/stable_defaults.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as directory:
    (Path(directory)/'kodi-first-v17.done').write_text('Kodi')
    settings = {'tvos_player':'KSPlayer','subtitle_search_mode':'Attach before playing'}
    calls = []
    addon = types.SimpleNamespace(getAddonInfo=lambda _:directory, setSetting=lambda k,v:settings.update({k:v}),getSetting=lambda k:settings.get(k,''))
    sys.modules['xbmcaddon'] = types.SimpleNamespace(Addon=lambda _:addon)
    sys.modules['xbmcvfs'] = types.SimpleNamespace(translatePath=lambda x:x)
    def rpc(value):
        request=json.loads(value)
        if request['method']=='Settings.GetSettingValue':return json.dumps({'result':{'value':0}})
        calls.append(request); return json.dumps({'result':True})
    sys.modules['xbmc'] = types.SimpleNamespace(executeJSONRPC=rpc,log=lambda *a:None,LOGINFO=1,LOGWARNING=2)
    module.install()
    assert settings == {'tvos_player':'Aether','subtitle_search_mode':'Play with subtitles'}
    assert calls[0]['params']['value'] == 1
    settings['tvos_player'] = 'Kodi'; module.install()
    assert len(calls) == 1 and settings['tvos_player'] == 'Kodi'
print('PASS: Aether-first migration once; background subtitles; later user preference retained')
