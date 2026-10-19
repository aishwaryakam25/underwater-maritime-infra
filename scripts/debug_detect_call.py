import json
import mimetypes
import os
import urllib.request
import uuid


def _add_field(parts: list[bytes], boundary: str, name: str, value: str) -> None:
    parts.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        ).encode()
    )


def _add_file(
    parts: list[bytes], boundary: str, name: str, filename: str, content: bytes, content_type: str
) -> None:
    parts.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode()
        + content
        + b"\r\n"
    )


def main() -> None:
    url = os.environ.get("NAUTICAI_API_DETECT_URL", "http://127.0.0.1:8000/api/detect")
    import sys
    img_path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("NAUTICAI_API_DETECT_IMAGE")
    if not img_path:
        raise SystemExit(
            "Pass an image path as argv[1] (or set NAUTICAI_API_DETECT_IMAGE) and re-run."
        )

    form = {
        "conf_thr": os.environ.get("NAUTICAI_CONF", "0.05"),
        "iou_thr": os.environ.get("NAUTICAI_IOU", "0.45"),
        "mode": os.environ.get("NAUTICAI_MODE", "general"),
        "sev_filter": os.environ.get("NAUTICAI_SEV_FILTER", "All Detections"),
        "use_clahe": os.environ.get("NAUTICAI_USE_CLAHE", "true"),
        "clahe_clip": os.environ.get("NAUTICAI_CLAHE_CLIP", "3.0"),
        "use_green": os.environ.get("NAUTICAI_USE_GREEN", "true"),
        "use_edge": os.environ.get("NAUTICAI_USE_EDGE", "false"),
        "turbidity_in": os.environ.get("NAUTICAI_TURBIDITY", "0"),
        "corr_turb": os.environ.get("NAUTICAI_CORR_TURB", "true"),
        "marine_snow": os.environ.get("NAUTICAI_MARINE_SNOW", "false"),
    }

    boundary = "----nauticai" + uuid.uuid4().hex
    parts: list[bytes] = []
    for k, v in form.items():
        _add_field(parts, boundary, k, str(v))

    with open(img_path, "rb") as f:
        content = f.read()
    ctype = mimetypes.guess_type(img_path)[0] or "application/octet-stream"
    _add_file(parts, boundary, "file", os.path.basename(img_path), content, ctype)

    body = b"".join(parts) + f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    with urllib.request.urlopen(req) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    obj = json.loads(raw)

    print("status: ok")
    print("total:", obj.get("total"))
    dets = obj.get("detections") or []
    print("first_two:", dets[:2])


if __name__ == "__main__":
    main()

