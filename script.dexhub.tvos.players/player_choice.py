"""Capture the original skin play query before opening the selection dialog."""
from urllib.parse import parse_qsl


def choose_and_play(xbmc, gui, addon, choose_once, supplied=''):
    query = supplied or xbmc.getInfoLabel('ListItem.Property(dhs.q)')
    query = query.lstrip('?&')
    if not query or '\n' in query or '\r' in query:
        gui.Dialog().ok('DexHub', 'اختر العمل أولاً. / Select a title first.')
        return False
    # Never accept a second action or an alternate plugin from a metadata query.
    if any(key == 'action' for key, _ in parse_qsl(query)):
        gui.Dialog().ok('DexHub', 'Invalid playback query')
        return False
    if not choose_once(xbmc, gui, addon):
        return False
    xbmc.executebuiltin('RunPlugin("plugin://plugin.video.dexhub.tvos/?action=skin_play&%s")' %
                        query.replace('"', '%22'))
    return True
