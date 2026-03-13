"""
=============================================================================
05_video_multiframe.py — Multi-frame defect accumulation
=============================================================================
Runs detection across all video frames (or sampled frames).
Accumulates defects across frames using spatial proximity matching.
Result: a unified defect map with temporal confidence (how many frames
each defect appeared in).
=============================================================================
"""

import cv2
import numpy as np
import base64
import json
from pathlib import Path
from typing import List, Dict
from ultralytics import YOLO
from dataclasses import dataclass, field


CLASSES = [
    "corrosion", "crack", "biofouling", "coating_damage",
    "anode_depletion", "marine_growth", "dent",
    "weld_defect", "leak", "free_span",
]

SEV_MAP = {
    "corrosion":"Critical","crack":"Critical","leak":"Critical",
    "weld_defect":"High","anode_depletion":"High","free_span":"High",
    "coating_damage":"Medium","dent":"Medium",
    "marine_growth":"Low","biofouling":"Low",
}


@dataclass
class AccumulatedDefect:
    """A defect that has been seen across multiple frames."""
    id:           int
    cls:          str
    severity:     str
    frames_seen:  int    = 0       # how many frames this defect appeared in
    total_frames: int    = 0       # total frames processed
    conf_sum:     float  = 0.0
    pipe_pos_sum: float  = 0.0     # accumulate for averaging
    angle_sum:    float  = 0.0
    bboxes:       list   = field(default_factory=list)

    @property
    def temporal_confidence(self) -> float:
        """How consistently this defect appears across frames (0-1)."""
        return self.frames_seen / max(self.total_frames, 1)

    @property
    def avg_conf(self) -> float:
        return self.conf_sum / max(self.frames_seen, 1)

    @property
    def avg_pipe_pos(self) -> float:
        return self.pipe_pos_sum / max(self.frames_seen, 1)

    @property
    def avg_angle(self) -> float:
        return self.angle_sum / max(self.frames_seen, 1)


def iou_overlap(b1: dict, b2: dict) -> float:
    """Compute IoU between two bbox dicts."""
    x1 = max(b1["xmin"], b2["xmin"])
    y1 = max(b1["ymin"], b2["ymin"])
    x2 = min(b1["xmax"], b2["xmax"])
    y2 = min(b1["ymax"], b2["ymax"])
    inter = max(0, x2-x1) * max(0, y2-y1)
    if inter == 0:
        return 0.0
    a1 = (b1["xmax"]-b1["xmin"]) * (b1["ymax"]-b1["ymin"])
    a2 = (b2["xmax"]-b2["xmin"]) * (b2["ymax"]-b2["ymin"])
    return inter / (a1 + a2 - inter + 1e-6)


