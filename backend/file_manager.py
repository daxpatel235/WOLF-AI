import os

class FileManager:
    def __init__(self):
        # Exact extension list from your main.js 
        self.VALID_EXTENSIONS = {
            '.py', '.js', '.jsx', '.ts', '.tsx', '.java', 
            '.cpp', '.c', '.go', '.rs', '.php', '.rb', '.swift', '.kt'
        }
        
        # Exact ignored directories from your main.js 
        self.IGNORED_DIRS = {
            'node_modules', '__pycache__', '.git', 'venv', 'env', 'dist', 'build'
        }

    def scan_folder(self, folder_path):
        """
        Recursively scans a folder for code files.
        Mirrors the 'scanFolder' function in main.js.
        """
        files_found = []

        # Walk through the directory tree
        for root, dirs, files in os.walk(folder_path):
            # Filter out ignored directories in-place to prevent traversing them
            dirs[:] = [d for d in dirs if d not in self.IGNORED_DIRS]

            for file in files:
                if self._is_valid_file(file):
                    full_path = os.path.join(root, file)
                    file_info = self.get_file_details(full_path)
                    if file_info:
                        files_found.append(file_info)
        
        return files_found

    def _is_valid_file(self, filename):
        """Checks if the file extension is in our allowed list."""
        _, ext = os.path.splitext(filename)
        return ext.lower() in self.VALID_EXTENSIONS

    def get_file_details(self, file_path):
        """
        Returns the object structure expected by the UI.
        """
        try:
            stats = os.stat(file_path)
            name = os.path.basename(file_path)
            
            return {
                "name": name,
                "path": file_path,
                "size": stats.st_size,
                "language": self._detect_language(name)
            }
        except Exception as e:
            print(f"Error reading details for {file_path}: {e}")
            return None

    def read_file_content(self, file_path):
        """Safe file reading with encoding handling."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def save_file_content(self, file_path, content):
        """Writes the fixed code back to the file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error saving file {file_path}: {e}")
            return False

    def _detect_language(self, filename):
        """
        Maps extensions to readable language names.
        Mirrors the 'detectLanguage' function in renderer.js.
        """
        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        
        language_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.jsx': 'React',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript React',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.go': 'Go',
            '.rs': 'Rust',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.swift': 'Swift',
            '.kt': 'Kotlin'
        }
        return language_map.get(ext, 'Unknown')
