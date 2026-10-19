"""
Verify NautiCAI backend imports and /api/health without starting a long-lived server.
Verify frontend production build (npm run build).

Usage (from repository root):
  python scripts/check_stack_health.py
  python scripts/check_stack_health.py --skip-npm
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-npm", action="store_true", help="Skip frontend npm run build")
    args = parser.parse_args()

    os.chdir(ROOT)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    print("=== Backend (import + /api/health) ===")
    try:
        from fastapi.testclient import TestClient

        from backend.main import app

        client = TestClient(app)
        r = client.get("/api/health")
        if r.status_code != 200:
            print(f"FAIL: /api/health status {r.status_code}")
            return 1
        body = r.json()
        print(f"OK: status={body.get('status')} model={body.get('model')} active={body.get('active_model')}")
    except Exception as e:
        print(f"FAIL: {e}")
        return 1

    if args.skip_npm:
        print("\n=== Frontend (skipped) ===")
        return 0

    print("\n=== Frontend (npm run build) ===")
    frontend = ROOT / "frontend"
    if not (frontend / "package.json").exists():
        print("FAIL: frontend/package.json missing")
        return 1
    shell = sys.platform == "win32"
    try:
        if not (frontend / "node_modules").exists():
            print("Installing npm dependencies (first run)...")
            subprocess.run("npm install", cwd=str(frontend), check=True, shell=shell)
        subprocess.run("npm run build", cwd=str(frontend), check=True, shell=shell)
        print("OK: production build finished")
    except subprocess.CalledProcessError as e:
        print(f"FAIL: npm run build exited {e.returncode}")
        return 1
    except FileNotFoundError:
        print("FAIL: npm not found — install Node.js LTS and retry")
        return 1

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
