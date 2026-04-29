#!/bin/bash
# Export Project Data for Transfer

VENV_PATH=".venv"

if [ ! -d "$VENV_PATH" ]; then
    echo "[!] Virtual environment not found. Please run ./setup.sh first."
    exit 1
fi

echo "[+] Exporting database data to data.json..."
PYTHONIOENCODING=utf-8 ./$VENV_PATH/bin/python manage.py dumpdata --exclude contenttypes --exclude auth.Permission --indent 2 -o data.json

if [ -f "data.json" ]; then
    echo "[+] Success! data.json created."
    echo "[+] You can now zip the project (including data.json) and move it to the new laptop."
else
    echo "[!] Failed to create data.json."
fi
