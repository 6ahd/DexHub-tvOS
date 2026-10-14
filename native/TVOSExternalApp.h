/*
 *  Copyright (C) 2026 Team Kodi
 *  This file is part of Kodi - https://kodi.tv
 *
 *  SPDX-License-Identifier: GPL-2.0-or-later
 *  See LICENSES/README.md for more information.
 */

#pragma once

#include <string>

class CTVOSExternalApp
{
public:
  /*!
   \brief Open another installed tvOS app via its custom URL scheme.
   \param url a full url, e.g. "infuse://x-callback-url/play?url=...&sub=..."
   \return true if the open request was dispatched to the system
   */
  static bool OpenURL(const std::string& url);
};
