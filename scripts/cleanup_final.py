import os
import shutil
import glob

os.chdir(r"C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly")

print("CLEANING UP PROJECT...")

# Create folders
os.makedirs('scripts', exist_ok=True)
os.makedirs('datasets_archive', exist_ok=True)
os.makedirs('reports', exist_ok=True)

# Move ALL .py files to scripts/
py_files = [f for f in glob.glob('*.py') if os.path.isfile(f)]
for f in py_files:
    shutil.move(f, 'scripts/' + f)
print(f"Moved {len(py_files)} Python files to scripts/")

# Move ALL .pdf to reports/
pdfs = glob.glob('*.pdf')
for f in pdfs:
    shutil.move(f, 'reports/' + f)
print(f"Moved {len(pdfs)} PDFs to reports/")

# Move .zip files
zips = glob.glob('*.zip')
for f in zips:
    shutil.move(f, 'datasets_archive/' + f)
print(f"Moved {len(zips)} zips to datasets_archive/")

# Move .ps1, .sh, .cmd
scripts = glob.glob('*.ps1') + glob.glob('*.sh') + glob.glob('*.cmd')
for f in scripts:
    shutil.move(f, 'scripts/' + f)
print(f"Moved {len(scripts)} script files")

# Move .txt, .md (except README.md)
docs = [f for f in glob.glob('*.txt') + glob.glob('*.md') if f != 'README.md']
for f in docs:
    shutil.move(f, 'docs/' + f)

print("\nDONE! Root is clean!")
print("\nROOT NOW HAS:")
print("  backend/, frontend/, app/")
print("  scripts/, datasets_archive/, reports/, docs/")