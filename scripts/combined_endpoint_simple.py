# This is the working combined endpoint - add to sonar_routes.py at the end

@router.post("/analyze-combined-simple")
async def analyze_combined_simple(
    sonar_files: List[UploadFile] = File([]),
    anomaly_files: List[UploadFile] = File([]),
    confidence_threshold: float = 0.25,
):
    """Simple combined analysis - uses existing detection functions"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    
    from detection import run_detection, annotate_image, build_heatmap
    from visibility import full_enhance
    from severity import compute_risk, score_to_grade
    
    # Process sonar with sonar detection
    sonar_results = []
    for file in sonar_files:
        try:
            img_bytes = await file.read()
            img = Image.open(io.BytesIO(img_bytes))
            # Use sonar detection
            boxes = detect_pipeline(img, confidence_threshold)
            sonar_results.append({
                "filename": file.filename,
                "total_detections": len(boxes),
                "detections": boxes
            })
        except:
            pass
    
    # Process anomaly with general detection
    anomaly_results = []
    for file in anomaly_files:
        try:
            img_bytes = await file.read()
            pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            enhanced = full_enhance(pil_img, True, True, 0, True, False, 3.0, False)
            dets = run_detection(enhanced, confidence_threshold, 0.45, "general")
            risk = compute_risk(dets)
            grade = score_to_grade(risk)
            
            anomaly_results.append({
                "filename": file.filename,
                "total_detections": len(dets),
                "risk_score": risk,
                "grade": grade,
                "detections": dets[:10]
            })
        except Exception as e:
            anomaly_results.append({"filename": file.filename, "error": str(e)})
    
    return {
        "sonar": {"total_images": len(sonar_results), "results": sonar_results},
        "anomaly": {"total_images": len(anomaly_results), "results": anomaly_results},
        "combined_summary": {
            "total_images": len(sonar_results) + len(anomaly_results),
            "total_detections": sum(r.get("total_detections",0) for r in sonar_results + anomaly_results)
        }
    }