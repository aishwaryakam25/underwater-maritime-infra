import os
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    from ultralytics import YOLO

    pts = sorted(root.rglob("*.pt"))
    print(f"Found {len(pts)} .pt files under {root}")
    for p in pts:
        rel = p.relative_to(root)
        try:
            m = YOLO(str(p))
            n = len(getattr(m, "names", {}) or {})
            names = list((m.names or {}).values())[:12]
            print(f"{rel}  |  n_classes={n}  |  sample={names}")
        except Exception as e:
            print(f"{rel}  |  ERROR: {e}")

    print("\nTip: you're looking for n_classes=21.")


if __name__ == "__main__":
    # Avoid matplotlib GUI backends in some envs
    os.environ.setdefault("MPLBACKEND", "Agg")
    main()

