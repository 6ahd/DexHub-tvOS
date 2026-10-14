import json
import xbmc
import xbmcgui

dialog = xbmcgui.Dialog()
choice = dialog.select('DexHub native player test', ['Aether + skin controls', 'Kodi', 'Infuse', 'VidHub'])
if choice < 0:
    raise SystemExit()
source = dialog.select('Video source', ['Public test clip', 'Enter URL'])
if source < 0:
    raise SystemExit()
url = 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4' if source == 0 else dialog.input('Video URL')
if not url:
    raise SystemExit()
subtitle = dialog.input('Subtitle URL or local file — optional')
item = xbmcgui.ListItem(path=url)
item.setProperty('dexhub.playercore', ['Aether', 'VideoPlayer', 'Infuse', 'VidHub'][choice])
if subtitle:
    item.setSubtitles([subtitle])
xbmc.Player().play(url, item)
