import os
import shutil
import glob

os.chdir(r"C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly")

print("ORGANIZING PROJECT...")

# Create folders
folders = {
    'scripts/training': [],
    'scripts/data_prep': [],
    'scripts/testing': [],
    'scripts/deployment': [],
    'datasets_archive': [],
    'reports': [],
    'archived/old_code': []
}

for f in folders:
    os.makedirs(f, exist_ok=True)

# Move files
moves = {
    'scripts/training': glob.glob('*train*.py') + glob.glob('sss_*.py') + glob.glob('marine_pulse*.py'),
    'scripts/data_prep': glob.glob('*prepare*.py') + glob.glob('*integrate*.py') + glob.glob('*download*.py') + glob.glob('copy_*.py'),
    'scripts/testing': glob.glob('test_*.py') + glob.glob('check_*.py') + glob.glob('fix_*.py') + glob.glob('find_*.py') + glob.glob('show_*.py') + glob.glob('verify*.py') + glob.glob('update_*.py') + glob.glob('add_*.py') + glob.glob('search*.py') + glob.glob('props.py') + glob.glob('restore*.py'),
    'scripts/deployment': glob.glob('deploy*.py') + glob.glob('deploy*.sh') + glob.glob('deploy*.ps1') + glob.glob('run-*.ps1') + glob.glob('setup*.ps1') + glob.glob('do-all*.ps1'),
    'reports': glob.glob('*Report.pdf'),
    'archived/old_code': glob.glob('*_backup.py') + glob.glob('insert_*.py') + glob.glob('upgrade_*.py') + glob.glob('replace_*.py') + glob.glob('remove_*.py'),
}

moved = 0
for dest, files in moves.items():
    for f in files:
        if os.path.exists(f) and os.path.isfile(f):
            try:
                shutil.move(f, os.path.join(dest, os.path.basename(f)))
                moved += 1
            except:
                pass

print(f"Moved {moved} files")
print("DONE! Open VS Code to see clean structure")