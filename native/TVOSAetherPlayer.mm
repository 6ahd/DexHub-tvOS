// SPDX-License-Identifier: GPL-2.0-or-later
#include "TVOSAetherPlayer.h"

#include "FileItem.h"
#include "ServiceBroker.h"
#include "cores/AudioEngine/Interfaces/AE.h"
#include "cores/DataCacheCore.h"
#include "cores/VideoPlayer/DVDSubtitles/SubtitlesAdapter.h"
#include "cores/VideoPlayer/VideoRenderers/OverlayRenderer.h"
#include "filesystem/SpecialProtocol.h"
#include "messaging/ApplicationMessenger.h"
#include "platform/darwin/tvos/filesystem/TVOSFileUtils.h"
#include "settings/Settings.h"
#include "settings/SettingsComponent.h"
#include "windowing/GraphicContext.h"
#include "utils/LanguageTag.h"
#include "utils/log.h"
#include "video/Bookmark.h"
#include "video/VideoInfoTag.h"
#include "windowing/WinSystem.h"
#include "TVOSEAGLView.h"
#include "XBMCController.h"

#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>

#include <algorithm>
#include <chrono>

@interface NSObject (DexAetherNativeAPI)
+ (void)startEmbedded:(NSDictionary*)request inView:(UIView*)parent belowView:(UIView*)overlay;
+ (NSDictionary*)snapshotForToken:(NSString*)token;
+ (void)command:(NSDictionary*)request;
@end

namespace
{
std::string String(id value)
{
  return [value isKindOfClass:[NSString class]] ? std::string([value UTF8String]) : "";
}
NSString* NS(const std::string& value) { return [NSString stringWithUTF8String:value.c_str()]; }
Class Bridge(const std::string&, bool load = true)
{
  NSString* name = @"DexAetherBridge";
  Class bridge = NSClassFromString(name);
  if (bridge)
    return bridge;
  if (!load)
    return Nil;
  NSString* path = [[[NSBundle mainBundle] privateFrameworksPath]
      stringByAppendingPathComponent:[name stringByAppendingString:@".framework"]];
  NSError* error = nil;
  if (![[NSBundle bundleWithPath:path] loadAndReturnError:&error])
    return Nil;
  return NSClassFromString(name);
}
struct Track
{
  int id;
  std::string name, language, codec;
  int channels, samplerate, bits;
  bool external;
};
std::vector<Track> Tracks(NSArray* rows)
{
  std::vector<Track> result;
  for (NSDictionary* row in rows)
    result.push_back({[row[@"id"] intValue], String(row[@"name"]), String(row[@"language"]),
                      String(row[@"codec"]), [row[@"channels"] intValue],
                      [row[@"samplerate"] intValue], [row[@"bits"] intValue],
                      [row[@"external"] boolValue]});
  return result;
}
int TrackIndex(const std::vector<Track>& tracks, int id)
{
  for (size_t index = 0; index < tracks.size(); ++index)
    if (tracks[index].id == id)
      return static_cast<int>(index);
  return -1;
}
}

struct CTVOSAetherPlayer::State
{
  CFileItem file;
  std::string token;
  std::string status{"loading"}, codec, hdr;
  std::vector<Track> audio, subtitles;
  int audioId{-1}, subtitleId{-1}, savedSubtitle{-1}, width{0}, height{0};
  int trackRevision{-1};
  double position{0}, duration{0}, sourceTime{0};
  float fps{0}, volume{1};
  bool visible{true}, muted{false}, suspended{false}, started{false}, external{false}, fullscreen{false};
  CVideoSettings settings;
  CRect source, dest, view, lastNativeRect;
  CSubtitlesAdapter text;
  OVERLAY::CRenderer overlays;
  std::shared_ptr<CDVDOverlay> overlay;
  std::string lastText;
  bool renderReported{false};
  NSArray* __strong cues{nil};
};

