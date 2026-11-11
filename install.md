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

🔑 Add your API key
Start the app and open Settings (⚙ in the title bar), then paste your Groq API key.
Do NOT put the key in the project folder or in the build: it is stored in your user profile.

🚀 5️⃣ Convert to Executable (.exe) Using PyInstaller
The UI files in Web/ must be bundled with the app (Windows uses ; and macOS/Linux use : in --add-data):
Windows:
pyinstaller --onefile --noconsole --add-data "Web;Web" --name WolfAI main.py
macOS / Linux:
pyinstaller --onefile --noconsole --add-data "Web:Web" --name WolfAI main.py
Never add wolf_key.json to --add-data: anyone with the .exe could extract the key.

📁 6️⃣ Understanding Generated Folders
After running PyInstaller, you will see:
build/
dist/
WolfAI.spec

📂 dist/ Folder (Important)
This is the final output folder.
Inside it:
dist/
 └── WolfAI.exe

 👉 This .exe file is your standalone application.
You can share this file with others — they do NOT need Python installed.







