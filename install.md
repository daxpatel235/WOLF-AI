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

🚀 5️⃣ Build installers
Each platform is built on its own OS. See "Building installers" in README.md for the tools each one needs.
Windows (x64-setup.exe + .msi):
.\scripts\build.ps1
macOS (.dmg for the Mac's architecture):
bash scripts/build_macos.sh
Linux (.AppImage, .deb, .rpm):
pip install -r requirements-linux.txt
bash scripts/build_linux.sh

Everything ends up in dist/. Check a build without opening a window:
dist/WolfAI/WolfAI --self-test

Never bundle wolf_key.json: anyone with the installer could extract the key.
GitHub Actions builds and checks all of these automatically on every push.
