"""
NautiCAI Detection Validation Filter
Filters out false positive detections before they reach the frontend
"""

import numpy as np
from typing import List, Dict, Tuple
import cv2

class DetectionValidator:
    """
    Post-processing filter to catch obvious false positives
    in underwater pipeline defect detection
    """
    
    def __init__(self):
        # Confidence thresholds per defect type
        self.min_confidence = {
            'cp_failure': 0.55,      # CP failures should be clearer
            'corrosion': 0.45,       # Corrosion can be subtle
            'scaling': 0.50,         # Scaling has distinct patterns
            'blockage': 0.60,        # Blockages should be obvious
            'default': 0.40          # General threshold
        }
        
        # Size constraints (normalized 0-1 relative to image)
        self.size_constraints = {
            'min_area': 0.002,       # Too small = likely noise
            'max_area': 0.85,        # Too large = likely wrong object
        }
        
        # Aspect ratio constraints (width/height)
        self.aspect_ratio_range = {
            'min': 0.3,              # Too thin = likely artifact
            'max': 5.0,              # Too wide = likely not defect
        }
    
    def validate_detection(
        self, 
        bbox: List[float],  # [x1, y1, x2, y2] normalized 0-1
        class_name: str,
        confidence: float,
        image_shape: Tuple[int, int, int],  # (H, W, C)
        image_patch: np.ndarray = None  # Optional: actual image crop
    ) -> Dict:
        """
        Validate a single detection and return filtering decision
        
        Returns:
            {
                'valid': bool,
                'reason': str,
                'adjusted_confidence': float,
                'severity_override': str (optional)
            }
        """
        result = {
            'valid': True,
            'reason': 'passed_all_checks',
            'adjusted_confidence': confidence,
            'warnings': []
        }
        
        # 1. Confidence threshold check
        threshold = self.min_confidence.get(
            class_name.lower().replace(' ', '_'), 
            self.min_confidence['default']
        )
        
        if confidence < threshold:
            result['valid'] = False
            result['reason'] = f'confidence_too_low (min: {threshold:.2f})'
            return result
        
        # 2. Bounding box geometry validation
        x1, y1, x2, y2 = bbox
        width = x2 - x1
        height = y2 - y1
        area = width * height
        
        # Check size
        if area < self.size_constraints['min_area']:
            result['valid'] = False
            result['reason'] = 'detection_too_small (likely noise)'
            return result
        
        if area > self.size_constraints['max_area']:
            result['valid'] = False
            result['reason'] = 'detection_too_large (likely not a defect)'
            return result
        
        # Check aspect ratio
        if height > 0:
            aspect_ratio = width / height
            if aspect_ratio < self.aspect_ratio_range['min']:
                result['warnings'].append('unusually_thin_detection')
            elif aspect_ratio > self.aspect_ratio_range['max']:
                result['warnings'].append('unusually_wide_detection')
        
        # 3. Visual feature checks (if image patch provided)
        if image_patch is not None:
            visual_checks = self._validate_visual_features(
                image_patch, class_name, confidence
            )
            result['warnings'].extend(visual_checks['warnings'])
            
            if not visual_checks['valid']:
                result['valid'] = False
                result['reason'] = visual_checks['reason']
                return result
        
        # 4. Severity adjustment based on warnings
        if len(result['warnings']) >= 2:
            # Multiple red flags = downgrade severity
            result['severity_override'] = 'low'
            result['adjusted_confidence'] = confidence * 0.7
        
        return result
    
    def _validate_visual_features(
        self, 
        image_patch: np.ndarray, 
        class_name: str, 
        confidence: float
    ) -> Dict:
        """
        Check visual characteristics to catch false positives
        """
        result = {'valid': True, 'reason': '', 'warnings': []}
        
        if image_patch.size == 0:
            return result
        
        # Convert to HSV for better color analysis
        try:
            hsv = cv2.cvtColor(image_patch, cv2.COLOR_RGB2HSV)
        except:
            return result
        
        # 1. Check for skin-tone colors (major false positive source)
        # Skin tones in underwater lighting: H:0-25 or 160-180, S:20-150
        h, s, v = cv2.split(hsv)
        skin_mask = (
            (((h < 25) | (h > 160)) & (s > 20) & (s < 150)) |
            ((h > 340) & (s > 20) & (s < 150))  # Red-shifted skin
        )
        skin_ratio = np.sum(skin_mask) / skin_mask.size
        
        if skin_ratio > 0.35:
            result['valid'] = False
            result['reason'] = 'skin_tone_detected (likely human/ROV equipment)'
            return result
        
        # 2. Check for smooth/uniform textures (hands, gloves, plastic)
        gray = cv2.cvtColor(image_patch, cv2.COLOR_RGB2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        if laplacian_var < 50:  # Very smooth = not typical defect
            result['warnings'].append('smooth_texture (defects usually rough)')
        
        # 3. Check for metallic/pipeline characteristics
        # Underwater pipelines typically have greenish or brownish hues
        mean_hue = np.mean(h)
        
        # Pipeline defects should appear on pipeline-colored surfaces
        # H: 40-90 (green), 10-30 (brown/rust)
        is_pipeline_color = (40 <= mean_hue <= 90) or (10 <= mean_hue <= 30)
        
        if not is_pipeline_color and confidence < 0.65:
            result['warnings'].append('non_pipeline_color')
        
        # 4. Edge density check (artifacts often have clean edges)
        edges = cv2.Canny(gray, 50, 150)
        edge_ratio = np.sum(edges > 0) / edges.size
        
        if edge_ratio > 0.4:  # Too many edges = possibly structured object
            result['warnings'].append('high_edge_density')
        
        return result
    
    def filter_detections(
        self, 
        detections: List[Dict],
        image: np.ndarray
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Filter a batch of detections
        
        Args:
            detections: List of detection dicts with keys:
                - bbox: [x1, y1, x2, y2] normalized
                - class: str
                - confidence: float
            image: Full sonar image (H, W, C)
        
        Returns:
            (valid_detections, rejected_detections)
        """
        valid = []
        rejected = []
        
        h, w = image.shape[:2]
        
        for det in detections:
            # Extract image patch for visual validation
            x1, y1, x2, y2 = det['bbox']
            x1_px = int(x1 * w)
            y1_px = int(y1 * h)
            x2_px = int(x2 * w)
            y2_px = int(y2 * h)
            
            # Ensure valid bounds
            x1_px = max(0, x1_px)
            y1_px = max(0, y1_px)
            x2_px = min(w, x2_px)
            y2_px = min(h, y2_px)
            
            if x2_px > x1_px and y2_px > y1_px:
                patch = image[y1_px:y2_px, x1_px:x2_px]
            else:
                patch = None
            
            # Validate
            validation = self.validate_detection(
                bbox=det['bbox'],
                class_name=det['class'],
                confidence=det['confidence'],
                image_shape=image.shape,
                image_patch=patch
            )
            
            if validation['valid']:
                # Update detection with adjusted confidence/severity
                det['original_confidence'] = det['confidence']
                det['confidence'] = validation['adjusted_confidence']
                if 'severity_override' in validation:
                    det['severity'] = validation['severity_override']
                if validation['warnings']:
                    det['warnings'] = validation['warnings']
                valid.append(det)
            else:
                det['rejection_reason'] = validation['reason']
                rejected.append(det)
        
        return valid, rejected


# Integration example for FastAPI backend
def integrate_with_sonar_routes():
    """
    Example showing how to integrate into sonar_routes.py
    """
    code_example = '''
# In sonar_routes.py, after YOLO inference:

from detection_filter import DetectionValidator

validator = DetectionValidator()

# After running model.predict() and extracting detections:
raw_detections = [
    {
        'bbox': [x1, y1, x2, y2],  # normalized coordinates
        'class': class_name,
        'confidence': conf
    }
    for x1, y1, x2, y2, conf, cls in results
]

# Filter out false positives
valid_detections, rejected = validator.filter_detections(
    raw_detections, 
    original_image
)

# Log rejected detections for analysis
if rejected:
    logger.info(f"Filtered {len(rejected)} false positives")
    for r in rejected:
        logger.debug(f"Rejected {r['class']} - {r['rejection_reason']}")

# Use valid_detections for response
return valid_detections
    '''
    return code_example


if __name__ == "__main__":
    print("Detection Validator initialized")
    print(integrate_with_sonar_routes())
