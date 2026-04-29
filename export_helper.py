import os
import subprocess
import sys

def export():
    # Use the current python interpreter to run manage.py
    # We set PYTHONIOENCODING to utf-8 to avoid charmap errors on Windows
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    
    print("[+] Exporting database data to data.json (UTF-8)...")
    
    # We use a context manager to open the file with utf-8 encoding and pass the handle
    with open("data.json", "w", encoding="utf-8") as f:
        try:
            subprocess.run(
                [sys.executable, "manage.py", "dumpdata", "--exclude", "contenttypes", "--exclude", "auth.Permission", "--indent", "2"],
                stdout=f,
                env=env,
                check=True
            )
            print("[+] Success! data.json created.")
        except subprocess.CalledProcessError as e:
            print(f"[!] Failed to export data: {e}")

if __name__ == "__main__":
    export()
