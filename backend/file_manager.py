import os

LANGUAGE_MAP = {
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
    '.kt': 'Kotlin',
}


class FileManager:
    def __init__(self):
        self.VALID_EXTENSIONS = set(LANGUAGE_MAP)
        self.IGNORED_DIRS = {
            'node_modules', '__pycache__', '.git', 'venv', 'env', 'dist', 'build'
        }

    def dialog_filter(self):
        """File-type filter for the Open dialog, built from the supported extensions."""
        patterns = ";".join(f"*{ext}" for ext in sorted(self.VALID_EXTENSIONS))
        return (f"Code Files ({patterns})", "All Files (*.*)")

    def scan_folder(self, folder_path):
        """Recursively scans a folder for code files."""
        files_found = []
        for root, dirs, files in os.walk(folder_path):
            # Filter out ignored directories in-place to prevent traversing them
            dirs[:] = [d for d in dirs if d not in self.IGNORED_DIRS]
            for file in files:
                if self._is_valid_file(file):
                    file_info = self.get_file_details(os.path.join(root, file))
                    if file_info:
                        files_found.append(file_info)
        return files_found

    def _is_valid_file(self, filename):
        _, ext = os.path.splitext(filename)
        return ext.lower() in self.VALID_EXTENSIONS

    def get_file_details(self, file_path):
        """Returns the object structure expected by the UI."""
        try:
            stats = os.stat(file_path)
            name = os.path.basename(file_path)
            return {
                "name": name,
                "path": os.path.abspath(file_path),
                "size": stats.st_size,
                "language": self._detect_language(name),
            }
        except OSError as e:
            print(f"Error reading details for {file_path}: {e}")
            return None

    def read_file_content(self, file_path):
        """
        Reads a file exactly as stored (line endings kept). Raises ValueError for
        files that aren't valid UTF-8, because writing a fix back would corrupt them.
        """
        try:
            with open(file_path, 'r', encoding='utf-8-sig', newline='') as f:
                return f.read()
        except UnicodeDecodeError:
            raise ValueError("File is not UTF-8 text, so it can't be analyzed safely.")

    def has_bom(self, file_path):
        with open(file_path, 'rb') as f:
            return f.read(3) == b'\xef\xbb\xbf'

    def save_file_content(self, file_path, content, bom=False):
        """Writes text back without translating line endings."""
        with open(file_path, 'w', encoding='utf-8-sig' if bom else 'utf-8', newline='') as f:
            f.write(content)

    def _detect_language(self, filename):
        _, ext = os.path.splitext(filename)
        return LANGUAGE_MAP.get(ext.lower(), 'Unknown')
