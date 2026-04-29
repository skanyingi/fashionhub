import os
import subprocess
import sys
import shutil
from pathlib import Path

def print_step(message):
    print(f"\n[+] {message}")

def print_error(message):
    print(f"\n[!] ERROR: {message}")

def run_command(command, shell=False):
    try:
        subprocess.check_call(command, shell=shell)
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {' '.join(command) if isinstance(command, list) else command}")
        sys.exit(1)

def setup():
    base_dir = Path(__file__).resolve().parent
    venv_dir = base_dir / ".venv"
    
    print_step("Project Setup started...")

    # 1. Create Virtual Environment
    if not venv_dir.exists():
        print_step("Creating virtual environment...")
        run_command([sys.executable, "-m", "venv", str(venv_dir)])
    else:
        print_step("Virtual environment already exists.")

    # 2. Determine venv python path
    if os.name == "nt":
        venv_python = venv_dir / "Scripts" / "python.exe"
        venv_pip = venv_dir / "Scripts" / "pip.exe"
    else:
        venv_python = venv_dir / "bin" / "python"
        venv_pip = venv_dir / "bin" / "pip"

    # 3. Upgrade pip
    print_step("Updating pip...")
    run_command([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])

    # 4. Install requirements
    requirements_file = base_dir / "requirements.txt"
    if requirements_file.exists():
        print_step("Installing dependencies from requirements.txt...")
        run_command([str(venv_pip), "install", "-r", str(requirements_file)])
    else:
        print_error("requirements.txt not found!")

    # 5. Handle .env file
    env_file = base_dir / "fashion_project" / ".env"
    env_example = base_dir / ".env.example"
    
    if not env_file.exists():
        if env_example.exists():
            print_step("Creating .env file from .env.example...")
            shutil.copy(str(env_example), str(env_file))
            print("Please update fashion_project/.env with your actual secret keys if necessary.")
        else:
            print_step("Creating a basic .env file...")
            with open(env_file, "w") as f:
                f.write("SECRET_KEY=django-insecure-development-key\nDEBUG=True\n")
    else:
        print_step(".env file already exists.")

    # 6. Run Migrations
    print_step("Running database migrations...")
    # Using python manage.py migrate
    # Note: This might fail if the database (PostgreSQL) is not set up.
    try:
        run_command([str(venv_python), "manage.py", "migrate"])
    except SystemExit:
        print_error("Migrations failed. Ensure your database (e.g., PostgreSQL) is running and configured in .env")
        print("Continuing setup anyway...")

    # 7. Collect Static
    print_step("Collecting static files...")
    run_command([str(venv_python), "manage.py", "collectstatic", "--noinput"])

    # 8. Load Data (if backup exists)
    data_file = base_dir / "data.json"
    if data_file.exists():
        print_step("Found data.json. Importing database data...")
        try:
            # Set environment variable for UTF-8 encoding
            os.environ["PYTHONIOENCODING"] = "utf-8"
            run_command([str(venv_python), "manage.py", "loaddata", "data.json"])
            print("Data imported successfully!")
        except SystemExit:
            print_error("Failed to load data.json. This usually happens if the database schema doesn't match the data file.")
    else:
        print("\n[i] No data.json found. Skipping data import.")

    print_step("Setup complete!")
    print("\nTo run the project:")
    if os.name == "nt":
        print(f"  {venv_dir}\\Scripts\\activate")
    else:
        print(f"  source {venv_dir}/bin/activate")
    print("  python manage.py runserver")

if __name__ == "__main__":
    setup()
