import ast
from pathlib import Path
from zipfile import ZipFile

base=Path(__file__).resolve().parents[1]
with ZipFile(base/'assets/plugin.video.themoviedb.helper-6.17.9+appletv.2.zip') as archive:
    source=archive.read('plugin.video.themoviedb.helper/resources/tmdbhelper/lib/monitor/player.py').decode()
node=next(node for node in ast.walk(ast.parse(source)) if isinstance(node,ast.FunctionDef) and node.name=='get_playingitem')
namespace={};exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'tmdb-stop-fixture','exec'),namespace)
class Player:
    resets=0
    def getPlayingFile(self):raise RuntimeError('Kodi is not playing any file')
    def reset_properties(self):self.resets+=1
player=Player();namespace['get_playingitem'](player)
assert player.resets==1
print('PASS: actual packaged TMDb callback handles stopped playback without propagating RuntimeError')
