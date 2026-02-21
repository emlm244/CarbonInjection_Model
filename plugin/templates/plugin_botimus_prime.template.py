import pathlib
import sys

_PLUGIN_DIR = pathlib.Path(__file__).resolve().parent / "botimus_prime"
if str(_PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_DIR))

from plugin_botimus import plugin_BotimusPrime
