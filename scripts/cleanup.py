import os
import shutil
import glob

print("Organizing project files...")

# Create folders
folders = ['scripts', 'scripts/testing', 'scripts/data_prep', 'archived']
for f in folders:
    os.makedirs(f, exist_ok=True)
    print(f"Created: {f}")

# Move test scripts
test_scripts = glob.glob('*test*.py') + glob.glob('*fix*.py') + glob.glob('*check*.py') + glob.glob('*update*.py') + glob.glob('*add*.py')
for script in test_scripts:
    if os.path.isfile(script):
        shutil.move(script, f'scripts/testing/{script}')

# Move data prep
data_scripts = glob.glob('*prepare*.py') + glob.glob('*integrate*.py') + glob.glob('*download*.py')
for script in data_scripts:
    if os.path.isfile(script) and not os.path.exists(f'scripts/data_prep/{script}'):
        shutil.move(script, f'scripts/data_prep/{script}')

print("\nDONE! Project organized!")
print("Open in VS Code to see clean structure")