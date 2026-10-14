// DexHub uploaded ZIP install v13.
#if defined(TARGET_DARWIN_TVOS)
static int DexHubInstallZip(const std::vector<std::string>& params)
{
  if (params.empty() || !g_passwordManager.CheckMenuLock(WINDOW_ADDON_BROWSER)) return -1;
  std::error_code error;
  const auto imports = std::filesystem::canonical(
      std::filesystem::path(CTVOSFileUtils::GetUserHomeDirectory()) / "dexhub-imports", error);
  if (error) return -1;
  const auto file = std::filesystem::canonical(params[0], error);
  if (error || file.parent_path() != imports || file.extension() != ".zip" ||
      !std::filesystem::is_regular_file(file, error) || error) return -1;
  if (!CServiceBroker::GetSettingsComponent()->GetSettings()->GetBool(
          CSettings::SETTING_ADDONS_ALLOW_UNKNOWN_SOURCES))
  {
    if (MESSAGING::HELPERS::ShowYesNoDialogText(13106, 36617, 186, 10004) == DialogResponse::CHOICE_YES)
      CServiceBroker::GetGUI()->GetWindowManager().ActivateWindow(
          WINDOW_SETTINGS_SYSTEM, CSettings::SETTING_ADDONS_ALLOW_UNKNOWN_SOURCES);
    return -1;
  }
  if (MESSAGING::HELPERS::ShowYesNoDialogText(
          "DexHub", "Install the addon ZIP uploaded from your phone?") != DialogResponse::CHOICE_YES)
    return -1;
  return CAddonInstaller::GetInstance().InstallFromZip(file.string()) ? 0 : -1;
}
#endif
