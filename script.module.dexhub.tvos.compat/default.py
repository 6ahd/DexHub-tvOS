import xbmcgui
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'resources', 'lib'))
from dexhub_tvos_compat import install
from dexhub_tvos_compat.af3 import repair

install()
repaired, failed = repair()
xbmcgui.Dialog().ok('DexWorld Apple TV',
    'ملفات أُصلحت / Restored: %d\nملفات تعذّر نسخها / Failed: %d\nأعد تحميل السكين بعد إصلاح الخط. / Reload skin after font repair.' % (len(repaired), len(failed)))