CTVOSAetherPlayer::CTVOSAetherPlayer(IPlayerCallback& callback)
  : IPlayer(callback), CThread("DexAetherPlayer"), m_state(std::make_unique<State>())
{
}
CTVOSAetherPlayer::~CTVOSAetherPlayer() { CloseFile(); }

bool CTVOSAetherPlayer::OpenFile(const CFileItem& file, const CPlayerOptions& options)
{
  CloseFile();
  @autoreleasepool
  {
    std::lock_guard lock(m_lock);
    m_state = std::make_unique<State>();
    auto& state = *m_state;
    state.file = file;
    state.external = m_name == "Infuse" || m_name == "VidHub";
    state.fullscreen = options.fullscreen;
    state.position = std::max(0.0, options.starttime);
    state.token = String([[NSUUID UUID] UUIDString]);
    if (!state.text.Initialize())
      return false;
    state.overlay = state.text.CreateOverlay();
    if (auto ae = CServiceBroker::GetActiveAE())
    {
      state.suspended = ae->Suspend();
      if (!state.suspended)
        return false;
    }
    CDataCacheCore::GetInstance().SetVideoDecoderName(m_name, true);
    CDataCacheCore::GetInstance().SetGuiRender(true);
    CDataCacheCore::GetInstance().SetVideoRender(!state.external);
    CDataCacheCore::GetInstance().SetSpeed(1, 1);
    NSMutableDictionary* request = [NSMutableDictionary dictionaryWithDictionary:@{
      @"token": NS(state.token), @"url": NS(file.GetDynPath()),
      @"position": @(state.position), @"percent": @(options.startpercent),
      @"engine": NS(m_name)}];
    request[@"home"] = NS(CTVOSFileUtils::GetUserHomeDirectory());
    request[@"truehdAtmosLayout"] = @(CServiceBroker::GetSettingsComponent()->GetSettings()->GetInt("videoplayer.dexhubtruehdatmos"));
    request[@"kodiPath"] = NS(file.GetPath());
    const std::string context = file.GetProperty("dexhub.external.context").asString();
    if (!context.empty())
    {
      NSData* data = [NS(context) dataUsingEncoding:NSUTF8StringEncoding];
      id value = [NSJSONSerialization JSONObjectWithData:data options:0 error:nullptr];
      if ([value isKindOfClass:[NSDictionary class]]) request[@"context"] = value;
    }
    const double duration = file.HasVideoInfoTag() ? file.GetVideoInfoTag()->GetDuration() : 0;
    request[@"duration"] = @(duration);
    if (state.external && state.position == 0 && options.startpercent > 0 && duration > 0)
      request[@"position"] = @(duration * options.startpercent / 100);
    std::string filename = file.GetProperty("dexhub.external.filename").asString();
    if (filename.empty())
    {
      filename = file.GetLabel();
      if (file.HasVideoInfoTag())
      {
        const auto* tag = file.GetVideoInfoTag();
        if (!tag->m_strShowTitle.empty()) filename = tag->m_strShowTitle;
        else if (!tag->m_strTitle.empty()) filename = tag->m_strTitle;
        if (tag->m_iSeason >= 0 && tag->m_iEpisode >= 0)
          filename += " S" + std::string(tag->m_iSeason < 10 ? "0" : "") + std::to_string(tag->m_iSeason) +
              "E" + std::string(tag->m_iEpisode < 10 ? "0" : "") + std::to_string(tag->m_iEpisode);
        else if (tag->GetYear() > 0) filename += " (" + std::to_string(tag->GetYear()) + ")";
      }
      if (!filename.empty()) filename += ".mkv";
    }
    request[@"filename"] = NS(filename);
    std::string subtitles = file.GetProperty("dexhub.aether.subtitles").asString();
    if (!subtitles.empty())
    {
      NSData* data = [NS(subtitles) dataUsingEncoding:NSUTF8StringEncoding];
      id rows = [NSJSONSerialization JSONObjectWithData:data options:0 error:nullptr];
      if ([rows isKindOfClass:[NSArray class]])
        request[@"subtitles"] = rows;
    }
    NSMutableArray* paths = [NSMutableArray array];
    for (NSString* path in request[@"subtitles"])
      [paths addObject:NS(CSpecialProtocol::TranslatePath(String(path)))];
    for (unsigned index = 1; ; ++index)
    {
      std::string key = "subtitle:" + std::to_string(index);
      if (!file.HasProperty(key)) break;
      NSString* path = NS(CSpecialProtocol::TranslatePath(file.GetProperty(key).asString()));
      if (![paths containsObject:path]) [paths addObject:path];
    }
    request[@"subtitles"] = paths;
    const std::string engineName = m_name;
    dispatch_async(dispatch_get_main_queue(), ^{
      Class bridge = Bridge(engineName);
      if ([bridge respondsToSelector:@selector(startEmbedded:inView:belowView:)])
        [bridge startEmbedded:request inView:g_xbmcController.view belowView:g_xbmcController.glView];
      else
        CLog::Log(LOGERROR, "DexAetherBridge native player entry point missing");
    });
    m_open = true;
    m_playing = true;
    Create();
  }
  return true;
}

