"""
Sonar Analysis Insights Generator
Generates human-readable analysis summaries from detection results
"""

def generate_insights(results):
    """
    Generate analysis insights from sonar detection results.
    
    Args:
        results: List of detection result dicts with keys:
                 - total_detections
                 - critical_count, high_count, medium_count, low_count
                 - detections (list of individual detection dicts)
                 - model_info
    
    Returns:
        Dict with insight categories
    """
    if not results:
        return {"status": "No results available"}
    
    # Aggregate across all images
    total_dets = sum(r.get("total_detections", 0) for r in results)
    total_critical = sum(r.get("critical_count", 0) for r in results)
    total_high = sum(r.get("high_count", 0) for r in results)
    total_medium = sum(r.get("medium_count", 0) for r in results)
    total_low = sum(r.get("low_count", 0) for r in results)
    
    # Collect all detections
    all_dets = []
    for r in results:
        all_dets.extend(r.get("detections", []))
    
    # Calculate metrics
    avg_conf = sum(d.get("confidence", 0) for d in all_dets) / max(len(all_dets), 1)
    low_conf_count = sum(1 for d in all_dets if d.get("confidence", 1.0) < 0.60)
    
    # Class distribution
    class_counts = {}
    for d in all_dets:
        cls = d.get("class_name", "Unknown")
        class_counts[cls] = class_counts.get(cls, 0) + 1
    
    insights = {
        "pipeline_health": _get_pipeline_health(total_critical, total_high, total_dets, avg_conf),
        "defect_distribution": _get_defect_distribution(class_counts, total_dets),
        "operational_impact": _get_operational_impact(total_critical, total_high),
        "confidence_analysis": _get_confidence_analysis(avg_conf, low_conf_count, total_dets),
        "recommendations": _get_recommendations(total_critical, total_high, low_conf_count),
    }
    
    return insights


def _get_pipeline_health(critical, high, total, avg_conf):
    """Assess overall pipeline structural health"""
    if total == 0:
        return {
            "status": "HEALTHY",
            "message": "No anomalies detected — pipeline appears structurally sound",
            "confidence": "High" if avg_conf > 0.80 else "Moderate"
        }
    
    if critical > 0:
        status = "CRITICAL"
        message = f"{critical} critical issue{'s' if critical > 1 else ''} detected — immediate action required"
    elif high > 2:
        status = "DEGRADED"
        message = f"{high} high-severity defects detected — inspection recommended within 7 days"
    elif high > 0:
        status = "ATTENTION NEEDED"
        message = f"{high} high-severity issue{'s' if high > 1 else ''} — monitor closely"
    else:
        status = "MINOR ISSUES"
        message = f"{total} minor defect{'s' if total > 1 else ''} detected — routine maintenance"
    
    return {
        "status": status,
        "message": message,
        "confidence": "High" if avg_conf > 0.75 else "Moderate" if avg_conf > 0.55 else "Low"
    }


def _get_defect_distribution(class_counts, total):
    """Analyze defect type distribution"""
    if not class_counts:
        return {"message": "No defects detected"}
    
    # Sort by count
    sorted_classes = sorted(class_counts.items(), key=lambda x: x[1], reverse=True)
    top_class, top_count = sorted_classes[0]
    
    percentage = (top_count / total * 100) if total > 0 else 0
    
    if percentage > 50:
        dominant = f"{top_class} is the dominant defect type ({percentage:.0f}% of all detections)"
    else:
        dominant = "Defects are distributed across multiple classes"
    
    return {
        "dominant_class": top_class,
        "dominant_percentage": round(percentage, 1),
        "message": dominant,
        "class_breakdown": dict(sorted_classes[:5])  # Top 5 classes
    }


def _get_operational_impact(critical, high):
    """Assess operational impact and urgency"""
    if critical > 0:
        urgency = "IMMEDIATE"
        impact = f"Operation should be halted — {critical} critical structural issue{'s' if critical > 1 else ''} require immediate repair"
        timeline = "0-24 hours"
    elif high >= 3:
        urgency = "HIGH"
        impact = f"{high} high-severity defects detected — schedule inspection within 7 days"
        timeline = "7 days"
    elif high > 0:
        urgency = "MEDIUM"
        impact = f"{high} issue{'s' if high > 1 else ''} requiring attention — plan maintenance within 30 days"
        timeline = "30 days"
    else:
        urgency = "LOW"
        impact = "Routine monitoring and scheduled maintenance"
        timeline = "Next inspection cycle"
    
    return {
        "urgency": urgency,
        "impact": impact,
        "timeline": timeline
    }


def _get_confidence_analysis(avg_conf, low_conf_count, total):
    """Analyze detection confidence levels"""
    conf_percentage = avg_conf * 100
    
    if avg_conf > 0.85:
        quality = "Excellent"
        message = f"High confidence detections ({conf_percentage:.1f}% average) — reliable results"
    elif avg_conf > 0.70:
        quality = "Good"
        message = f"Moderate confidence ({conf_percentage:.1f}% average) — generally reliable"
    else:
        quality = "Fair"
        message = f"Lower confidence ({conf_percentage:.1f}% average) — consider manual review"
    
    manual_review = ""
    if low_conf_count > 0:
        pct = (low_conf_count / total * 100) if total > 0 else 0
        manual_review = f"{low_conf_count} detection{'s' if low_conf_count > 1 else ''} ({pct:.0f}%) below 60% confidence — recommend manual verification"
    
    return {
        "quality": quality,
        "average_confidence": round(conf_percentage, 1),
        "message": message,
        "manual_review_needed": manual_review if low_conf_count > 0 else None
    }


def _get_recommendations(critical, high, low_conf_count):
    """Generate actionable recommendations"""
    recs = []
    
    if critical > 0:
        recs.append({
            "priority": "CRITICAL",
            "action": "Halt operations and dispatch ROV for detailed inspection",
            "timeline": "Immediate (0-24 hours)"
        })
        recs.append({
            "priority": "CRITICAL",
            "action": "Notify structural engineering team for emergency assessment",
            "timeline": "Immediate"
        })
    
    if high > 0:
        recs.append({
            "priority": "HIGH",
            "action": f"Schedule detailed inspection of {high} high-severity zone{'s' if high > 1 else ''}",
            "timeline": "Within 7 days"
        })
    
    if low_conf_count > 3:
        recs.append({
            "priority": "MEDIUM",
            "action": "Manual review recommended for low-confidence detections",
            "timeline": "Within 14 days"
        })
    
    if not recs:
        recs.append({
            "priority": "ROUTINE",
            "action": "Continue standard monitoring and maintenance schedule",
            "timeline": "Next inspection cycle"
        })
    
    return recs
