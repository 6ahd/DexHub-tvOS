"""Exercise the real token-protected HTTP handler with Kodi API substitutes."""
import importlib
import json
import sys
import tempfile
import threading
import types
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from zipfile import ZipFile

base=Path(__file__).resolve().parents[1]
lib=base/'src/plugin.video.dexhub.tvos/resources/lib'
package=types.ModuleType('transfer_fixture');package.__path__=[str(lib)]
sys.modules['transfer_fixture']=package
traceback=types.ModuleType('transfer_fixture.lazy_tb');traceback.format_exc=lambda:'test error'
sys.modules[traceback.__name__]=traceback
commands=[];subtitles=[]
xbmc=types.ModuleType('xbmc');xbmc.LOGINFO=1;xbmc.LOGWARNING=2;xbmc.log=lambda *a:None
xbmc.executebuiltin=commands.append
xbmc.executeJSONRPC=lambda _:json.dumps({'result':{'value':13}})
xbmc.Player=lambda:types.SimpleNamespace(isPlayingVideo=lambda:True,setSubtitles=subtitles.append)
sys.modules['xbmc']=xbmc;sys.modules['xbmcaddon']=types.ModuleType('xbmcaddon')
sys.modules['xbmcvfs']=types.ModuleType('xbmcvfs')
gui=types.ModuleType('xbmcgui');gui.WindowDialog=object;sys.modules['xbmcgui']=gui
phone=importlib.import_module('transfer_fixture.phone_setup')
# 5.10.286+: every POST names the active profile (X-DexHub-Profile); the fixture has one.
phone._scope.active_key=lambda:'fixture-profile'
backup=importlib.import_module('transfer_fixture.full_backup')
with tempfile.TemporaryDirectory() as tmp:
    home=Path(tmp);root=home/'fixture';root.mkdir();(root/'accounts.json').write_text('{"account":"fixture"}')
    sys.modules['xbmcvfs'].translatePath=lambda _:str(home)
    identifier=backup.ROOTS[0]
    backup.context=lambda:(home,{identifier:root},{identifier:{'api_key':'fixture'}},{'videoplayer.dexhubengine':1})
    backup.virtual_xml=lambda _: {'profiles/'+identifier+'/virtual.xml':b'<settings>persistent XML fixture</settings>'}
    session=phone.Session.__new__(phone.Session)
    session.token='protected-fixture';session.lock=threading.RLock();session.uploads={};session.changes=0;session.done=False
    handler=type('Handler',(phone._Handler,),{'session':session})
    server=ThreadingHTTPServer(('127.0.0.1',0),handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    baseurl='http://127.0.0.1:%d/'%server.server_port
    def request(route,data=None,headers=None,token=True):
        url=baseurl+(session.token+'/' if token else '')+route
        req=urllib.request.Request(url,data=data,headers=dict({'X-DexHub-Profile':'fixture-profile'},**(headers or {})))
        try:
            with urllib.request.urlopen(req,timeout=10) as response:return response.status,response.read()
        except urllib.error.HTTPError as e:return e.code,e.read()
    try:
        status,response=request('api/files',json.dumps({'op':'list','root':'files'}).encode())
        assert status==200 and json.loads(response)['entries']==[]
        status,response=request('api/files/upload?root=files&path=folder/test.txt',b'fixture contents')
        assert status==200 and json.loads(response)['ok']
        assert request('api/files/download?root=files&path=folder/test.txt')[1]==b'fixture contents'
        assert request('api/files/upload?root=files&path=../escape',b'fixture')[0]==400
        assert request('api/files/download?root=files&path=folder/test.txt',token=False)[0]==404
        assert request('api/files/upload?root=files&path=bad',b'fixture',{'Origin':'http://foreign.example'})[0]==403
        assert request('api/files/upload?root=files&path=empty',b'')[0]==200
        assert request('api/backup/full',token=False)[0]==404
        status,payload=request('api/backup/full');assert status==200
        archive=home/'download.zip';archive.write_bytes(payload)
        with ZipFile(archive) as z:
            assert json.loads(z.read('manifest.json'))['settings'][identifier]['api_key']=='fixture'
            assert b'persistent XML fixture' in z.read('profiles/'+identifier+'/virtual.xml')
        assert request('api/upload?name=x.ttf',b'\x00\x01\x00\x00fixture',{'Origin':'http://foreign.example'})[0]==403
        status,row=request('api/upload?name=Arabic.ttf',b'\x00\x01\x00\x00fixture');row=json.loads(row)
        assert status==200 and Path(row['path']).parent==home/'media/Fonts'
        status,row=request('api/upload?name=Arabic.srt',b'1\n00:00:00,000 --> 00:00:02,000\nArabic fixture')
        assert status==200 and json.loads(row)['applied'] and subtitles
        addon=home/'addon.zip'
        with ZipFile(addon,'w') as z:z.writestr('plugin.fixture/addon.xml','<addon id="plugin.fixture" version="1.0" name="Fixture"/>')
        status,row=request('api/upload?name=addon.zip',addon.read_bytes());row=json.loads(row);assert status==200
        status,response=request('api/transfer',json.dumps({'op':'install','upload_id':row['upload_id']}).encode())
        assert status==200 and json.loads(response)['queued'] and commands[-1].startswith('DexHub.InstallZip(')
        status,response=request('api/backup/restore',payload);assert status==200 and json.loads(response)['restart_required']
        assert (home/'dexhub-restore-pending/manifest.json').is_file()
        assert request('api/backup/restore',payload)[0]==400
        import shutil
        shutil.rmtree(home/'dexhub-restore-pending')
        descriptor=home/'fixture-addon/resources';descriptor.mkdir(parents=True)
        (descriptor/'settings.xml').write_text('<settings><setting id="api_key" type="text"/></settings>')
        sys.modules['xbmcaddon'].Addon=lambda _:types.SimpleNamespace(getAddonInfo=lambda key:str(descriptor.parent) if key=='path' else str(root))
        data={'format':'dexhub_backup','version':2,'parts':{'accounts':{'settings':{'api_key':'restored-fixture'}}}}
        status,response=request('api/backup/restore?name=settings.json',json.dumps(data).encode())
        assert status==200 and json.loads(response)['type']=='dexhub_json',response
        assert (root/'.dexhub-json-restore-pending.json').is_file()
        assert backup.context()[2][identifier]['api_key']=='fixture'
        assert request('api/backup/restore',payload)[0]==400
        assert request('api/backup/restore',b'{"format":"unrelated_json"}')[0]==400
        xbmc.executeJSONRPC=lambda _:json.dumps({'result':{'value':12}})
        _,response=request('api/transfer',json.dumps({'op':'install','upload_id':row['upload_id']}).encode())
        assert not json.loads(response)['ok']
    finally:server.shutdown();server.server_close();thread.join()
print('PASS: HTTP ZIP/JSON staged restore, unchanged live settings, fonts/subtitles/addon upload, token/origin and native-version checks')
