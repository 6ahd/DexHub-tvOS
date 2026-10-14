"""Apple TV Back routing; leaves other platforms and user keymaps untouched."""
import os

import xbmc
import xbmcgui
import xbmcvfs

NAME = 'zzzzzz_dexhub_tvos_navigation.xml'
MARKER = '<!-- DexHub Apple TV navigation -->'
HOME_ACTION = 'RunScript(script.dexhub.tvos.players,home-back)'


def bindings(action):
    return '''
    <keyboard>
      <backspace>{0}</backspace>
      <browser_back>{0}</browser_back>
      <escape>{0}</escape>
    </keyboard>
    <remote><back>{0}</back><menu>{0}</menu></remote>
    <joystick profile="game.controller.default"><b>{0}</b><back>{0}</back></joystick>
    <gamepad><B>{0}</B><back>{0}</back></gamepad>
    <customcontroller name="AppleRemote"><button id="6">{0}</button></customcontroller>
    <customcontroller name="SiriRemote"><button id="6">{0}</button></customcontroller>
'''.format(action)


CONTENT = ('<?xml version="1.0" encoding="UTF-8"?>\n' + MARKER + '\n<keymap>\n'
           + '<Home>' + bindings(HOME_ACTION) + '</Home>\n'
           + '<FullscreenVideo>' + bindings('FullScreen') + '</FullscreenVideo>\n'
           + '<VideoOSD>' + bindings('Dialog.Close(videoosd)') + '</VideoOSD>\n'
           + '</keymap>\n')


def install_keymap():
    if not xbmc.getCondVisibility('System.Platform.TVOS'):
        return False
    folder = xbmcvfs.translatePath('special://profile/keymaps/')
    path = os.path.join(folder, NAME)
    if os.path.isfile(path):
        with open(path, encoding='utf-8') as handle:
            previous = handle.read()
        if previous == CONTENT:
            return True
        if MARKER not in previous:
            xbmc.log('[DexHub] navigation keymap name is occupied; left unchanged', xbmc.LOGWARNING)
            return False
    os.makedirs(folder, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(CONTENT)
    xbmc.executebuiltin('Action(reloadkeymaps)')
    return True


def home_back():
    if not xbmc.getCondVisibility('System.Platform.TVOS'):
        return
    if xbmcgui.getCurrentWindowId() != 10000:
        return
    if xbmc.getCondVisibility('System.HasActiveModalDialog'):
        return
    home = xbmcgui.Window(10000)
    busy = 'dexhub.tvos.exit.confirming'
    if home.getProperty(busy):
        return
    if xbmc.Player().isPlayingVideo():
        xbmc.executebuiltin('ActivateWindow(fullscreenvideo)')
        return
    home.setProperty(busy, '1')
    try:
        if xbmcgui.Dialog().yesno('Dex Hub Apple TV', 'الخروج من Kodi؟ / Exit Kodi?',
                                 nolabel='لا / Stay', yeslabel='خروج / Exit'):
            xbmc.executebuiltin('Quit')
    finally:
        home.clearProperty(busy)
