"""Plan native player changes before the caller writes any source files."""
from pathlib import Path
import hashlib
import json

def plan_native(root, base, planned, replace_one):
    def read(name):
        if name in planned:
            return planned[name]
        path = root / name
        if not path.is_file():
            raise SystemExit('Unsupported/incomplete Kodi source: ' + name)
        return path.read_text()
    folder = 'xbmc/platform/darwin/tvos/'
    for name in ('TVOSAetherPlayer.h', 'TVOSAetherPlayer.mm'):
        relative = folder + name
        if (root / relative).exists() and relative not in planned:
            previous = (root / relative).read_text()
            template = (base / 'native' / name).read_text()
            owned = previous == template
            for manifest in (root / '.dexhub-backups').glob('*/manifest.json'):
                saved = json.loads(manifest.read_text())
                owned = owned or any(entry['path'] == relative and entry['after'] == hashlib.sha256(previous.encode()).hexdigest() for entry in saved['files'])
            if not owned:
                raise SystemExit('Native player file conflicts: ' + relative)
        planned[relative] = (base / 'native' / name).read_text()
    relative = folder + 'CMakeLists.txt'
    text = read(relative)
    for section, filename in [('SOURCES', 'TVOSAetherPlayer.mm'), ('HEADERS', 'TVOSAetherPlayer.h')]:
        if filename not in text:
            anchor = 'set(' + section + ' '
            text = replace_one(text, anchor, anchor + filename + '\n            ', relative)
    planned[relative] = text


    relative = 'xbmc/cores/playercorefactory/PlayerCoreConfig.cpp'
    text = read(relative)
    if 'TVOSAetherPlayer.h' not in text:
        text = replace_one(text, '#include "PlayerCoreConfig.h"', '#include "PlayerCoreConfig.h"\n#if defined(TARGET_DARWIN_TVOS)\n#include "platform/darwin/tvos/TVOSAetherPlayer.h"\n#endif', relative)
        anchor = '#ifdef TARGET_WEBOS\n    player = std::make_shared<CVideoPlayerWebOS>(callback);'
        text = replace_one(text, anchor, '#if defined(TARGET_DARWIN_TVOS)\n    if (m_name == "Aether" || m_name == "Infuse" || m_name == "VidHub")\n      player = std::make_shared<CTVOSAetherPlayer>(callback);\n    else\n      player = std::make_shared<CVideoPlayer>(callback);\n#elif defined(TARGET_WEBOS)\n    player = std::make_shared<CVideoPlayerWebOS>(callback);', relative)
    planned[relative] = text

    relative = 'xbmc/cores/playercorefactory/PlayerCoreFactory.cpp'
    text = read(relative)
    if '// DexHub native player cores.' not in text:
        anchor = '    m_vecPlayerConfigs.emplace_back(std::move(VideoPlayer));'
        block = '''
#if defined(TARGET_DARWIN_TVOS)
    // DexHub native player cores.
    for (const char* name : {"Aether", "Infuse", "VidHub"})
    {
      auto native = std::make_unique<CPlayerCoreConfig>(name, "video", nullptr);
      native->m_bPlaysAudio = true;
      native->m_bPlaysVideo = true;
      m_vecPlayerConfigs.emplace_back(std::move(native));
    }
#endif'''
        text = replace_one(text, anchor, anchor + block, relative)
        anchor = '      strRealCoreName = CServiceBroker::GetSettingsComponent()->GetAdvancedSettings()->m_videoDefaultPlayer;'
        block = '''    {
      strRealCoreName = CServiceBroker::GetSettingsComponent()->GetAdvancedSettings()->m_videoDefaultPlayer;
#if defined(TARGET_DARWIN_TVOS)
      const int preferred = m_settings->GetInt("videoplayer.dexhubengine");
      if (preferred == 1) strRealCoreName = "Aether";
      else if (preferred == 2)
        strRealCoreName = m_settings->GetInt("videoplayer.dexhubexternal") == 1 ? "VidHub" : "Infuse";
#endif
    }'''
        text = replace_one(text, anchor, block, relative)
    planned[relative] = text

    relative = 'xbmc/application/ApplicationPlayer.cpp'
    text = read(relative)
    if 'dexhub.playercore' not in text:
        anchor = '    newPlayer = factory.GetDefaultPlayer(item);'
        block = '''
#if defined(TARGET_DARWIN_TVOS)
  const std::string dexCore = item.GetProperty("dexhub.playercore").asString();
  if (playerName.empty() && (dexCore == "VideoPlayer" || dexCore == "Aether" || dexCore == "Infuse" || dexCore == "VidHub"))
    newPlayer = dexCore;
  if ((newPlayer == "Infuse" || newPlayer == "VidHub") &&
      ((!item.GetDynPath().starts_with("http://") && !item.GetDynPath().starts_with("https://")) ||
       item.GetDynPath().find('|') != std::string::npos))
    newPlayer = "VideoPlayer";
  if (newPlayer == "Aether" && !item.GetDynPath().starts_with("http://") &&
      !item.GetDynPath().starts_with("https://") && !item.GetDynPath().starts_with("file://") &&
      !item.GetDynPath().starts_with("/"))
    newPlayer = "VideoPlayer";
#endif'''
        text = replace_one(text, anchor, anchor + block, relative)
    planned[relative] = text

    relative = 'xbmc/application/ApplicationPlayer.cpp'
    text = read(relative)
    if '// DexHub trailers stay internal.' not in text:
        anchor = '    newPlayer = factory.GetDefaultPlayer(item);'
        # Insert after the owned per-item preference block, so it cannot
        # override the trailer decision later.
        position = text.index(anchor)
        position = text.index('#endif', text.index('dexhub.playercore', position)) + len('#endif')
        text = text[:position] + '''
#if defined(TARGET_DARWIN_TVOS)
  // DexHub trailers stay internal.
  const std::string trailerPath = item.GetDynPath();
  if (item.GetProperty("dexhub.trailer").asString() == "1" ||
      trailerPath.find("imdb-video.media-imdb.com/") != std::string::npos ||
      trailerPath.find("trailers.apple.com/") != std::string::npos)
    newPlayer = "VideoPlayer";
#endif
''' + text[position:]
    planned[relative] = text

    relative = 'xbmc/video/windows/GUIWindowFullScreen.cpp'
    text = read(relative)
    if '// DexHub native subtitle updates.' not in text:
        anchor = '  if (!appPlayer->IsRenderingVideoLayer())\n    MarkDirtyRegion();'
        text = replace_one(text, anchor, '  // DexHub native subtitle updates.\n  if (!appPlayer->IsRenderingVideoLayer() || appPlayer->GetCurrentPlayer() == "Aether")\n    MarkDirtyRegion();', relative)
    if '// DexHub native surface uses transparent clearing.' not in text:
        anchor = '  if (appPlayer->IsRenderingVideoLayer())\n    CServiceBroker::GetWinSystem()->GetGfxContext().Clear(0);'
        text = replace_one(text, anchor, '  // DexHub native surface uses transparent clearing.\n  if (appPlayer->IsRenderingVideoLayer() || appPlayer->GetCurrentPlayer() == "Aether")\n    CServiceBroker::GetWinSystem()->GetGfxContext().Clear(0);', relative)
    planned[relative] = text

    relative = 'xbmc/guilib/GUIVideoControl.cpp'
    text = read(relative)
    if '// DexHub embedded video rect and subtitles.' not in text:
        anchor = '      CServiceBroker::GetWinSystem()->GetGfxContext().SetScissors(old);'
        text = replace_one(text, anchor, anchor + '\n      // DexHub embedded video rect and subtitles.\n      if (appPlayer->GetCurrentPlayer() == "Aether")\n        appPlayer->Render(false, alpha);', relative)
        anchor = '  if (!appPlayer->IsRenderingVideoLayer())\n    MarkDirtyRegion();'
        text = replace_one(text, anchor, '  if (!appPlayer->IsRenderingVideoLayer() || appPlayer->GetCurrentPlayer() == "Aether")\n    MarkDirtyRegion();', relative)
    planned[relative] = text

    relative = 'system/settings/darwin_tvos.xml'
    text = read(relative)
    if 'videoplayer.dexhubengine' not in text:
        anchor = '    <category id="videoplayer">'
        block = '''
      <group id="1">
        <setting id="videoplayer.dexhubengine" type="integer" label="49990">
          <level>0</level><default>0</default>
          <constraints><options>
            <option label="49991">0</option><option label="49992">1</option><option label="49993">2</option>
          </options></constraints>
          <control type="list" format="integer" />
        </setting>
        <setting id="videoplayer.dexhubexternal" type="integer" label="49994">
          <level>0</level><default>0</default>
          <constraints><options><option label="49995">0</option><option label="49996">1</option></options></constraints>
          <control type="list" format="integer" />
        </setting>
      </group>'''
        text = replace_one(text, anchor, anchor + block, relative)
    planned[relative] = text
    relative = 'addons/resource.language.en_gb/resources/strings.po'
    text = read(relative)
    labels = {49990: 'Preferred player / المشغل المفضل', 49991: 'Kodi', 49992: 'Aether',
              49993: 'External / خارجي', 49994: 'External player / المشغل الخارجي', 49995: 'Infuse', 49996: 'VidHub'}
    for key, label in labels.items():
        entry = f'msgctxt "#{key}"\nmsgid "{label}"\nmsgstr ""'
        if f'msgctxt "#{key}"' in text:
            if entry not in text:
                raise SystemExit('Kodi localization ID conflict: ' + str(key))
        else:
            text += '\n\n' + entry + '\n'
    planned[relative] = text

    # Upgrade our previous multi-engine patch without touching unrelated edits.
    replacements = {
        'xbmc/cores/playercorefactory/PlayerCoreConfig.cpp': [
            ('m_name == "Aether" || m_name == "Infuse" || m_name == "VidHub"', 'm_name == "Aether" || m_name == "KSPlayer" || m_name == "MPV" || m_name == "Infuse" || m_name == "VidHub"')],
        'xbmc/cores/playercorefactory/PlayerCoreFactory.cpp': [
            ('{"Aether", "Infuse", "VidHub"}', '{"Aether", "Infuse", "VidHub", "KSPlayer", "MPV"}'),
            ('if (preferred == 1) strRealCoreName = "Aether";', 'if (preferred == 1) strRealCoreName = "Aether";\n      else if (preferred == 3) strRealCoreName = "KSPlayer";\n      else if (preferred == 4) strRealCoreName = "MPV";')],
        'xbmc/application/ApplicationPlayer.cpp': [
            ('dexCore == "VideoPlayer" || dexCore == "Aether" || dexCore == "Infuse" || dexCore == "VidHub"', 'dexCore == "VideoPlayer" || dexCore == "Aether" || dexCore == "KSPlayer" || dexCore == "MPV" || dexCore == "Infuse" || dexCore == "VidHub"'),
            ('if (newPlayer == "Aether" &&', 'if ((newPlayer == "Aether" || newPlayer == "KSPlayer" || newPlayer == "MPV") &&')],
        'xbmc/video/windows/GUIWindowFullScreen.cpp': [
            ('appPlayer->GetCurrentPlayer() == "Aether"', '(appPlayer->GetCurrentPlayer() == "Aether" || appPlayer->GetCurrentPlayer() == "KSPlayer" || appPlayer->GetCurrentPlayer() == "MPV")')],
        'xbmc/guilib/GUIVideoControl.cpp': [
            ('appPlayer->GetCurrentPlayer() == "Aether"', '(appPlayer->GetCurrentPlayer() == "Aether" || appPlayer->GetCurrentPlayer() == "KSPlayer" || appPlayer->GetCurrentPlayer() == "MPV")')],
        'system/settings/darwin_tvos.xml': [
            ('<option label="49993">2</option>', '<option label="49993">2</option><option label="49997">3</option><option label="49998">4</option>')],
    }
    for name, pairs in replacements.items():
        value = read(name)
        if 'DexHub multi-engine v13' in value:
            for old, new in pairs:
                if new not in value:
                    raise SystemExit('Previous engine migration conflicts: ' + name)
                value = value.replace(new, old)
            marker = '\n<!-- DexHub multi-engine v13 -->\n' if name.endswith('.xml') else '\n// DexHub multi-engine v13\n'
            value = value.replace(marker, '')
        if name == 'system/settings/darwin_tvos.xml':
            value = value.replace('<setting id="videoplayer.dexhubengine" type="integer" label="49990">\n          <level>0</level><default>0</default>', '<setting id="videoplayer.dexhubengine" type="integer" label="49990">\n          <level>0</level><default>1</default>')
        planned[name] = value
    strings = 'addons/resource.language.en_gb/resources/strings.po'
    value = read(strings)
    for key, label in [(49997, 'KSPlayer (TEST)'), (49998, 'MPV (TEST)')]:
        entry = f'msgctxt "#{key}"\nmsgid "{label}"\nmsgstr ""'
        if f'msgctxt "#{key}"' in value:
            if entry not in value: raise SystemExit('Localization ID conflict: ' + str(key))
            value = value.replace(entry + '\n', '')
    planned[strings] = value

    relative = 'system/settings/darwin_tvos.xml'
    value = read(relative)
    if 'videoplayer.dexhubtruehdatmos' not in value:
        anchor = '    <category id="videoplayer">'
        block = '''
      <group id="8">
        <setting id="videoplayer.dexhubtruehdatmos" type="integer" label="49999">
          <level>0</level><default>0</default>
          <constraints><options>
            <option label="50000">0</option><option label="50001">1</option>
            <option label="50002">2</option><option label="50003">3</option>
            <option label="50004">4</option><option label="50005">5</option>
          </options></constraints>
          <control type="list" format="integer" />
        </setting>
      </group>'''
        value = replace_one(value, anchor, anchor + block, relative)
    planned[relative] = value
    value = read(strings)
    for key, label in {49999: 'Aether TrueHD Atmos / توزيع سماعات Atmos',
                       50000: 'Off (E-AC-3 Atmos remains automatic)',
                       50001: '5.1.2', 50002: '5.1.4', 50003: '7.1.2',
                       50004: '7.1.4', 50005: '9.1.6'}.items():
        entry = f'msgctxt "#{key}"\nmsgid "{label}"\nmsgstr ""'
        if f'msgctxt "#{key}"' in value:
            if entry not in value: raise SystemExit('Localization ID conflict: ' + str(key))
        else: value += '\n\n' + entry + '\n'
    planned[strings] = value

    for filename in ('TVOSDexHubSetup.h', 'TVOSDexHubSetup.mm'):
        relative = folder + filename
        path = root / relative
        template = (base / 'native' / filename).read_text()
        if path.exists() and path.read_text() != template:
            owned = False
            for manifest in (root / '.dexhub-backups').glob('*/manifest.json'):
                saved = json.loads(manifest.read_text())
                owned |= any(row['path'] == relative and row['after'] == hashlib.sha256(path.read_bytes()).hexdigest() for row in saved['files'])
            if not owned: raise SystemExit('Setup source file conflicts: ' + relative)
        planned[relative] = template
    relative = folder + 'CMakeLists.txt'
    value = read(relative)
    for section, filename in [('SOURCES', 'TVOSDexHubSetup.mm'), ('HEADERS', 'TVOSDexHubSetup.h')]:
        if filename not in value:
            anchor = 'set(' + section + ' '
            value = replace_one(value, anchor, anchor + filename + '\n            ', relative)
    planned[relative] = value

    relative = 'xbmc/application/Application.cpp'
    value = read(relative)
    if '#include "platform/darwin/tvos/TVOSDexHubSetup.h"' not in value:
        anchor = '#include "Application.h"'
        value = replace_one(value, anchor, anchor + '\n#if defined(TARGET_DARWIN_TVOS)\n#include "platform/darwin/tvos/TVOSDexHubSetup.h"\n#endif', relative)
    if '  ConfigureDexHubSkin();' not in value:
        anchor = '    CServiceBroker::RegisterTextureCache(std::make_shared<CTextureCache>());'
        value = replace_one(value, anchor, anchor + '\n#if defined(TARGET_DARWIN_TVOS)\n    ConfigureDexHubSkin();\n#endif', relative)
    # v20: the GUI always runs in the Apple TV's own mode (desktop). A saved 23.976 Hz
    # screen mode kept every menu at 24 frames a second (kodi.log: "About to switch to
    # 3840 x 2160 @ 23.976" at start). Players still switch rates for the video itself.
    if '// DexHub GUI desktop mode v20.' not in value:
        anchor = '  CDisplaySettings::GetInstance().SetCurrentResolution(CDisplaySettings::GetInstance().GetDisplayResolution());'
        value = replace_one(value, anchor,
            '#if defined(TARGET_DARWIN_TVOS)\n'
            '  // DexHub GUI desktop mode v20.\n'
            '  if (CDisplaySettings::GetInstance().GetDisplayResolution() != RES_DESKTOP)\n'
            '    sav_res = true;\n'
            '  CDisplaySettings::GetInstance().SetCurrentResolution(RES_DESKTOP);\n'
            '#else\n' + anchor + '\n#endif', relative)
    planned[relative] = value

    relative = 'xbmc/interfaces/builtins/AddonBuiltins.cpp'
    value = read(relative)
    if '// DexHub uploaded ZIP install v13.' not in value:
        anchor = '#include "AddonBuiltins.h"'
        value = replace_one(value, anchor, anchor + '\n#if defined(TARGET_DARWIN_TVOS)\n#include "platform/darwin/tvos/filesystem/TVOSFileUtils.h"\n#include "settings/Settings.h"\n#include "settings/SettingsComponent.h"\n#include <filesystem>\n#endif', relative)
        anchor = 'CBuiltins::CommandMap CAddonBuiltins::GetOperations() const'
        value = replace_one(value, anchor, (base / 'native/DexHubZipBuiltin.inc').read_text() + '\n' + anchor, relative)
        anchor = '           {"installaddon",'
        value = replace_one(value, anchor, '#if defined(TARGET_DARWIN_TVOS)\n           {"dexhub.installzip", {"Install an uploaded addon ZIP", 1, DexHubInstallZip}},\n#endif\n' + anchor, relative)
    planned[relative] = value

    relative = 'system/settings/darwin_tvos.xml'
    value = read(relative)
    if 'videoplayer.dexhubnativeversion' not in value:
        anchor = '    <category id="videoplayer">'
        # Internal level hides the UI control while retaining JSON-RPC visibility.
        value = replace_one(value, anchor, anchor + '\n      <group id="9"><setting id="videoplayer.dexhubnativeversion" type="integer">\n        <level>4</level><default>19</default>\n        <control type="edit" format="integer" />\n      </setting></group>', relative)
    value = value.replace('<level>4</level><default>14</default>', '<level>4</level><default>19</default>')
    planned[relative] = value
    relative = 'xbmc/ServiceManager.cpp'
    value = read(relative)
    if '#include "platform/darwin/tvos/TVOSDexHubSetup.h"' not in value:
        anchor = '#include "ServiceManager.h"'
        value = replace_one(value, anchor, anchor + '\n#if defined(TARGET_DARWIN_TVOS)\n#include "platform/darwin/tvos/TVOSDexHubSetup.h"\n#endif', relative)
        anchor = 'bool CServiceManager::InitStageTwo(const std::string& profilesUserDataFolder)\n{'
        value = replace_one(value, anchor, anchor + '\n#if defined(TARGET_DARWIN_TVOS)\n  PrepareDexHubBundle();\n#endif', relative)
        anchor = '  m_repositoryUpdater = std::make_unique<ADDON::CRepositoryUpdater>(*m_addonMgr);'
        value = replace_one(value, anchor, '#if defined(TARGET_DARWIN_TVOS)\n  ActivateDexHubBundle(*m_addonMgr);\n#endif\n\n' + anchor, relative)
    planned[relative] = value

