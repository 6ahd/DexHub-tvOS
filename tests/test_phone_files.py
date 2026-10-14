"""File operations preserve replaced data and reject sandbox escapes."""
import importlib.util
import tempfile
from pathlib import Path
from zipfile import ZipFile

base = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('phone_files', base/'src/plugin.video.dexhub.tvos/resources/lib/phone_files.py')
files = importlib.util.module_from_spec(spec)
spec.loader.exec_module(files)

def fails(call):
    try:
        call()
    except (ValueError, FileExistsError):
        return
    raise AssertionError('Expected rejection')

with tempfile.TemporaryDirectory() as temporary:
    home = Path(temporary)/'home'; home.mkdir()
    incoming = Path(temporary)/'incoming'; incoming.write_bytes(b'old')
    files.upload(home, 'files', 'series/subs/ar.srt', incoming)
    assert files.operate(home, {'path':'series/subs'})['entries'][0]['name'] == 'ar.srt'
    incoming.write_bytes(b'new')
    fails(lambda: files.upload(home, 'files', 'series/subs/ar.srt', incoming))
    files.upload(home, 'files', 'series/subs/ar.srt', incoming, replace=True)
    assert list((home/'dexhub-file-trash').iterdir())[0].read_bytes() == b'old'
    files.operate(home, {'op':'copy', 'path':'series', 'target':'copied'})
    files.operate(home, {'op':'move', 'path':'copied', 'target_root':'imports', 'target':'moved'})
    assert (home/'dexhub-imports/moved/subs/ar.srt').read_bytes() == b'new'
    path, name, cleanup = files.download(home, 'imports', 'moved')
    with ZipFile(path) as archive:
        assert archive.read('moved/subs/ar.srt') == b'new'
    assert name == 'moved.zip' and cleanup; path.unlink()
    fails(lambda: files.operate(home, {'op':'copy', 'path':'series', 'target':'series/child'}))
    fails(lambda: files.upload(home, 'files', '../escape', incoming))
    fails(lambda: files.upload(home, 'addons', 'plugin.fixture/file.py', incoming))
    (home/'dexhub-files/link').symlink_to(Path(temporary))
    fails(lambda: files.upload(home, 'files', 'link/escape', incoming))
    fails(lambda: files.download(home, 'files', 'link/incoming'))
    fails(lambda: files.operate(home, {'op':'trash', 'path':''}))
    files.operate(home, {'op':'trash', 'root':'imports', 'path':'moved'})
    assert not (home/'dexhub-imports/moved').exists()
    incoming.write_bytes(b'')
    files.upload(home, 'files', 'empty.txt', incoming)
    assert (home/'dexhub-files/empty.txt').stat().st_size == 0
print('PASS: folder upload/download, replace with trash, copy/move, empty files, roots/path/symlink guards')
