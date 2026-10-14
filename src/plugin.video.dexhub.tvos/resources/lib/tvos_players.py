"""Direct tvOS playback and one-shot player overrides."""
import json
import math
import time
from urllib.parse import parse_qsl, quote, urlencode, urlsplit

OVERRIDE = 'dexhub.tvos.player.override'
# v5.10.296: every tvOS player that takes a video by link. Each entry says what
# it receives: time (resume position) and subtitles. The first two keep Kodi's
# own setting values (videoplayer.dexhubexternal 0 and 1).
EXTERNALS = ('Infuse', 'VidHub', 'SenPlayer', 'VLC', 'Native Player', 'Outplayer', 'nPlayer')
EXTERNAL_DETAIL = {
    'Infuse': 'الوقت والترجمة / Time and subtitles',
    'VidHub': 'الوقت والترجمة / Time and subtitles',
    'SenPlayer': 'الوقت والترجمة / Time and subtitles',
    'Native Player': 'الوقت والترجمة / Time and subtitles',
    'VLC': 'الترجمة فقط / Subtitles only',
    'Outplayer': 'الرابط فقط / Link only',
    'nPlayer': 'الرابط فقط / Link only',
}
SESSION = 'dexhub.tvos.player.session'


def preference(xbmc, addon):
    def value(setting):
        result = json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1,
            'method': 'Settings.GetSettingValue', 'params': {'setting': setting}})))
        return result.get('result', {}).get('value')
    try:
        engine = value('videoplayer.dexhubengine')
        external = value('videoplayer.dexhubexternal')
        if engine in (0, 1, 2, 3, 4) and external in (0, 1):
            return (['Kodi', 'Aether', 'External'][engine] if engine < 3 else 'Aether'), _external_app(addon, ['Infuse', 'VidHub'][external])
    except (AttributeError, ValueError, TypeError):
        pass
    engine = addon.getSetting('tvos_player') or 'Aether'
    return (engine if engine in ('Kodi', 'Aether', 'External') + EXTERNALS else 'Aether'), _external_app(addon, 'Infuse')


def _external_app(addon, fallback):
    """The chosen external app. Kodi's own setting only knows Infuse and VidHub,
    so a newer app lives in the add-on setting."""
    try:
        chosen = addon.getSetting('tvos_external_player')
    except AttributeError:
        chosen = ''
    return chosen if chosen in EXTERNALS[2:] else fallback


def choose_once(xbmc, xbmcgui, xbmcaddon):
    if not xbmc.getCondVisibility('System.Platform.TVOS'):
        return False
    dialog = xbmcgui.Dialog()
    choices = [('Aether', 'داخلي • تشغيل بتصميم السكين / Internal', 'Aether'),
               ('Kodi', 'داخلي • توافق Kodi / Internal', 'Kodi')]
    choices += [(name, 'خارجي • ' + EXTERNAL_DETAIL[name], 'External') for name in EXTERNALS]
    rows = []
    for title, detail, _ in choices:
        row = xbmcgui.ListItem(label=title, label2=detail)
        row.setArt({'icon': 'special://home/addons/skin.dexhub.tvos/media/dexhub/' +
                    ('external-player.png' if title in EXTERNALS else 'btn_play.png')})
        rows.append(row)
    selected = dialog.select('اختر المشغل — يبدأ البحث مباشرة / Play using', rows, useDetails=True)
    if selected < 0:
        return False
    value = choices[selected][2]
    _, external = preference(xbmc, xbmcaddon.Addon('plugin.video.dexhub.tvos'))
    if value == 'External':
        external = choices[selected][0]
    xbmcgui.Window(10000).setProperty(OVERRIDE, json.dumps({'player': value, 'external': external, 'time': time.time()}))
    return True


def remote_subtitles(rows):
    result = []
    for row in rows or []:
        sub = row.get('subtitle') or {}
        url = str(sub.get('url') or sub.get('key') or row.get('path') or '')
        if urlsplit(url).scheme.lower() in ('http', 'https') and '|' not in url:
            result.append({'url': url, 'path': str(row.get('path') or ''), 'name': str(sub.get('name') or sub.get('display_name') or '')})
    return result


