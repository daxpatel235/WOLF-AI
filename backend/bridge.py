import json
import os
import sys
import socket
import webview
from .file_manager import FileManager
from .groq_client import GroqService

class ApiBridge:
    def __init__(self):
        self.file_manager = FileManager()
        self.groq_service = GroqService()
        self.window = None
        self._api_key = self._load_initial_key()

    def set_window(self, window):
        """Allows the bridge to access window features like file dialogs."""
        self.window = window

    def _load_initial_key(self):
        """
        Robustly finds the API key in 3 locations:
        1. Next to the .exe (User override)
        2. Inside the .exe (Bundled)
        3. In the source folder (Dev mode)
        """
        try:
            paths = [
                os.path.join(os.getcwd(), 'wolf_key.json'),
                os.path.join(sys._MEIPASS, 'wolf_key.json') if hasattr(sys, '_MEIPASS') else None,
                os.path.join(os.path.dirname(__file__), '..', 'wolf_key.json')
            ]
            for path in paths:
                if path and os.path.exists(path):
                    with open(path, 'r') as f:
                        return json.load(f).get('api_key', '')
        except:
            pass
        return ''

    # ==========================
    # NEW: Internet Connection Check & Quit
    # ==========================
    
    def check_connection(self):
        """
        Checks if internet is available by trying to connect to Google DNS.
        Returns True if connected, False otherwise.
        """
        try:
            # Try to connect to Google's DNS server (8.8.8.8) on port 53
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            return False
    
    def quit_app(self):
        """
        Force quit the application.
        """
        try:
            if self.window:
                self.window.destroy()
            sys.exit(0)
        except:
            sys.exit(0)

    # ==========================
    # Functions Callable from JS
    # ==========================

    def select_folder(self):
        """
        Triggered by the 'Select Folder' button.
        Opens a FOLDER dialog and scans recursively.
        """
        if not self.window: return []
        
        # 1. Open Folder Dialog
        folder_path = self.window.create_file_dialog(webview.FOLDER_DIALOG)
        
        # 2. If user picked a folder, scan it
        if folder_path and len(folder_path) > 0:
            # pywebview returns a tuple/list, we need the string path
            selected_path = folder_path[0]
            return self.file_manager.scan_folder(selected_path)
        return []

    def select_files(self):
        """
        Triggered by clicking the Drop Zone.
        Opens a FILE dialog to pick specific files.
        """
        if not self.window: return []
        
        # 1. Open File Dialog (Multi-select enabled)
        file_paths = self.window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=True,
            file_types=('Code Files (*.py;*.js;*.jsx;*.ts;*.tsx;*.html;*.css;*.java;*.cpp)', 'All Files (*.*)')
        )
        
        valid_files = []
        if file_paths:
            for path in file_paths:
                # 2. Get details for each selected file
                details = self.file_manager.get_file_details(path)
                if details:
                    valid_files.append(details)
                    
        return valid_files

    def start_analysis(self, file_path, language):
        """
        Reads code, sends to Groq, auto-saves fix, returns result.
        """
        code = self.file_manager.read_file_content(file_path)
        filename = os.path.basename(file_path)
        
        result = self.groq_service.analyze_code(
            self._api_key, code, filename, language
        )
        
        # Auto-save logic if a fix is provided
        if result['success'] and result.get('fixedCode') and result['fixedCode'] != code:
            self.file_manager.save_file_content(file_path, result['fixedCode'])
            
        return result

    def save_report(self, filename, content):
        """
        Saves the HTML report to disk.
        """
        if not self.window: return False
        
        save_path = self.window.create_file_dialog(
            webview.SAVE_DIALOG, 
            save_filename=filename, 
            file_types=('HTML Files (*.html)',)
        )
        
        if save_path:
            try:
                final_path = save_path if isinstance(save_path, str) else save_path[0]
                with open(final_path, 'w', encoding='utf-8') as f: 
                    f.write(content)
                return True
            except: 
                return False
        return False

    def check_api_key(self):
        """Validates the key format."""
        return bool(self._api_key and self._api_key.startswith("gsk_"))