bool CTVOSAetherPlayer::CloseFile(bool reopen)
{
  if (!m_open.exchange(false))
    return true;
  StopThread();
  Command("stop");
  std::lock_guard lock(m_lock);
  if (m_state->suspended)
  {
    CServiceBroker::GetActiveAE()->Resume();
    m_state->suspended = false;
  }
  CDataCacheCore::GetInstance().SetVideoRender(false);
  m_playing = false;
  return true;
}

void CTVOSAetherPlayer::Command(const std::string& name, double value, const std::string& text)
{
  @autoreleasepool
  {
    std::string token;
    { std::lock_guard lock(m_lock); token = m_state->token; }
    NSDictionary* request = @{@"token": NS(token), @"name": NS(name), @"value": @(value), @"text": NS(text)};
    const std::string engineName = m_name;
    dispatch_async(dispatch_get_main_queue(), ^{
      Class bridge = Bridge(engineName, false);
      if ([bridge respondsToSelector:@selector(command:)])
        [bridge command:request];
    });
  }
}

void CTVOSAetherPlayer::Process()
{
  auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(120);
  bool ended = false, failed = false;
  while (!m_bStop)
  {
    bool start = false;
    @autoreleasepool
    {
      NSString* token = NS(m_state->token);
      Class bridge = Bridge(m_name, false);
      NSDictionary* snapshot = [bridge respondsToSelector:@selector(snapshotForToken:)] ?
          [bridge snapshotForToken:token] : nil;
      if (snapshot)
      {
        std::lock_guard lock(m_lock);
        auto& state = *m_state;
        state.status = String(snapshot[@"state"]);
        state.position = [snapshot[@"position"] doubleValue];
        state.duration = [snapshot[@"duration"] doubleValue];
        state.sourceTime = [snapshot[@"sourceTime"] doubleValue];
        const int revision = [snapshot[@"trackRevision"] intValue];
        const int audioId = snapshot[@"audioId"] ? [snapshot[@"audioId"] intValue] : -1;
        const int subtitleId = snapshot[@"subtitleId"] ? [snapshot[@"subtitleId"] intValue] : -1;
        const bool tracksChanged = revision != state.trackRevision || audioId != state.audioId || subtitleId != state.subtitleId;
        if (revision != state.trackRevision)
        {
          state.audio = Tracks(snapshot[@"audio"]);
          state.subtitles = Tracks(snapshot[@"subtitles"]);
          state.trackRevision = revision;
        }
        state.audioId = snapshot[@"audioId"] ? [snapshot[@"audioId"] intValue] : -1;
        state.subtitleId = snapshot[@"subtitleId"] ? [snapshot[@"subtitleId"] intValue] : -1;
        state.width = [snapshot[@"width"] intValue];
        state.height = [snapshot[@"height"] intValue];
        state.fps = [snapshot[@"fps"] floatValue];
        state.codec = String(snapshot[@"codec"]);
        state.hdr = String(snapshot[@"hdr"]);
        state.cues = snapshot[@"cues"];
        auto& cache = CDataCacheCore::GetInstance();
        cache.SetVideoRender(!state.external);
        cache.SetPlayTimes(0, state.position * 1000, 0, state.duration * 1000);
        cache.SetVideoDimensions(state.width, state.height);
        cache.SetVideoFps(state.fps);
        if (state.height > 0) cache.SetVideoDAR(float(state.width) / state.height);
        if (tracksChanged) cache.SignalSubtitleInfoChange();
        if (!state.started && (state.status == "playing" || state.status == "paused"))
        {
          CLog::Log(LOGINFO, "DexAether video surface: state={}, size={}x{}, codec={}",
                    state.status, state.width, state.height, state.codec);
          CLog::Log(LOGINFO, "DexAether v11 surface attachment: window={}, view={}x{}, layers={}",
                    [snapshot[@"surfaceInWindow"] boolValue],
                    [snapshot[@"surfaceWidth"] doubleValue], [snapshot[@"surfaceHeight"] doubleValue],
                    [snapshot[@"surfaceLayers"] intValue]);
          start = state.started = true;
        }
        ended = state.status == "ended";
        failed = state.status == "error";
        if (failed)
          CLog::Log(LOGERROR, "Aether playback error: {}", String(snapshot[@"message"]));
        if (state.status == "external")
          break;
      }
    }
    if (start)
    {
      m_callback.OnPlayBackStarted(m_state->file);
      m_callback.OnAVStarted(m_state->file);
      m_callback.RequestVideoSettings(m_state->file);
      if (!m_state->external && m_state->fullscreen)
      {
        CLog::Log(LOGINFO, "DexAether v11: requesting Kodi fullscreen video window");
        CServiceBroker::GetAppMessenger()->PostMsg(TMSG_SWITCHTOFULLSCREEN);
      }
    }
    if (ended || failed)
      break;
    if (!m_state->started && std::chrono::steady_clock::now() > deadline)
    {
      failed = true;
      CLog::Log(LOGERROR, "Aether startup timed out");
      break;
    }
    Sleep(std::chrono::milliseconds(100));
  }
  CBookmark bookmark;
  {
    std::lock_guard lock(m_lock);
    bookmark.timeInSeconds = m_state->position;
    bookmark.totalTimeInSeconds = m_state->duration;
    bookmark.player = m_name;
  }
  if (m_state->started)
  {
    m_callback.StoreVideoSettings(m_state->file, GetVideoSettings());
    m_callback.OnPlayerCloseFile(m_state->file, bookmark);
  }
  m_playing = false;
  if (failed) m_callback.OnPlayBackError();
  else if (ended) m_callback.OnPlayBackEnded();
  else m_callback.OnPlayBackStopped();
}