def media_filename(item=None, metadata=None, video=''):
    """Name the temporary external item without changing its signed URL."""
    metadata = dict(metadata or {})
    if item is not None:
        try:
            tag = item.getVideoInfoTag()
            metadata.update(title=tag.getTitle(), showtitle=tag.getTVShowTitle(),
                            season=tag.getSeason(), episode=tag.getEpisode(), year=tag.getYear())
        except (AttributeError, RuntimeError):
            pass
        try:
            metadata['label'] = item.getLabel()
        except AttributeError:
            pass
    title = metadata.get('showtitle') or metadata.get('title') or metadata.get('label') or ''
    title = str(title).replace('/', '-').replace('\\', '-').replace('\n', ' ').strip()
    if not title:
        return ''
    try:
        season, episode = int(metadata.get('season', -1)), int(metadata.get('episode', -1))
        year = int(metadata.get('year', 0))
    except (TypeError, ValueError):
        season, episode, year = -1, -1, 0
    if episode >= 0 and season >= 0:
        title += ' S%02dE%02d' % (season, episode)
    elif year > 0:
        title += ' (%d)' % year
    extension = urlsplit(video).path.rsplit('.', 1)[-1].lower()
    return title + '.' + (extension if extension in ('mkv', 'mp4', 'm4v', 'mov', 'ts', 'avi', 'webm') else 'mkv')


def external_link(video, position, subtitles, external, filename='', callbacks=None, title=''):
    """The app's own link: video, resume time and subtitles where it takes them.

    The selected subtitle is always first; Infuse and SenPlayer get the others
    too (up to eight) so they can be switched inside the app."""
    seconds = str(int(max(0, float(position or 0))))
    subtitles = [s for s in (subtitles or []) if s]
    encode = lambda query: urlencode(query, quote_via=quote)
    if external == 'VLC':
        query = [('url', video)] + [('sub', s) for s in subtitles[:1]]
        return 'vlc-x-callback://x-callback-url/stream?' + encode(query)
    if external == 'Outplayer':
        query = [('url', video)] + ([('filename', filename)] if filename else [])
        return 'outplayer://x-callback-url/play?' + encode(query)
    if external == 'nPlayer':
        scheme, _sep, rest = video.partition('://')
        return 'nplayer-%s://%s' % (scheme.lower(), quote(rest, safe=":/?&=%@+;,~!$'()*[]#"))
    if external == 'Native Player':
        query = [('url', video), ('position', seconds)]
        if title or filename:
            query.append(('name', title or filename))
        query += [('sub', s) for s in subtitles
                  if s.lower().split('?', 1)[0].endswith(('.srt', '.sub'))][:8]
        return 'nativeplayer://play?' + encode(query)
    query = [('url', video), ('position', seconds)]
    many = external in ('Infuse', 'SenPlayer')
    query += [('sub', s) for s in (subtitles[:8] if many else subtitles[:1])]
    if filename:
        query.append(('filename', filename))
    if external == 'Infuse' and callbacks:
        query.extend((key, callbacks[key]) for key in ('x-success', 'x-error'))
    scheme = {'VidHub': 'open-vidhub', 'SenPlayer': 'senplayer'}.get(external, 'infuse')
    return scheme + '://x-callback-url/play?' + encode(query)


def _positive(value):
    try:
        number = float(value or 0)
        return number if math.isfinite(number) and number > 0 else 0.0
    except (TypeError, ValueError):
        return 0.0


def external_resume(api, position, item, ctx):
    """Resolve a requested resume to seconds before leaving Kodi."""
    ctx = ctx or {}
    seconds = _positive(position) or _positive(ctx.get('resume_seconds'))
    percent = _positive(ctx.get('resume_percent'))
    duration = _positive(ctx.get('duration')) or _positive(ctx.get('duration_s')) or _positive(ctx.get('duration_ms')) / 1000
    duration = duration or _positive((ctx.get('kodi_info') or {}).get('duration'))
    try:
        duration = duration or _positive(item.getVideoInfoTag().getDuration())
    except (AttributeError, RuntimeError):
        pass
    action = ''
    try:
        action = dict(parse_qsl(api.sys.argv[2].lstrip('?'))).get('action', '')
    except (AttributeError, IndexError, TypeError):
        pass
    if action == 'cw_play_from_start':
        return 0.0, duration
    try:
        seconds = seconds or _positive(item.getProperty('ResumeTime'))
    except AttributeError:
        pass
    requested = seconds > 0 or percent > 0 or action in ('cw_resume', 'native_resume')
    identities = (ctx.get('canonical_id'), ctx.get('tmdb_id'), ctx.get('imdb_id'), ctx.get('tvdb_id'))
    if requested and any(identities) and (seconds <= 0 or duration <= 0):
        try:
            row = api.playback_store.find_resume_entry(
                media_type=ctx.get('media_type') or ('series' if ctx.get('episode') else 'movie'),
                canonical_id=ctx.get('canonical_id') or '', tmdb_id=ctx.get('tmdb_id') or '',
                imdb_id=ctx.get('imdb_id') or '', tvdb_id=ctx.get('tvdb_id') or '',
                season=ctx.get('season'), episode=ctx.get('episode')) or {}
            seconds = seconds or _positive(row.get('position'))
            duration = duration or _positive(row.get('duration'))
            percent = percent or _positive(row.get('percent'))
        except (AttributeError, RuntimeError, ValueError):
            pass
    if seconds <= 0 and 0 < percent < 100 and duration > 0:
        seconds = duration * percent / 100
    if seconds <= 0 and percent > 0:
        return None, duration
    return seconds, duration


