import os
import zipfile
from pathlib import Path

def zip_project():
    base_dir = Path(__file__).resolve().parent
    output_filename = base_dir.parent / "FashionV3_Transfer.zip"
    
    # Folders to skip to keep the zip small
    exclude_dirs = {".venv", ".git", "__pycache__", "staticfiles", "node_modules"}
    
    print(f"[+] Creating zip archive: {output_filename}")
    
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(base_dir):
            # Prune directory search
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                # Skip the zip file itself if it's being created in the same folder
                if file == output_filename.name:
                    continue
                
                file_path = Path(root) / file
                archive_name = file_path.relative_to(base_dir)
                zipf.write(file_path, archive_name)
                
    print(f"[+] Success! Your project has been zipped and saved to: {output_filename}")
    print("[+] You can now copy this zip file to your new laptop.")

if __name__ == "__main__":
    zip_project()
