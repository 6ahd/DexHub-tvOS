"""Trailer preferences shared by native settings, phone setup and playback."""
import math


def volume_level(value):
    try:
        number = float(value)
        if not math.isfinite(number):
            return 30
        return max(0, min(100, int(number)))
    except (TypeError, ValueError, OverflowError):
        return 30


MODES = ('background', 'card')


def display_mode(value=None):
    """v5.10.326: background (the whole screen) or card (inside the focused
    Spotlight card of a row, skin.dexhub 3.28.70); anything else is background."""
    return value if value in MODES else 'background'


_MEMO = {'at': 0.0, 'scope': None, 'values': None}
_MEMO_TTL = 30.0


def invalidate():
    """v5.10.289: forget the remembered trailer values (a setting changed)."""
    _MEMO['values'] = None


def _values(scope):
    """v5.10.289: the trailer watcher publishes these on every tick (4 a second
    while the remote is in use); read them from Kodi at most every 30 s."""
    import time
    now = time.monotonic()
    if _MEMO['values'] is None or _MEMO['scope'] != scope or now - _MEMO['at'] > _MEMO_TTL:
        import xbmcaddon
        addon = xbmcaddon.Addon('plugin.video.dexhub.tvos')
        _MEMO.update(at=now, scope=scope, values={
            'mode': addon.getSetting('homeui_trailer_mode'),
            'trailers': addon.getSetting('homeui_trailers'),
            'lang': (addon.getSetting('ui_language') or '').lower()})
    return _MEMO['values']


def publish_presentation(mode=None):
    """Publish layout without starting/importing the video service or resolver."""
    import xbmcgui
    from . import profile_scope
    if not profile_scope.is_current():
        return
    scope = profile_scope.key()
    values = _values(scope)
    home = xbmcgui.Window(10000)
    mode = display_mode(values.get('mode'))
    enabled = '0' if values['trailers'] == 'false' else '1'
    for key, value in (('dhs.trailer.mode', mode), ('dhs.trailer.enabled', enabled),
                       ('dhs.trailer.config.scope', scope)):
        if home.getProperty(key) != value:
            home.setProperty(key, value)
    return mode


def publish_status(state):
    import xbmcaddon
    import xbmcgui
    from . import profile_scope
    if not profile_scope.is_current():
        return
    labels = {
        'disabled': ('التريلرات متوقفة — شغّلها من القائمة ← الرئيسية', 'Trailers are off — enable them in Menu > Home'),
        'waiting': ('توقف على عمل لبدء التريلر', 'Select a title to start its trailer'),
        'loading': ('جار تحميل التريلر…', 'Loading trailer…'),
        'unavailable': ('لا يتوفر تريلر قابل للتشغيل لهذا العمل', 'No playable trailer is available for this title'),
        'error': ('تعذر بدء خدمة التريلر — أعد تشغيل Kodi', 'Trailer service could not start — restart Kodi'),
        'playing': ('', ''),
    }
    lang = _values(profile_scope.key())['lang']
    home = xbmcgui.Window(10000)
    notice = labels.get(state, labels['waiting'])[1 if lang == 'english' else 0]
    if home.getProperty('dhs.trailer.status') != state:
        home.setProperty('dhs.trailer.status', state)
    if home.getProperty('dhs.trailer.notice') != notice:
        home.setProperty('dhs.trailer.notice', notice)


def write_setting(key, value):
    """Do not claim success if Kodi rejects a value against its setting schema."""
    import xbmcaddon
    from . import profile_scope
    profile_scope.require_current()
    value = str(value)
    addon = xbmcaddon.Addon('plugin.video.dexhub.tvos')
    if addon.setSetting(key, value) is False:
        raise RuntimeError('Kodi rejected the trailer setting; update the add-on and restart Kodi')
    # A fresh handle verifies the value other invocations will read.
    saved = xbmcaddon.Addon('plugin.video.dexhub.tvos').getSetting(key)
    if saved != value:
        raise RuntimeError('Trailer setting was not saved; update the add-on and restart Kodi')
    invalidate()
    if key in ('homeui_trailer_mode', 'homeui_trailers'):
        publish_presentation()
    if key == 'homeui_trailer_mode':
        # the poster rows change shape: the Home's rows are published again
        try:
            from .homeui.layout import _skin_follows
            _skin_follows()
        except Exception:
            pass
    return saved