def stop_for_external(xbmc, player=None, timeout=5):
    """Let Kodi finish stopping its video before tvOS backgrounds the app."""
    player = player or xbmc.Player()
    if not player.isPlayingVideo():
        return True
    player.stop()
    monitor = xbmc.Monitor()
    deadline = time.monotonic() + timeout
    while player.isPlayingVideo():
        if time.monotonic() >= deadline or monitor.waitForAbort(0.05):
            return False
    return not monitor.waitForAbort(0.1)


def handoff(api, stream_url, rows, selected_path, position, item, ctx=None):
    import xbmcaddon
    if not api.xbmc.getCondVisibility('System.Platform.TVOS'):
        return False
    if item.getProperty('dexhub.trailer') == '1':
        item.setProperty('dexhub.playercore', 'VideoPlayer')
        return False
    addon = xbmcaddon.Addon('plugin.video.dexhub.tvos')
    engine, external = preference(api.xbmc, addon)
    if engine in EXTERNALS:
        external, engine = engine, 'External'
    home = api.xbmcgui.Window(10000)
    raw = home.getProperty(OVERRIDE)
    home.clearProperty(OVERRIDE)
    if raw:
        try:
            override = json.loads(raw)
            if 0 <= time.time() - float(override['time']) < 600:
                engine, external = override['player'], override['external']
        except (ValueError, KeyError, TypeError):
            pass
    video, separator, raw_headers = str(stream_url).partition('|')
    headers = dict(parse_qsl(raw_headers)) if separator else {}
    tracks = remote_subtitles(rows)
    selected = next((row['url'] for row in tracks if row['path'] == selected_path), '')
    filename = media_filename(item, video=video)
    item.setProperty('dexhub.external.filename', filename)
    item.setProperty('dexhub.external.context', json.dumps(ctx or {}))
    home.setProperty(SESSION, json.dumps({'video': video, 'headers': headers, 'tracks': tracks, 'selected': selected, 'filename': filename, 'context': ctx or {}}))
    if engine == 'Kodi':
        item.setProperty('dexhub.playercore', 'VideoPlayer')
        return False
    if urlsplit(video).scheme.lower() not in ('http', 'https'):
        api.xbmcgui.Dialog().ok('DexHub', 'هذا المصدر يعمل بمشغل Kodi. / This source requires Kodi.')
        item.setProperty('dexhub.playercore', 'VideoPlayer')
        return False
    if engine == 'External':
        if headers:
            api.xbmcgui.Dialog().ok('DexHub', 'هذا المصدر يحتاج رؤوس طلب. سيستخدم Kodi. / HTTP headers required; using Kodi.')
            item.setProperty('dexhub.playercore', 'VideoPlayer')
            return False
        position, duration = external_resume(api, position, item, ctx)
        if position is None:
            api.xbmcgui.Dialog().ok('DexHub', 'الاستكمال نسبة فقط والمدة غير متاحة؛ سيستخدم Kodi حتى لا يبدأ من الصفر. / Resume duration unavailable; using Kodi instead of starting over.')
            item.setProperty('dexhub.playercore', 'VideoPlayer')
            return False
        callbacks = None
        if external == 'Infuse':
            from .infuse_progress import prepare
            callbacks = prepare(video, position, filename, ctx, duration)
        # v5.10.296: the selected subtitle first, then the other found ones
        ordered = ([selected] if selected else []) + [row['url'] for row in tracks if row['url'] != selected]
        link = 'dex-external://play?' + urlencode({'target': external_link(video, position, ordered, external, filename, callbacks, title=filename.rsplit('.', 1)[0])}, quote_via=quote)
        if not stop_for_external(api.xbmc):
            api.xbmcgui.Dialog().ok('DexHub', 'تعذر إيقاف الفيديو؛ لم يُفتح المشغل الخارجي. / Video did not stop; external player not opened.')
            return True
        api.xbmc.executebuiltin('System.OpenURL(%s)' % json.dumps(link))
        return True
    item.setProperty('dexhub.playercore', 'Aether')
    item.setProperty('dexhub.aether.subtitles', json.dumps([selected or selected_path] if selected or selected_path else []))
    if position and float(position) > 0:
        item.setProperty('StartOffset', '%.3f' % float(position))
    # Close the launching modal before the native fullscreen request arrives.
    if api.xbmc.getCondVisibility('Window.IsVisible(movieinformation)'):
        api.xbmc.executebuiltin('Dialog.Close(movieinformation,true)', True)
    return False
