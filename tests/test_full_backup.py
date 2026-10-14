import importlib.util
import json
import sqlite3
import tempfile
import warnings
from pathlib import Path
from zipfile import ZipFile

base = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('full_backup', base/'src/plugin.video.dexhub.tvos/resources/lib/full_backup.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp); profile = root/'source'; profile.mkdir()
    (profile/'unknown-new-settings.json').write_text('{"custom":true}')
    (profile/'accounts.json').write_text('{"account":"private-fixture"}')
    (profile/'cache').mkdir(); (profile/'cache/skipped').write_text('cached')
    db = sqlite3.connect(profile/'resume #1.db')
    db.execute('PRAGMA journal_mode=WAL'); db.execute('CREATE TABLE resume(seconds INTEGER)')
    db.execute('INSERT INTO resume VALUES(1234)'); db.commit()
    fonts = root/'fonts'; fonts.mkdir(); (fonts/'Arabic.ttf').write_bytes(b'\x00\x01\x00\x00font')
    archive = root/'backup.zip'; identifier = module.ROOTS[0]
    virtual={'profiles/'+identifier+'/virtual-settings.xml':b'<settings><setting id="skin">restored</setting></settings>'}
    manifest = module.create_archive(archive, {identifier:profile}, {identifier:{'effective':'NSUserDefaults-fixture'}}, {'videoplayer.dexhubengine':1}, fonts, virtual)
    db.close()
    assert not any('cache/' in name or name.endswith('-wal') for name in manifest['files'])
    home = root/'home'; home.mkdir(); live = home/'userdata/addon_data'/identifier; live.mkdir(parents=True)
    (live/'accounts.json').write_text('existing-data')
    result = module.stage_restore(archive, home)
    assert result['restart_required'] and (live/'accounts.json').read_text()=='existing-data'
    pending = home/'dexhub-restore-pending'
    snapshot = sqlite3.connect(pending/'profiles'/identifier/'resume #1.db')
    assert snapshot.execute('SELECT seconds FROM resume').fetchone()==(1234,); snapshot.close()
    assert (pending/'fonts/Arabic.ttf').is_file()
    assert b'restored' in (pending/'profiles'/identifier/'virtual-settings.xml').read_bytes()
    assert json.loads((pending/'manifest.json').read_text())['settings'][identifier]['effective']=='NSUserDefaults-fixture'
    try: module.stage_restore(archive, home); raise AssertionError('duplicate restore accepted')
    except ValueError: pass
    for kind in ('traversal','duplicate','checksum','limit'):
        bad = root/(kind+'.zip')
        with ZipFile(archive) as source, ZipFile(bad,'w') as target:
            for item in source.infolist():
                data = source.read(item)
                if kind=='checksum' and item.filename.endswith('accounts.json'):data=b'corrupt'
                target.writestr(item,data)
            if kind=='traversal':target.writestr('../escape','unsafe')
            if kind=='duplicate':
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore'); target.writestr('manifest.json',source.read('manifest.json'))
        before=module.LIMIT
        if kind=='limit':module.LIMIT=1
        try:
            module.stage_restore(bad,root/('reject-'+kind)); raise AssertionError(kind+' accepted')
        except ValueError:pass
        finally:module.LIMIT=before
        assert not list((root/('reject-'+kind)).glob('.dexhub-restore-*'))
    font = root/'font.otf'; font.write_bytes(b'OTTOvalid-font-fixture')
    row=module.receive_file(font,home,'Custom.otf');assert Path(row['path']).parent==home/'media/Fonts'
    addon=root/'addon.zip'
    with ZipFile(addon,'w') as z:z.writestr('plugin.fixture/addon.xml','<addon id="plugin.fixture" version="1.0" name="Fixture"/>')
    row=module.receive_file(addon,home,'addon.zip');assert row['addon_id']=='plugin.fixture'
    with ZipFile(addon,'a') as z:z.writestr('../outside','bad')
    before=set((home/'dexhub-imports').iterdir())
    try:module.receive_file(addon,home,'bad.zip');raise AssertionError('unsafe addon accepted')
    except ValueError:pass
    assert set((home/'dexhub-imports').iterdir())==before
print('PASS: complete profiles, effective settings, live WAL snapshot, staged restore, fonts/uploads and rejected invalid archives')