def accumulate_defects(
    video_path:    str,
    weights:       str   = "weights/best.pt",
    conf_thr:      float = 0.25,
    iou_thr:       float = 0.45,
    sample_fps:    int   = 2,      # frames per second to sample
    match_iou:     float = 0.3,    # IoU threshold to match across frames
    min_temporal:  float = 0.2,    # defect must appear in ≥20% of frames
) -> dict:
    """
    Process video and accumulate defects across frames.
    
    Returns unified defect list with temporal_confidence — a measure
    of how real each defect is (not just a single-frame false positive).
    """
    model = YOLO(weights)
    cap   = cv2.VideoCapture(video_path)

    fps        = cap.get(cv2.CAP_PROP_FPS) or 25
    total_vid_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_step = max(1, int(fps / sample_fps))
    w          = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h          = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"Video: {total_vid_frames} frames @ {fps:.1f}fps  →  sampling every {frame_step} frames")

    accumulated: List[AccumulatedDefect] = []
    frame_idx   = 0
    frames_processed = 0
    best_frame  = None
    best_det_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_step != 0:
            frame_idx += 1
            continue

        frames_processed += 1

        # run detection
        results = model.predict(frame, conf=conf_thr, iou=iou_thr, verbose=False)
        result  = results[0]

        frame_dets = []
        for box in result.boxes:
            cls_id   = int(box.cls[0])
            cls_name = CLASSES[cls_id] if cls_id < len(CLASSES) else f"class_{cls_id}"
            conf_val = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            bbox = {"xmin":x1,"ymin":y1,"xmax":x2,"ymax":y2}
            frame_dets.append({
                "cls":      cls_name,
                "conf":     conf_val,
                "bbox":     bbox,
                "pipe_pos": (x1+x2)/2/w,
                "angle":    (y1+y2)/2/h,
            })

        # update temporal confidence for each accumulated defect
        for acc in accumulated:
            acc.total_frames += 1

        # match frame detections to accumulated defects
        matched = set()
        for det in frame_dets:
            best_match = None
            best_iou   = match_iou
            for i, acc in enumerate(accumulated):
                if acc.cls != det["cls"]:
                    continue
                if not acc.bboxes:
                    continue
                avg_bbox = {
                    "xmin": np.mean([b["xmin"] for b in acc.bboxes[-5:]]),
                    "ymin": np.mean([b["ymin"] for b in acc.bboxes[-5:]]),
                    "xmax": np.mean([b["xmax"] for b in acc.bboxes[-5:]]),
                    "ymax": np.mean([b["ymax"] for b in acc.bboxes[-5:]]),
                }
                iou = iou_overlap(det["bbox"], avg_bbox)
                if iou > best_iou:
                    best_iou   = iou
                    best_match = i

            if best_match is not None:
                acc = accumulated[best_match]
                acc.frames_seen   += 1
                acc.conf_sum      += det["conf"]
                acc.pipe_pos_sum  += det["pipe_pos"]
                acc.angle_sum     += det["angle"]
                acc.bboxes.append(det["bbox"])
                matched.add(best_match)
            else:
                # new defect
                new_acc = AccumulatedDefect(
                    id       = len(accumulated),
                    cls      = det["cls"],
                    severity = SEV_MAP.get(det["cls"], "Unknown"),
                )
                new_acc.frames_seen  = 1
                new_acc.total_frames = 1
                new_acc.conf_sum     = det["conf"]
                new_acc.pipe_pos_sum = det["pipe_pos"]
                new_acc.angle_sum    = det["angle"]
                new_acc.bboxes       = [det["bbox"]]
                accumulated.append(new_acc)

        # save best frame (most detections)
        if len(frame_dets) >= best_det_count:
            best_det_count = len(frame_dets)
            best_frame     = frame.copy()

        frame_idx += 1
        if frames_processed % 10 == 0:
            print(f"  Processed {frames_processed} frames  |  Tracked {len(accumulated)} defects")

    cap.release()

    # filter by temporal confidence
    stable = [
        acc for acc in accumulated
        if acc.temporal_confidence >= min_temporal
    ]

    print(f"\n── Multi-frame Accumulation Results ──────────────────")
    print(f"  Frames processed:     {frames_processed}")
    print(f"  Raw defects tracked:  {len(accumulated)}")
    print(f"  Stable defects (≥{min_temporal:.0%} temporal): {len(stable)}")

    # build output
    defect_list = []
    for acc in sorted(stable, key=lambda x: -x.temporal_confidence):
        avg_bbox = {
            "xmin": int(np.mean([b["xmin"] for b in acc.bboxes])),
            "ymin": int(np.mean([b["ymin"] for b in acc.bboxes])),
            "xmax": int(np.mean([b["xmax"] for b in acc.bboxes])),
            "ymax": int(np.mean([b["ymax"] for b in acc.bboxes])),
        }
        d = {
            "id":                   acc.id,
            "cls":                  acc.cls,
            "severity":             acc.severity,
            "conf":                 round(acc.avg_conf, 4),
            "temporal_confidence":  round(acc.temporal_confidence, 3),
            "frames_seen":          acc.frames_seen,
            "frames_total":         frames_processed,
            "bbox":                 avg_bbox,
            "pipe_pos":             round(acc.avg_pipe_pos, 4),
            "angle":                round(acc.avg_angle, 4),
        }
        defect_list.append(d)
        print(f"  {acc.cls:<20} temporal={acc.temporal_confidence:.1%}  conf={acc.avg_conf:.2f}  frames={acc.frames_seen}/{frames_processed}")

    # encode best frame
    best_b64 = ""
    if best_frame is not None:
        _, buf = cv2.imencode(".jpg", best_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        best_b64 = base64.b64encode(buf).decode()

    # compute overall risk
    if defect_list:
        crit  = sum(1 for d in defect_list if d["severity"] == "Critical")
        high  = sum(1 for d in defect_list if d["severity"] == "High")
        risk  = min(100, crit * 25 + high * 15 + len(defect_list) * 3)
        grade = "A" if risk < 20 else "B" if risk < 40 else "C" if risk < 60 else "D" if risk < 80 else "F"
    else:
        risk, grade = 0, "A"

    return {
        "detections":       defect_list,
        "total":            len(defect_list),
        "frames_processed": frames_processed,
        "risk_score":       risk,
        "grade":            grade,
        "best_frame_b64":   best_b64,
        "img_width":        w,
        "img_height":       h,
        "note":             f"Defects confirmed across ≥{min_temporal:.0%} of {frames_processed} sampled frames",
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  Segmentation:  python scripts.py seg  <image.jpg> <weights.pt>")
        print("  Multi-frame:   python scripts.py vid  <video.mp4> <weights.pt>")
        sys.exit(0)

    mode = sys.argv[1]

    if mode == "seg":
        img_path = sys.argv[2]
        weights  = sys.argv[3] if len(sys.argv) > 3 else "weights/best_seg.pt"
        result   = run_segmentation(img_path, weights)
        out = Path(img_path).stem + "_seg_result.json"
        with open(out, "w") as f:
            json.dump({k: v for k, v in result.items() if k != "annotated_b64"}, f, indent=2)
        print(f"\n✅ {result['total']} defects with masks → {out}")

    elif mode == "vid":
        vid_path = sys.argv[2]
        weights  = sys.argv[3] if len(sys.argv) > 3 else "weights/best.pt"
        result   = accumulate_defects(vid_path, weights)
        out = Path(vid_path).stem + "_multiframe_result.json"
        with open(out, "w") as f:
            json.dump({k: v for k, v in result.items() if k != "best_frame_b64"}, f, indent=2)
        print(f"\n✅ {result['total']} stable defects across {result['frames_processed']} frames → {out}")
