"""Restore known missing AF3 assets without rewriting the skin XML."""
import os
import xbmc
import xbmcaddon
import xbmcvfs


def repair():
    if not xbmc.getCondVisibility('System.Platform.TVOS'):
        return [], []
    own = xbmcvfs.translatePath(xbmcaddon.Addon('script.module.dexhub.tvos.compat').getAddonInfo('path'))
    repaired, failed = [], []
    for addon_id in ('skin.arctic.fuse.3', 'skin.dexhub.tvos'):
        try:
            root = xbmcvfs.translatePath(xbmcaddon.Addon(addon_id).getAddonInfo('path'))
        except RuntimeError:
            continue
        for relative, asset in (
            ('fonts/LeagueSpartan-ExtraBold.ttf', 'LeagueSpartan-ExtraBold.ttf'),
            ('extras/backgrounds/blur/purle_blur.jpg', 'purple_blur.jpg'),
            ('extras/backgrounds/blur/purple_blur.jpg', 'purple_blur.jpg'),
        ):
            destination = os.path.join(root, relative)
            if xbmcvfs.exists(destination):
                continue
            xbmcvfs.mkdirs(os.path.dirname(destination))
            if xbmcvfs.copy(os.path.join(own, 'resources', 'assets', asset), destination):
                repaired.append(addon_id + '/' + relative)
            else:
                failed.append(addon_id + '/' + relative)
    if repaired or failed:
        xbmc.log('[DexWorld tvOS] AF3 missing assets: repaired=%d failed=%d' % (len(repaired), len(failed)), xbmc.LOGINFO)
    return repaired, failed
