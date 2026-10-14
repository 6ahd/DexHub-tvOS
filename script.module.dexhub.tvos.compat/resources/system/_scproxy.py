"""tvOS-only SystemConfiguration fallback for embedded Kodi Python.

Packaged into the tvOS app, never the host Python installation. urllib.request
continues to use environment and explicitly configured proxies as usual.
"""


def _get_proxy_settings():
    return {'exclude_simple': False, 'exceptions': []}


def _get_proxies():
    return {}
