import json
import logging
import os
import sys
import traceback
from logging.handlers import RotatingFileHandler

import webview

from backend.bridge import ApiBridge
from backend.config import app_data_dir
from backend.version import APP_NAME, __version__

log = logging.getLogger("wolfai")


def setup_logging():
    """Logs go to %APPDATA%\\WolfAI\\wolfai.log so problems in the windowed .exe can be diagnosed."""
    try:
        handler = RotatingFileHandler(os.path.join(app_data_dir(), "wolfai.log"),
                                      maxBytes=1_000_000, backupCount=2, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logging.basicConfig(level=logging.INFO, handlers=[handler])
    except OSError:
        logging.basicConfig(level=logging.INFO)


def show_fatal_error(message):
    """The .exe has no console, so startup errors are shown in a message box."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, message, APP_NAME, 0x10)
            return
        except Exception:
            pass
    print(message, file=sys.stderr)


def get_resource_path(relative_path):
    """Absolute path to a bundled resource, for both source runs and PyInstaller builds."""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


class WolfAIApp:
    def __init__(self):
        self.api = ApiBridge()
        self.window = None

    def on_drop(self, event):
        """Files/folders dropped anywhere on the window are added to the queue."""
        try:
            files = (event.get("dataTransfer") or {}).get("files") or []
            paths = [f.get("pywebviewFullPath") for f in files if f.get("pywebviewFullPath")]
            valid_files = self.api.files_from_paths(paths)
            if valid_files:
                # json.dumps keeps Windows backslashes valid inside the JS call
                self.window.evaluate_js(f"handleFolderFiles({json.dumps(valid_files)})")
            elif paths:
                self.window.evaluate_js("showToast('No supported code files in the dropped items', 'warning')")
        except Exception:
            log.exception("Drop handling failed")

    def bind_events(self, window):
        """Runs once the window is up. Drag & drop is optional; failure here must not stop the app."""
        try:
            from webview.dom import DOMEventHandler

            def ignore(_event):
                pass

            # prevent_default on dragover/drop stops WebView2 from navigating to the dropped file
            window.dom.document.events.dragover += DOMEventHandler(ignore, True, True, debounce=500)
            window.dom.document.events.drop += DOMEventHandler(self.on_drop, True, True)
        except Exception:
            log.exception("Could not enable drag & drop")

    def run(self):
        html_path = get_resource_path(os.path.join("Web", "index.html"))
        if not os.path.exists(html_path):
            raise FileNotFoundError(f"UI files are missing: {html_path}")

        self.window = webview.create_window(
            title=APP_NAME,
            url=html_path,
            js_api=self.api,
            width=1400,
            height=900,
            min_size=(1000, 700),
            background_color="#0a0a0f",
            resizable=True,
        )
        self.api.set_window(self.window)

        # On Windows, require WebView2 (Edge). Without it pywebview could fall back to an
        # engine that can't run the modern UI and the window would stay blank.
        gui = "edgechromium" if sys.platform == "win32" else None
        webview.start(self.bind_events, self.window, gui=gui, debug=False)


def main():
    setup_logging()
    log.info("Starting %s %s", APP_NAME, __version__)
    try:
        WolfAIApp().run()
    except Exception as e:
        log.error("Fatal error:\n%s", traceback.format_exc())
        hint = ""
        if sys.platform == "win32" and ("webview2" in str(e).lower() or "edgechromium" in str(e).lower()):
            hint = "\n\nInstall the Microsoft Edge WebView2 Runtime and try again."
        show_fatal_error(f"{APP_NAME} could not start.\n\n{e}{hint}\n\n"
                         f"Details: {os.path.join(app_data_dir(), 'wolfai.log')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