bool CTVOSAetherPlayer::IsPlaying() const { return m_playing; }
bool CTVOSAetherPlayer::HasVideo() const { return m_playing; }
bool CTVOSAetherPlayer::HasAudio() const { std::lock_guard lock(m_lock); return !m_state->audio.empty(); }
bool CTVOSAetherPlayer::CanSeek() const { std::lock_guard lock(m_lock); return m_state->duration > 0; }
void CTVOSAetherPlayer::Pause()
{
  bool paused;
  { std::lock_guard lock(m_lock); paused = m_state->status == "paused"; }
  SetSpeed(paused ? 1 : 0);
}
void CTVOSAetherPlayer::SetSpeed(float speed)
{
  speed = std::clamp(speed, 0.0f, 2.0f);
  Command("rate", speed);
  CDataCacheCore::GetInstance().SetSpeed(1, speed);
  if (speed == 0) m_callback.OnPlayBackPaused();
  else m_callback.OnPlayBackResumed();
}
void CTVOSAetherPlayer::Seek(bool plus, bool large, bool chapter)
{ SeekTimeRelative((plus ? 1 : -1) * (large ? 600000 : 10000)); }
void CTVOSAetherPlayer::SeekPercentage(float percent)
{
  double total;
  { std::lock_guard lock(m_lock); total = m_state->duration; }
  SeekTime(total * std::clamp(percent, 0.0f, 100.0f) * 10);
}
bool CTVOSAetherPlayer::SeekTimeRelative(int64_t time)
{
  double position;
  { std::lock_guard lock(m_lock); position = m_state->position; }
  SeekTime(position * 1000 + time);
  return true;
}
void CTVOSAetherPlayer::SeekTime(int64_t time)
{
  double before;
  { std::lock_guard lock(m_lock); before = m_state->position; }
  time = std::max<int64_t>(0, time);
  Command("seek", double(time) / 1000);
  m_callback.OnPlayBackSeek(time, time - int64_t(before * 1000));
}
void CTVOSAetherPlayer::SetVolume(float value)
{
  bool muted;
  { std::lock_guard lock(m_lock); m_state->volume = value; muted = m_state->muted; }
  Command("volume", muted ? 0 : std::clamp(value, 0.0f, 1.0f));
}
void CTVOSAetherPlayer::SetMute(bool muted)
{
  float volume;
  { std::lock_guard lock(m_lock); m_state->muted = muted; volume = m_state->volume; }
  Command("volume", muted ? 0 : volume);
}
void CTVOSAetherPlayer::SetAVDelay(float delay)
{ { std::lock_guard lock(m_lock); m_state->settings.m_AudioDelay = delay; } Command("audioDelay", delay); }
float CTVOSAetherPlayer::GetAVDelay() { std::lock_guard lock(m_lock); return m_state->settings.m_AudioDelay; }
void CTVOSAetherPlayer::SetSubTitleDelay(float delay)
{ { std::lock_guard lock(m_lock); m_state->settings.m_SubtitleDelay = delay; } Command("subtitleDelay", delay); }
float CTVOSAetherPlayer::GetSubTitleDelay() { std::lock_guard lock(m_lock); return m_state->settings.m_SubtitleDelay; }
int CTVOSAetherPlayer::GetSubtitleCount() const { std::lock_guard lock(m_lock); return m_state->subtitles.size(); }
int CTVOSAetherPlayer::GetSubtitle() { std::lock_guard lock(m_lock); return TrackIndex(m_state->subtitles, m_state->subtitleId); }
void CTVOSAetherPlayer::GetSubtitleStreamInfo(int index, SubtitleStreamInfo& info) const
{
  std::lock_guard lock(m_lock);
  if (index < 0 || index >= int(m_state->subtitles.size())) return;
  const auto& track = m_state->subtitles[index];
  info.valid = true; info.name = track.name; info.codecName = track.codec;
  info.language = KODI::UTILS::CLanguageTag::Parse(track.language); info.isExternal = track.external;
}
void CTVOSAetherPlayer::SetSubtitle(int index)
{
  int id;
  { std::lock_guard lock(m_lock);
    if (index < 0 || index >= int(m_state->subtitles.size())) return;
    id = m_state->subtitles[index].id; m_state->savedSubtitle = id; m_state->visible = true;
    m_state->settings.m_SubtitleStream = index; m_state->settings.m_SubtitleOn = true;
  }
  Command("subtitle", id);
}
bool CTVOSAetherPlayer::GetSubtitleVisible() const { std::lock_guard lock(m_lock); return m_state->visible && m_state->subtitleId >= 0; }
void CTVOSAetherPlayer::SetSubtitleVisible(bool visible)
{
  int id = -1;
  { std::lock_guard lock(m_lock);
    if (!visible && m_state->subtitleId >= 0) m_state->savedSubtitle = m_state->subtitleId;
    m_state->visible = visible; m_state->settings.m_SubtitleOn = visible;
    if (visible) id = m_state->savedSubtitle >= 0 ? m_state->savedSubtitle : (m_state->subtitles.empty() ? -1 : m_state->subtitles.front().id);
  }
  Command("subtitle", id);
}
void CTVOSAetherPlayer::AddSubtitle(const std::string& path)
{ Command("addSubtitle", 0, CSpecialProtocol::TranslatePath(path)); }
int CTVOSAetherPlayer::GetAudioStreamCount() const { std::lock_guard lock(m_lock); return m_state->audio.size(); }
int CTVOSAetherPlayer::GetAudioStream() { std::lock_guard lock(m_lock); return TrackIndex(m_state->audio, m_state->audioId); }
void CTVOSAetherPlayer::GetAudioStreamInfo(int index, AudioStreamInfo& info) const
{
  std::lock_guard lock(m_lock);
  if (index < 0 || index >= int(m_state->audio.size())) return;
  const auto& track = m_state->audio[index];
  info.valid = true; info.name = track.name; info.codecName = track.codec;
  info.language = KODI::UTILS::CLanguageTag::Parse(track.language); info.channels = track.channels;
  info.samplerate = track.samplerate; info.bitspersample = track.bits;
}
void CTVOSAetherPlayer::SetAudioStream(int index)
{
  int id;
  { std::lock_guard lock(m_lock);
    if (index < 0 || index >= int(m_state->audio.size())) return;
    id = m_state->audio[index].id; m_state->settings.m_AudioStream = index;
  }
  Command("audio", id);
}
int CTVOSAetherPlayer::GetVideoStreamCount() const { return 1; }
int CTVOSAetherPlayer::GetVideoStream() const { return 0; }
void CTVOSAetherPlayer::GetVideoStreamInfo(int index, VideoStreamInfo& info) const
{
  std::lock_guard lock(m_lock);
  info.valid = true; info.width = m_state->width; info.height = m_state->height;
  info.codecName = m_state->codec; info.videoAspectRatio = m_state->height > 0 ? float(m_state->width) / m_state->height : 1;
  info.fpsRate = m_state->fps * 1000; info.fpsScale = 1000;
  if (m_state->hdr == "dolbyVision") info.hdrType = StreamHdrType::HDR_TYPE_DOLBYVISION;
  else if (m_state->hdr == "hdr10Plus") info.hdrType = StreamHdrType::HDR_TYPE_HDR10PLUS;
  else if (m_state->hdr == "hdr10") info.hdrType = StreamHdrType::HDR_TYPE_HDR10;
  else if (m_state->hdr == "hlg") info.hdrType = StreamHdrType::HDR_TYPE_HLG;
}
float CTVOSAetherPlayer::GetRenderAspectRatio() const
{ std::lock_guard lock(m_lock); return m_state->height > 0 ? float(m_state->width) / m_state->height : 1; }
bool CTVOSAetherPlayer::IsRenderingVideo() const { return m_playing; }
bool CTVOSAetherPlayer::IsCaching() const { std::lock_guard lock(m_lock); return m_state->status == "loading"; }
void CTVOSAetherPlayer::GetRects(CRect& source, CRect& dest, CRect& view) const
{ std::lock_guard lock(m_lock); source = m_state->source; dest = m_state->dest; view = m_state->view; }
bool CTVOSAetherPlayer::HasVisibleOverlay() const
{ std::lock_guard lock(m_lock); return m_state->visible && m_state->overlays.HasVisibleOverlay(0); }
void CTVOSAetherPlayer::SetSubtitleVerticalPosition(int value, bool save)
{
  // PrepareOverlays calls back here while Render holds the player-state lock.
  // The overlay renderer protects its own state with a recursive lock.
  m_state->overlays.SetSubtitleVerticalPosition(value, save);
}
void CTVOSAetherPlayer::GetAudioCapabilities(std::vector<IPlayerAudioCaps>& caps) const
{ caps = {IPlayerAudioCaps::SELECT_STREAM, IPlayerAudioCaps::OFFSET}; }
void CTVOSAetherPlayer::GetSubtitleCapabilities(std::vector<IPlayerSubtitleCaps>& caps) const
{ caps = {IPlayerSubtitleCaps::SELECT_STREAM, IPlayerSubtitleCaps::EXTERNAL, IPlayerSubtitleCaps::OFFSET}; }
CVideoSettings CTVOSAetherPlayer::GetVideoSettings() const { std::lock_guard lock(m_lock); return m_state->settings; }
void CTVOSAetherPlayer::SetVideoSettings(CVideoSettings& settings)
{
  { std::lock_guard lock(m_lock); m_state->settings = settings; }
  SetAVDelay(settings.m_AudioDelay); SetSubTitleDelay(settings.m_SubtitleDelay);
  if (settings.m_AudioStream >= 0) SetAudioStream(settings.m_AudioStream);
  if (settings.m_SubtitleStream >= 0) SetSubtitle(settings.m_SubtitleStream);
  SetSubtitleVisible(settings.m_SubtitleOn);
}

