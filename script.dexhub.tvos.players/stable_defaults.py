"""Apply the requested Aether playback preference once, before restores."""
import json
import os


def install():
    import xbmc
    import xbmcaddon
    import xbmcvfs
    addon = xbmcaddon.Addon('plugin.video.dexhub.tvos')
    profile = xbmcvfs.translatePath(xbmcaddon.Addon('script.dexhub.tvos.players').getAddonInfo('profile'))
    marker = os.path.join(profile, 'aether-first-v18.done')
    if os.path.exists(marker):
        # Preserve Kodi/external choices; only migrate removed engine settings.
        current = json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,
            'method':'Settings.GetSettingValue','params':{'setting':'videoplayer.dexhubengine'}})))
        if current.get('result', {}).get('value') in (3, 4):
            xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,
                'method':'Settings.SetSettingValue','params':{'setting':'videoplayer.dexhubengine','value':1}}))
            addon.setSetting('tvos_player', 'Aether')
        elif addon.getSetting('tvos_player') in ('KSPlayer', 'MPV'):
            addon.setSetting('tvos_player', 'Aether')
        return
    response = json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,
        'method':'Settings.SetSettingValue','params':{'setting':'videoplayer.dexhubengine','value':1}})))
    if response.get('result') is not True:
        xbmc.log('DexHub: Aether preference remains pending', xbmc.LOGWARNING)
        return
    addon.setSetting('tvos_player', 'Aether')
    addon.setSetting('subtitle_search_mode', 'Play with subtitles')
    os.makedirs(profile, exist_ok=True)
    with open(marker, 'w', encoding='utf-8') as handle:
        handle.write('Aether; subtitles in background\n')
    xbmc.log('DexHub: Aether default, background subtitles; future user changes retained', xbmc.LOGINFO)
