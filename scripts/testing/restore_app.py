import shutil
import os

file_path = r"frontend\src\App.jsx"
backup_path = file_path + ".backup"

print("Restoring App.jsx...")

if os.path.exists(backup_path):
    shutil.copy2(backup_path, file_path)
    print("RESTORED! Your app is back to normal")
else:
    print("No backup - file unchanged")

print("\nRestart: cd frontend && npm start")