import base64, importlib, json, sys, tempfile
from pathlib import Path
from types import ModuleType, SimpleNamespace
from zipfile import ZipFile

base=Path(__file__).resolve().parents[1]
pkg=ModuleType('restore_fixture');pkg.__path__=[str(base/'src/plugin.video.dexhub.tvos/resources/lib')]
sys.modules['restore_fixture']=pkg
sys.modules['xbmc']=SimpleNamespace()
sys.modules['xbmcgui']=SimpleNamespace()
sys.modules['xbmcvfs']=SimpleNamespace()
sys.modules['xbmcaddon']=SimpleNamespace()
module=importlib.import_module('restore_fixture.json_restore')
backup=importlib.import_module('restore_fixture.backup')
full=importlib.import_module('restore_fixture.full_backup')
def encoded(value):return base64.b64encode(json.dumps(value).encode()).decode()
allowed={'theme','bucket_art_map'}
data={'format':'dexhub_backup','version':2,'parts':{
    'settings':{'settings':{'theme':'blue','unknown-old-setting':'ignored'}},
    'sources':{'files':{'providers.json':encoded([{'name':'Fixture'}])}},
    'progress':{'playback':[{'canonical_id':'tt123','position':321}]}}}
parsed=module.normalize(data,allowed)
assert parsed['parts']['settings']['settings']=={'theme':'blue'}
old=module.normalize({'dexhub_export_version':1,'settings':{'theme':'old'},'providers':[],
                      'catalog_pins':[],'bucket_art_map':{}},allowed)
assert base64.b64decode(old['parts']['sources']['files']['providers.json'])==b'[]'
for invalid in [[],{'format':'nuvio_collection'}, {'format':'dexhub_backup','version':99,'parts':{}},
    {'format':'dexhub_backup','version':2,'parts':{'sources':{'files':{'../escape':encoded({})}}}},
    {'format':'dexhub_backup','version':2,'parts':{'sources':{'files':{'providers.json':'bad-base64'}}}}]:
    try:module.normalize(invalid,allowed);raise AssertionError('Invalid backup accepted')
    except (ValueError,TypeError):pass
with tempfile.TemporaryDirectory() as directory:
    home=Path(directory);profile=home/'userdata/addon_data/plugin.video.dexhub.tvos';profile.mkdir(parents=True)
    (profile/'providers.json').write_text('["existing"]')
    desc=home/'addon/resources';desc.mkdir(parents=True);(desc/'settings.xml').write_text('<settings><setting id="theme" type="text"/></settings>')
    sys.modules['xbmcaddon'].Addon=lambda _:SimpleNamespace(getAddonInfo=lambda key:str(home/'addon') if key=='path' else str(profile))
    full.context=lambda:(home,{'plugin.video.dexhub.tvos':profile},{'plugin.video.dexhub.tvos':{'theme':'previous'}},{})
    full.virtual_xml=lambda _:{}
    upload=home/'settings.json';upload.write_text(json.dumps(data))
    assert module.stage(upload,home)['restart_required']
    assert (profile/'providers.json').read_text()=='["existing"]'
    archives=list((home/'dexhub-json-restore-backups').glob('*.zip'));assert len(archives)==1
    with ZipFile(archives[0]) as z:assert z.read('profiles/plugin.video.dexhub.tvos/providers.json')==b'["existing"]'
    assert (profile/module.PENDING).is_file()
    try:module.stage(upload,home);raise AssertionError('Duplicate staged restore')
    except ValueError:pass
    try:full.stage_restore(archives[0],home);raise AssertionError('ZIP overwrote pending JSON')
    except ValueError:pass
    sys.modules['xbmcvfs'].translatePath=lambda path:path
    events=[]
    sys.modules['xbmc'].Player=lambda:SimpleNamespace(isPlayingVideo=lambda:False)
    sys.modules['xbmc'].executebuiltin=events.append
    restored=[];backup.restore=lambda d,p,strict:restored.append((d,p,strict))
    assert module.apply_pending() and restored[0][2] and not (profile/module.PENDING).exists()
    assert events==['ReloadSkin()']
print('PASS: old/new DexHub JSON, allowed settings/files, deferred restore, rollback backup, duplicate/conflict rejection.')
