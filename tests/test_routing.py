import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

base=Path(__file__).resolve().parents[1]
path=base/'src/plugin.video.dexhub.tvos/resources/lib/tvos_players.py'
spec=importlib.util.spec_from_file_location('tvos_players',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
for index,name in enumerate(['Kodi','Aether','External','Aether','Aether']):
    xbmc=SimpleNamespace(executeJSONRPC=lambda request:json.dumps({'result':{'value':index if json.loads(request)['params']['setting']=='videoplayer.dexhubengine' else 1}}))
    assert module.preference(xbmc,SimpleNamespace())==(name,'VidHub')
class Window:
    def __init__(self):self.properties={}
    def setProperty(self,key,value):self.properties[key]=value
    def getProperty(self,key):return self.properties.get(key,'')
    def clearProperty(self,key):self.properties.pop(key,None)
window=Window()
class Dialog:
    def select(self,*args,**kwargs):return selection
class ListItem:
    def __init__(self,**kwargs):self.label=kwargs['label'];self.detail=kwargs['label2']
    def setArt(self,art):self.art=art
xbmc=SimpleNamespace(getCondVisibility=lambda _:True,executebuiltin=lambda *args:None,executeJSONRPC=lambda _:json.dumps({'result':{'value':0}}))
gui=SimpleNamespace(Dialog=Dialog,Window=lambda _:window,ListItem=ListItem)
addon=SimpleNamespace(Addon=lambda _:SimpleNamespace())
for selection,name in [(0,'Aether'),(1,'Kodi'),(2,'External'),(3,'External')]:
    assert module.choose_once(xbmc,gui,addon)
    assert json.loads(window.getProperty(module.OVERRIDE))['player']==name
    if selection in (2,3): assert json.loads(window.getProperty(module.OVERRIDE))['external'] == ['Infuse','VidHub'][selection-2]
window.clearProperty(module.OVERRIDE);selection=-1
assert not module.choose_once(xbmc,gui,addon)
assert not window.getProperty(module.OVERRIDE)
item=Window();item.setProperty('dexhub.trailer','1')
api=SimpleNamespace(xbmc=xbmc)
sys.modules['xbmcaddon']=addon
assert not module.handoff(api,'https://example.test/trailer.mp4',[],None,0,item)
assert item.getProperty('dexhub.playercore')=='VideoPlayer'
for index, name in [(1,'Aether'),(3,'Aether'),(4,'Aether')]:
    window.clearProperty(module.OVERRIDE)
    xbmc.executeJSONRPC=lambda request:json.dumps({'result':{'value':index if json.loads(request)['params']['setting']=='videoplayer.dexhubengine' else 0}})
    api.xbmcgui=gui
    item=Window()
    assert not module.handoff(api,'https://example.test/movie.mkv|Authorization=Bearer%20fixture',[],None,0,item)
    assert item.getProperty('dexhub.playercore')==name
    assert json.loads(window.getProperty(module.SESSION))['headers']['Authorization']=='Bearer fixture'
spec=importlib.util.spec_from_file_location('player_choice',base/'script.dexhub.tvos.players/player_choice.py')
choice=importlib.util.module_from_spec(spec);spec.loader.exec_module(choice)
commands=[]
xbmc.executebuiltin=commands.append
xbmc.getInfoLabel=lambda _: 'id=123&season=2&episode=4'
assert choice.choose_and_play(xbmc,gui,addon,lambda *a:True)
assert commands == ['RunPlugin("plugin://plugin.video.dexhub.tvos/?action=skin_play&id=123&season=2&episode=4")']
commands.clear()
assert not choice.choose_and_play(xbmc,gui,addon,lambda *a:False)
assert not commands
print('PASS: Aether/Kodi/external preferences, removed-engine migration, one-shot choices, immediate search, cancellation and trailers')
