import shutil
import os

file_path = r"frontend\src\App.jsx"
backup = file_path + ".backup"

if os.path.exists(backup):
    shutil.copy2(backup, file_path)
    print("RESTORED! App.jsx is working again")
else:
    print("No backup found")