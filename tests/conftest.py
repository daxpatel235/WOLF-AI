import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# The backend imports pywebview for its dialog constants. CI doesn't need a GUI,
# so use a stand-in when pywebview isn't installed.
try:
    import webview  # noqa: F401
except ImportError:
    sys.modules["webview"] = types.SimpleNamespace(FOLDER_DIALOG=20, OPEN_DIALOG=10, SAVE_DIALOG=30)
