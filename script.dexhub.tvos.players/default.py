import json
import os
import sys
from urllib.parse import parse_qsl, quote, urlencode, urlsplit
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

mode = sys.argv[1] if len(sys.argv) > 1 else 'install-navigation'
if mode == 'ui-quality':
    sys.path.insert(0, os.path.dirname(__file__))
    from ui_quality import install
    install(force=True)
    xbmcgui.Dialog().ok('DexHub', 'تم ضبط جودة الخلفيات والصور. أعد تشغيل Kodi لتطبيقها. / Restart Kodi to apply artwork quality.')
    raise SystemExit()
if mode in ('home-back', 'install-navigation'):
    sys.path.insert(0, os.path.dirname(__file__))
    from dexhub_navigation import home_back, install_keymap
    if mode == 'home-back':
        home_back()
    else:
        install_keymap()
    raise SystemExit()

addon = xbmcaddon.Addon('plugin.video.dexhub.tvos')
sys.path.insert(0, xbmcvfs.translatePath(addon.getAddonInfo('path')))
from resources.lib.tvos_players import choose_once, external_link, media_filename, preference, stop_for_external, SESSION

if mode == 'preferences':
    choices = ['Kodi', 'Aether', 'External']
    current, external = preference(xbmc, addon)
    index = choices.index(current) if current in choices else 0
    selected = xbmcgui.Dialog().select('المشغل المفضل / Preferred player',
                                      ['Kodi', 'Aether', 'خارجي / External'], preselect=index)
    if selected >= 0:
        if choices[selected] == 'External':
            pick = xbmcgui.Dialog().select('المشغل الخارجي / External player',
                                          ['Infuse', 'VidHub'], preselect=1 if external == 'VidHub' else 0)
            if pick < 0:
                raise SystemExit()
            external = ['Infuse', 'VidHub'][pick]
        addon.setSetting('tvos_player', choices[selected])
        addon.setSetting('tvos_external_player', external)
        for setting, value in [('videoplayer.dexhubexternal', 1 if external == 'VidHub' else 0),
                               ('videoplayer.dexhubengine', selected)]:
            response = json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1,
                'method': 'Settings.SetSettingValue', 'params': {'setting': setting, 'value': value}})))
            if response.get('error'):
                xbmcgui.Dialog().ok('Dex Hub Apple TV', 'ثبّت بناء Kodi الجديد لتفعيل الإعداد العام. / Install the new native Kodi build for the global preference.')
                break
    raise SystemExit()
if mode == 'fonts':
    skin = xbmcaddon.Addon('skin.dexhub.tvos')
    source = xbmcvfs.translatePath(skin.getAddonInfo('path')) + '/fonts/'
    destination = 'special://home/media/Fonts/'
    xbmcvfs.mkdirs(destination)
    copied = 0
    failed = 0
    _, files = xbmcvfs.listdir(source)
    for name in files:
        if not name.lower().endswith(('.ttf', '.otf')) or name.lower().startswith('fa-'):
            continue
        target = destination + name
        if xbmcvfs.exists(target):
            continue
        if xbmcvfs.copy(source + name, target):
            copied += 1
        else:
            failed += 1
    xbmcgui.Dialog().ok('Dex Hub Apple TV',
                       'Fonts copied: %d; failed: %d. Restart Kodi, then Settings → Player → Subtitles → Font. / أعد تشغيل Kodi ثم اختر الخط من إعدادات المشغل ← الترجمة.' % (copied, failed))
    raise SystemExit()
if xbmc.getCondVisibility('System.Platform.TVOS'):
    if mode == 'choose-click':
        from player_choice import choose_and_play
        choose_and_play(xbmc, xbmcgui, xbmcaddon, choose_once,
                        sys.argv[2] if len(sys.argv) > 2 else '')
    elif mode == 'external':
        player = xbmc.Player()
        if player.isPlayingVideo():
            from resources.lib.trailer_mark import playing_is_trailer
            if playing_is_trailer(player):
                xbmcgui.Dialog().ok('DexHub', 'التريلر يعمل داخل Kodi. / Trailers stay in Kodi.')
                raise SystemExit()
            video = player.getPlayingFile()
            position = player.getTime()
            video, separator, encoded_headers = video.partition('|')
            headers = dict(parse_qsl(encoded_headers)) if separator else {}
            try:
                session = json.loads(xbmcgui.Window(10000).getProperty(SESSION) or '{}')
            except ValueError:
                session = {}
            if session.get('video') == video:
                headers = headers or session.get('headers') or {}
            else:
                session = {}
            dialog = xbmcgui.Dialog()
            if headers or urlsplit(video).scheme.lower() not in ('http', 'https'):
                dialog.ok('DexHub', 'هذا المصدر يحتاج المشغل الداخلي. / This source requires internal playback.')
            else:
                _, external = preference(xbmc, addon)
                selected = dialog.select('المشغل الخارجي / External player', ['Infuse', 'VidHub'], preselect=1 if external == 'VidHub' else 0)
                if selected >= 0:
                    props = json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'Player.GetProperties', 'params': {'playerid': 1, 'properties': ['currentsubtitle', 'subtitleenabled']}}))).get('result', {})
                    subtitle = ''
                    if props.get('subtitleenabled'):
                        name = str((props.get('currentsubtitle') or {}).get('name') or '')
                        matches = [row['url'] for row in session.get('tracks') or [] if name and name in (row.get('name'), os.path.basename(row.get('path') or ''), os.path.splitext(os.path.basename(row.get('path') or ''))[0])]
                        if len(matches) == 1:
                            subtitle = matches[0]
                        else:
                            tracks = session.get('tracks') or []
                            pick = dialog.select('الترجمة للخارجي / External subtitle', ['ترجمة مدمجة / Embedded subtitles'] + [row.get('name') or os.path.basename(row.get('path') or '') or 'Subtitle %d' % (i+1) for i, row in enumerate(tracks)])
                            if pick < 0:
                                raise SystemExit()
                            if pick > 0:
                                subtitle = tracks[pick-1]['url']
                    filename = session.get('filename') or ''
                    if not filename:
                        item = json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 2, 'method': 'Player.GetItem', 'params': {'playerid': 1, 'properties': ['title', 'showtitle', 'season', 'episode', 'year']}}))).get('result', {}).get('item', {})
                        filename = media_filename(metadata=item, video=video)
                    callbacks = None
                    if selected == 0:
                        from resources.lib.infuse_progress import prepare
                        total = player.getTotalTime()
                        callbacks = prepare(video, position, filename, session.get('context'), total)
                    target = external_link(video, position, [subtitle] if subtitle else [], ['Infuse', 'VidHub'][selected], filename, callbacks)
                    if not stop_for_external(xbmc, player):
                        dialog.ok('DexHub', 'تعذر إيقاف الفيديو؛ لم يُفتح المشغل الخارجي. / Video did not stop; external player not opened.')
                        raise SystemExit()
                    link = 'dex-external://play?' + urlencode({'target': target}, quote_via=quote)
                    xbmc.executebuiltin('System.OpenURL(%s)' % json.dumps(link))
