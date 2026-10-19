import shutil

# Add innovation routes to main.py
lines_to_add = '''
# ── Innovation Routes ─────────────────────────────────────────────────────────
try:
    from innovation_routes import router as innovation_router
    app.include_router(innovation_router)
    print("✅ Innovation routes loaded!")
except ImportError as e:
    print(f"⚠️ Innovation routes not loaded: {e}")

# Signups file
_signups_file = Path(__file__).resolve().parent / "signups.json"
_report_downloads = {}
'''

with open('backend/main.py', 'r') as f:
    content = f.read()

# Insert after app.add_middleware block
insert_after = 'allow_headers=["*"],\n)'
updated = content.replace(insert_after, insert_after + '\n' + lines_to_add)

with open('backend/main.py', 'w') as f:
    f.write(updated)

print("✅ main.py updated!")