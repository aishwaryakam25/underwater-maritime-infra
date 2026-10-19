"""
Combined Analysis Endpoint - Add to sonar_routes.py
Analyzes sonar images (SubPipe) + underwater anomaly images (general model) together
"""

# This code should be added to backend/sonar_routes.py

@router.post("/analyze-combined")
async def analyze_combined(
    sonar_files: List[UploadFile] = File(...),
    anomaly_files: List[UploadFile] = File(...),
    confidence_threshold: float = 0.25,
):
    """
    Combined analysis: Sonar images (SubPipe) + Underwater anomaly images (General)
    Returns side-by-side comparison of both analyses
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    
    from detection import run_detection as run_general_detection
    from detection import annotate_image as annotate_general
    from detection import build_heatmap
    from severity import compute_risk, score_to_grade
    from visibility import full_enhance
    
    start = time.time()
    
    # Process sonar images (SubPipe + Marine-PULSE)
    sonar_results = []
    for file in sonar_files:
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
            continue
        
        contents = await file.read()
        img = Image.open(io.BytesIO(contents))
        
        # Run sonar detection (same as analyze_sonar_image)
        det_boxes = detect_pipeline(img, confidence_threshold)
        classifications = []
        for box in det_boxes:
            x1, y1, x2, y2, conf, cls_id = box
            roi = img.crop((x1, y1, x2, y2))
            cls_result = classify_pipeline_type(roi)
            classifications.append({
                "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                "confidence": conf,
                "class_name": cls_result["class_name"],
                "class_confidence": cls_result["confidence"],
                "severity": get_severity(cls_result["class_name"])
            })
        
        # Count severities
        critical = sum(1 for c in classifications if c["severity"] == "critical")
        high = sum(1 for c in classifications if c["severity"] == "high")
        medium = sum(1 for c in classifications if c["severity"] == "medium")
        low = sum(1 for c in classifications if c["severity"] == "low")
        
        sonar_results.append({
            "filename": file.filename,
            "type": "sonar",
            "total_detections": len(classifications),
            "critical_count": critical,
            "high_count": high,
            "medium_count": medium,
            "low_count": low,
            "detections": classifications,
            "image_width": img.width,
            "image_height": img.height,
        })
    
    # Process underwater anomaly images (General detection)
    anomaly_results = []
    for file in anomaly_files:
        contents = await file.read()
        pil_img = Image.open(io.BytesIO(contents)).convert("RGB")
        
        # Run general detection
        enhanced = full_enhance(pil_img, True, True, 0.0, True, False, 3.0, False)
        dets = run_general_detection(enhanced, confidence_threshold, 0.45, "general")
        
        annotated = annotate_general(enhanced, dets)
        heatmap = build_heatmap(enhanced, dets)
        risk = compute_risk(dets)
        grade = score_to_grade(risk)
        
        # Count severities
        sev_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        for d in dets:
            sev_counts[d.get("severity", "Medium")] += 1
        
        anomaly_results.append({
            "filename": file.filename,
            "type": "anomaly",
            "total_detections": len(dets),
            "critical_count": sev_counts["Critical"],
            "high_count": sev_counts["High"],
            "medium_count": sev_counts["Medium"],
            "low_count": sev_counts["Low"],
            "detections": dets,
            "risk_score": risk,
            "grade": grade,
            "annotated_b64": _pil_to_b64(annotated),
            "heatmap_b64": _pil_to_b64(heatmap),
        })
    
    # Combined summary
    total_sonar_dets = sum(r["total_detections"] for r in sonar_results)
    total_anomaly_dets = sum(r["total_detections"] for r in anomaly_results)
    total_critical = sum(r["critical_count"] for r in sonar_results + anomaly_results)
    
    # Generate insights for both
    sonar_insights = generate_insights(sonar_results) if sonar_results else None
    anomaly_insights = generate_insights([{
        "total_detections": r["total_detections"],
        "critical_count": r["critical_count"],
        "high_count": r["high_count"],
        "medium_count": r["medium_count"],
        "low_count": r["low_count"],
        "detections": [{"confidence": d.get("conf", 0), "class_name": d.get("cls", "")} for d in r["detections"]]
    } for r in anomaly_results]) if anomaly_results else None
    
    elapsed = time.time() - start
    
    return {
        "mode": "combined",
        "sonar": {
            "total_images": len(sonar_results),
            "total_detections": total_sonar_dets,
            "results": sonar_results,
            "insights": sonar_insights
        },
        "anomaly": {
            "total_images": len(anomaly_results),
            "total_detections": total_anomaly_dets,
            "results": anomaly_results,
            "insights": anomaly_insights
        },
        "combined_summary": {
            "total_images": len(sonar_results) + len(anomaly_results),
            "total_detections": total_sonar_dets + total_anomaly_dets,
            "total_critical": total_critical,
        },
        "processing_time": round(elapsed, 2)
    }


# Helper to convert PIL to base64
def _pil_to_b64(img):
    import io, base64
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()
