#!/bin/bash

set -e

# Navigate to project root
cd "$(dirname "$0")/.."

# Create virtual environment if it does not exist
if [ ! -f "venv-linux/bin/python" ]; then
    python3 -m venv venv-linux
fi

# Activate virtual environment
source venv-linux/bin/activate

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
python -m pip install -r requirements.txt

# Install PyInstaller
python -m pip install pyinstaller

# Build executable
python -m PyInstaller \
    --onefile \
    --paths src \
    --add-binary "external/linux/libopus.so:external/linux" \
    --name voice-call \
    --distpath dist \
    --workpath build-linux \
    --specpath build-linux \
    src/main.py

echo ""
echo "Build completed successfully!"
echo "Executable: dist/voice-call"
