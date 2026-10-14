import xbmc
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'resources', 'lib'))
from dexhub_tvos_compat import install
from dexhub_tvos_compat.af3 import repair

install()
monitor = xbmc.Monitor()
if not monitor.waitForAbort(5):
    repair()
