
# ═══════════════════════════════════════════════════════════════
# STEP 1: Add import at the top of sonar_routes.py
# ═══════════════════════════════════════════════════════════════

from detection_filter import DetectionValidator
import cv2
import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# STEP 2: Initialize validator (add after model loading)
# ═══════════════════════════════════════════════════════════════

# Load your YOLO model
model = YOLO('models/subpipe_best.pt')

# Initialize detection validator
validator = DetectionValidator()
logger.info("Detection validator initialized")

# ═══════════════════════════════════════════════════════════════
# STEP 3: Update your analyze endpoint
# ═══════════════════════════════════════════════════════════════

@router.post("/api/sonar/analyze")
async def analyze_sonar(file: UploadFile = File(...)):
    try:
        # Save uploaded file
        file_path = f"temp_{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())
        
        # Run YOLO inference
        results = model.predict(file_path, conf=0.25)[0]
        
        # Read image for validator
        image_array = cv2.imread(file_path)
        if image_array is None:
            return {"error": "Failed to read image"}
        
        # Extract raw detections
        raw_detections = []
        for box in results.boxes:
            # Get normalized coordinates (0-1)
            x1, y1, x2, y2 = box.xyxyn[0].tolist()
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            class_name = model.names[cls]
            
            raw_detections.append({
                'bbox': [x1, y1, x2, y2],
                'class': class_name,
                'confidence': conf
            })
        
        # ═══ FILTER FALSE POSITIVES HERE ═══
        valid_detections, rejected = validator.filter_detections(
            raw_detections, 
            image_array
        )
        
        # Log filtering results
        if rejected:
            logger.warning(f"🚫 Filtered {len(rejected)} false positives:")
            for r in rejected:
                logger.warning(
                    f"   • {r['class']} @ conf={r['confidence']:.2f} "
                    f"- Reason: {r['rejection_reason']}"
                )
        
        logger.info(f"✓ Valid detections: {len(valid_detections)}/{len(raw_detections)}")
        
        # Map confidence to severity for valid detections
        detections_with_severity = []
        for det in valid_detections:
            severity = calculate_severity(det['confidence'])
            
            detections_with_severity.append({
                'bbox': det['bbox'],
                'class': det['class'],
                'confidence': det['confidence'],
                'severity': det.get('severity', severity),  # Use override if present
                'warnings': det.get('warnings', [])
            })
        
        # Calculate risk score
        risk_score = calculate_risk_score(detections_with_severity)
        
        # Clean up temp file
        os.remove(file_path)
        
        return {
            'success': True,
            'detections': detections_with_severity,
            'total_found': len(detections_with_severity),
            'filtered_out': len(rejected),
            'risk_score': risk_score,
            'filtering_active': True
        }
    
    except Exception as e:
        logger.error(f"Error in sonar analysis: {str(e)}")
        return {"error": str(e)}


def calculate_severity(confidence: float) -> str:
    '''Convert confidence to severity (inverse relationship)'''
    if confidence < 0.4:
        return "critical"
    elif confidence < 0.6:
        return "high"
    elif confidence < 0.75:
        return "medium"
    else:
        return "low"


def calculate_risk_score(detections: list) -> int:
    '''Calculate overall risk score from detections'''
    if not detections:
        return 0
    
    severity_weights = {
        'critical': 4,
        'high': 3,
        'medium': 2,
        'low': 1
    }
    
    total_weight = sum(severity_weights.get(d['severity'], 1) for d in detections)
    max_possible = len(detections) * 4
    
    return int((total_weight / max_possible) * 100)