void CTVOSAetherPlayer::Render(bool clear, uint32_t alpha, bool gui)
{
  if (!gui || !m_playing) return;
  @autoreleasepool
  {
    std::lock_guard lock(m_lock);
    auto& state = *m_state;
    if (state.external) return;
    auto& gfx = CServiceBroker::GetWinSystem()->GetGfxContext();
    if (clear) gfx.Clear(0);
    state.source = CRect(0, 0, state.width, state.height);
    state.view = gfx.GetViewWindow();
    if (!state.renderReported)
    {
      state.renderReported = true;
      CLog::Log(LOGINFO, "DexAether v11 Kodi render: fullscreen={}, rect={}x{}",
                gfx.IsFullScreenVideo(), state.view.Width(), state.view.Height());
    }
    state.dest = state.view;
    const float aspect = state.height > 0 ? float(state.width) / state.height : 16.0f / 9;
    if (state.view.Height() > 0 && state.view.Width() / state.view.Height() > aspect)
    { float width = state.view.Height() * aspect; state.dest.x1 += (state.view.Width() - width) / 2; state.dest.x2 = state.dest.x1 + width; }
    else if (aspect > 0)
    { float height = state.view.Width() / aspect; state.dest.y1 += (state.view.Height() - height) / 2; state.dest.y2 = state.dest.y1 + height; }
    if (state.view != state.lastNativeRect && gfx.GetWidth() > 0 && gfx.GetHeight() > 0)
    {
      state.lastNativeRect = state.view;
      NSDictionary* request = @{@"token": NS(state.token), @"name": @"rect",
          @"x": @(state.view.x1 / gfx.GetWidth()), @"y": @(state.view.y1 / gfx.GetHeight()),
          @"width": @(state.view.Width() / gfx.GetWidth()), @"height": @(state.view.Height() / gfx.GetHeight())};
      const std::string engineName = m_name;
      dispatch_async(dispatch_get_main_queue(), ^{ [Bridge(engineName, false) command:request]; });
    }
    std::string text;
    if (state.visible)
      for (NSDictionary* cue in state.cues)
      {
        double time = state.sourceTime + state.settings.m_SubtitleDelay;
        if (time >= [cue[@"start"] doubleValue] && time < [cue[@"end"] doubleValue])
        {
          auto line = String(cue[@"text"]);
          if (!line.empty()) { if (!text.empty()) text += "\n"; text += line; }
        }
      }
    if (text != state.lastText)
    {
      state.text.FlushSubtitles();
      state.lastText = text;
      if (!text.empty())
      {
        std::string escaped;
        for (char c : text)
          if (c == '\n') escaped += "\\N";
          else if (c == '{' || c == '}' || c == '\\') { escaped += '\\'; escaped += c; }
          else escaped += c;
        state.text.AddSubtitle(escaped, 0, 24.0 * 3600 * 1000000);
      }
      OVERLAY::MarkDirty();
    }
    state.overlays.Release(0);
    state.overlays.SetVideoRect(state.source, state.dest, state.view);
    state.overlays.AddOverlay(state.overlay, 1000000, 0);
    state.overlays.PrepareOverlays(0);
    state.overlays.Render(0);
  }
}
