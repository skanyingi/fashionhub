#!/bin/bash
# Project Setup for Linux/macOS

VENV_PATH=".venv"

if [ ! -d "$VENV_PATH" ]; then
    echo "[+] Creating virtual environment..."
    python3 -m venv $VENV_PATH
fi

echo "[+] Running setup script..."
./$VENV_PATH/bin/python3 setup_project.py

echo "[+] Setup complete! To start the server, run:"
echo "source $VENV_PATH/bin/activate"
echo "python manage.py runserver"
