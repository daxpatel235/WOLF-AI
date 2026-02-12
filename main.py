import os
import sys
import json
import webview
from backend.bridge import ApiBridge

class WolfAIApp:
    def __init__(self):
        # Initialize the API Bridge (The Logic)
        self.api = ApiBridge()
        self.window = None

    def get_resource_path(self, relative_path):
        """
        Get absolute path to resource.
        Works for both development (source code) and PyInstaller (.exe).
        """
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def on_dropped(self, files):
        """
        Triggered when files/folders are dragged & dropped onto the window.
        """
        # print(f"Processing dropped files: {files}") # Debugging
        
        valid_files = []
        
        for path in files:
            if os.path.isdir(path):
                # If it's a folder, use our scanner to find all code files inside
                found = self.api.file_manager.scan_folder(path)
                valid_files.extend(found)
            elif os.path.isfile(path):
                # If it's a single file, check if it's a valid code file
                if self.api.file_manager._is_valid_file(path):
                    details = self.api.file_manager.get_file_details(path)
                    if details:
                        valid_files.append(details)
        
        if valid_files:
            # Send the data to JavaScript safely
            # json.dumps ensures that Windows paths (backslashes) don't break JS
            js_payload = json.dumps(valid_files)
            self.window.evaluate_js(f"handleFolderFiles({js_payload})")

    def run(self):
        """
        Launches the application window.
        """
        html_path = self.get_resource_path(os.path.join('web', 'index.html'))
        
        self.window = webview.create_window(
            title='Wolf AI Code Debugger',
            url=html_path,
            js_api=self.api,  # Expose Python functions to JS
            width=1400,
            height=900,
            min_size=(1000, 700),
            background_color='#0a0a0f',
            resizable=True
        )

        # Connect the window to the API bridge so dialogs work
        self.api.set_window(self.window)

        # Bind the Drop Event (Graceful fallback if not supported)
        try:
            if hasattr(self.window.events, 'dropped'):
                self.window.events.dropped += self.on_dropped
        except Exception:
            pass 

        # Start the GUI loop
        webview.start(debug=False)

if __name__ == '__main__':
    # Create and run the app
    app = WolfAIApp()
    app.run()
