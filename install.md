🛠 Wolf AI – Setup Guide
1️⃣ Requirements

Python 3.12.x
pip
Windows / Linux / macOS
Check Python version:
python --version
If not 3.12, install from:
https://www.python.org/downloads/

🐍 2️⃣ Create Virtual Environment (Python 3.12)
Windows
python 3.12 -m venv venv
Activate:
venv\Scripts\activate
macOS / Linux
python3 3.12 -m venv venv
Activate:
source venv/bin/activate

After activation, your terminal should show:
(venv)

📦 3️⃣ Install Dependencies
If you have requirements.txt:
pip install -r requirements.txt
Or manually:
pip install pyinstaller

▶ 4️⃣ Run the Project In Terminal First (Just Overview)
Example:
python main.py

🚀 5️⃣ Convert to Executable (.exe) Using PyInstaller
Basic command:
pyinstaller --onefile main.py
If you want no console window (for GUI apps):
pyinstaller --onefile --noconsole main.py

📁 6️⃣ Understanding Generated Folders
After running PyInstaller, you will see:
build/
dist/
main.spec

📂 dist/ Folder (Important)
This is the final output folder.
Inside it:
dist/
 └── main.exe

 👉 This .exe file is your standalone application.
You can share this file with others — they do NOT need Python installed.







