from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
import io, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

router = APIRouter(prefix="/api/innovation", tags=["Innovation"])

class ABSReportRequest(BaseModel):
    vessel_name: str = "MV Pacific Explorer"
    vessel_imo: str = "IMO 9876543"
    inspector: str = "NautiCAI Automated System"
    detections: List[dict] = []

class BiofoulingRequest(BaseModel):
    vessel_name: str = "MV Pacific Explorer"
    vessel_imo: str = "IMO 9876543"
    vessel_type: str = "Container Ship"
    dwt_tonnes: int = 50000
    route_km: int = 15000
    fuel_type: str = "HFO"
    biofouling_coverage_percent: float = 50.0
    biofouling_severity: str = "Medium"

class BlockchainRequest(BaseModel):
    vessel_name: str
    vessel_imo: str
    inspector: str
    location: str
    detections: List[dict] = []

class EnvironmentalRiskRequest(BaseModel):
    vessel_name: str = "MV Pacific Explorer"
    vessel_imo: str = "IMO 9876543"
    lat: float = 1.2
    lon: float = 103.8
    location_name: str = "Singapore Strait"

class CorrosionVelocityRequest(BaseModel):
    asset_ids: List[str] = ["Pipeline-SG-001", "Pipeline-SG-002", "Hull-FR-001"]

class AcousticRequest(BaseModel):
    signal_type: str = "auto"

class MarineGrowthRequest(BaseModel):
    vessel_name: str = "MV Pacific Explorer"
    vessel_imo: str = "IMO 9876543"

class AnnotationRequest(BaseModel):
    frame_id: str
    defect_class: str
    severity: str
    coverage: float
    notes: str
    confidence: str
    agree_with_ai: bool
    annotator: str = "Expert"

_blockchain_instance = None

def get_blockchain():
    global _blockchain_instance
    if _blockchain_instance is None:
        from blockchain_audit import InspectionBlockchain
        _blockchain_instance = InspectionBlockchain()
    return _blockchain_instance

@router.post("/abs-dnv-report")
async def generate_abs_dnv_report(req: ABSReportRequest):
    try:
        from abs_report_generator import generate_abs_report
        output_path = tempfile.mktemp(suffix=".pdf")
        if not req.detections:
            req.detections = [
                {'class': 'Leakage', 'location': 'Frame 45, Port Side', 'confidence': 0.87, 'severity': 'Critical', 'action': 'Immediate repair required'},
                {'class': 'Corrosion', 'location': 'Frame 12, Starboard', 'confidence': 0.76, 'severity': 'Moderate', 'action': 'Monitor and schedule repair'},
            ]
        generate_abs_report(vessel_name=req.vessel_name, vessel_imo=req.vessel_imo,
            inspector=req.inspector, detections=req.detections, output_path=output_path)
        with open(output_path, 'rb') as f:
            pdf_bytes = f.read()
        return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="ABS_DNV_Report.pdf"'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/biofouling-co2")
async def biofouling_co2_report(req: BiofoulingRequest):
    try:
        from biofouling_co2_calculator import calculate_biofouling_impact
        output_path = tempfile.mktemp(suffix=".pdf")
        calculate_biofouling_impact(vessel_name=req.vessel_name, vessel_imo=req.vessel_imo,
            vessel_type=req.vessel_type, dwt_tonnes=req.dwt_tonnes, route_km=req.route_km,
            fuel_type=req.fuel_type, biofouling_coverage_percent=req.biofouling_coverage_percent,
            biofouling_severity=req.biofouling_severity, output_path=output_path)
        with open(output_path, 'rb') as f:
            pdf_bytes = f.read()
        return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="Biofouling_CO2_Report.pdf"'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/blockchain/record")
async def add_blockchain_record(req: BlockchainRequest):
    try:
        blockchain = get_blockchain()
        block = blockchain.add_inspection_record(vessel_name=req.vessel_name,
            vessel_imo=req.vessel_imo, inspector=req.inspector,
            location=req.location, detections=req.detections)
        is_valid, msg = blockchain.verify_chain()
        return {"block_index": block.index, "block_hash": block.hash,
            "chain_valid": is_valid, "chain_length": len(blockchain.chain)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/blockchain/verify")
async def verify_blockchain():
    try:
        blockchain = get_blockchain()
        is_valid, msg = blockchain.verify_chain()
        return {"is_valid": is_valid, "message": msg, "chain_length": len(blockchain.chain)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/environmental-risk")
async def environmental_risk(req: EnvironmentalRiskRequest):
    try:
        from environmental_risk_scoring import get_ocean_data, calculate_corrosion_risk, calculate_biofouling_risk, get_risk_level
        ocean_data = get_ocean_data(req.lat, req.lon)
        corrosion_score = calculate_corrosion_risk(ocean_data)
        biofouling_score = calculate_biofouling_risk(ocean_data)
        overall_score = int((corrosion_score + biofouling_score) / 2)
        corrosion_level, _ = get_risk_level(corrosion_score)
        biofouling_level, _ = get_risk_level(biofouling_score)
        overall_level, _ = get_risk_level(overall_score)
        return {"vessel_name": req.vessel_name, "location": req.location_name,
            "ocean_data": ocean_data, "risk_scores": {
                "corrosion": {"score": corrosion_score, "level": corrosion_level},
                "biofouling": {"score": biofouling_score, "level": biofouling_level},
                "overall": {"score": overall_score, "level": overall_level}}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/corrosion-velocity")
async def corrosion_velocity(req: CorrosionVelocityRequest):
    try:
        from corrosion_velocity_model import generate_inspection_history, predict_failure
        results = []
        for asset_id in req.asset_ids:
            history = generate_inspection_history(asset_id)
            _, _, _, _, days_remaining, months_remaining = predict_failure(history)
            growth_rate = (history[-1]['corrosion_mm'] - history[0]['corrosion_mm']) / (len(history) * 6)
            if months_remaining < 6: risk = 'CRITICAL'
            elif months_remaining < 12: risk = 'HIGH'
            elif months_remaining < 24: risk = 'MODERATE'
            else: risk = 'LOW'
            results.append({"asset_id": asset_id,
                "current_corrosion_mm": history[-1]['corrosion_mm'],
                "growth_rate_mm_per_month": round(growth_rate, 2),
                "months_to_failure": months_remaining, "risk_level": risk})
        return {"assets": results, "total_assets": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/acoustic/classify")
async def acoustic_classify(req: AcousticRequest):
    try:
        from acoustic_emission_ai import generate_acoustic_signal, extract_features, generate_dataset
        from sklearn.preprocessing import StandardScaler
        from sklearn.ensemble import RandomForestClassifier
        X, y = generate_dataset(500)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_scaled, y)
        event = req.signal_type if req.signal_type != "auto" else "crack_initiation"
        signal = generate_acoustic_signal(event)
        import numpy as np
        features = extract_features(signal).reshape(1, -1)
        pred = model.predict(scaler.transform(features))[0]
        prob = model.predict_proba(scaler.transform(features))[0]
        labels = ['Normal', 'Crack Initiation', 'Crack Propagation', 'Leak']
        return {"predicted_event": labels[pred], "confidence": round(float(max(prob)), 3),
            "alert_level": "CRITICAL" if pred == 3 else "HIGH" if pred == 2 else "MODERATE" if pred == 1 else "NORMAL"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/marine-growth/classify")
async def marine_growth_classify(req: MarineGrowthRequest):
    try:
        from marine_growth_classifier import simulate_hull_scan
        detections = simulate_hull_scan()
        total_damage = sum(d['monthly_damage'] for d in detections)
        return {"vessel_name": req.vessel_name, "hull_zones": detections,
            "total_monthly_damage_mm": round(total_damage, 3),
            "cleaning_urgency": "IMMEDIATE" if total_damage > 2.0 else "WITHIN_30_DAYS"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/expert/annotate")
async def submit_annotation(req: AnnotationRequest):
    try:
        import datetime, uuid
        annotation_id = f"ANN-{uuid.uuid4().hex[:8].upper()}"
        reward = 2.50 if not req.agree_with_ai else 1.00
        return {"annotation_id": annotation_id, "status": "accepted",
            "reward_usd": reward, "timestamp": datetime.datetime.now().isoformat(),
            "message": f"Annotation {annotation_id} recorded. ${reward:.2f} added to your account."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary")
async def innovation_summary():
    return {"features": [
        {"id": "#03", "name": "Acoustic Emission AI", "endpoint": "/api/innovation/acoustic/classify"},
        {"id": "#06", "name": "Corrosion Velocity Model", "endpoint": "/api/innovation/corrosion-velocity"},
        {"id": "#07", "name": "Environmental Risk Scoring", "endpoint": "/api/innovation/environmental-risk"},
        {"id": "#09", "name": "ABS/DNV Report Generator", "endpoint": "/api/innovation/abs-dnv-report"},
        {"id": "#10", "name": "Biofouling CO2 Calculator", "endpoint": "/api/innovation/biofouling-co2"},
        {"id": "#13", "name": "Blockchain Audit Trail", "endpoint": "/api/innovation/blockchain/record"},
        {"id": "#15", "name": "Marine Growth Classifier", "endpoint": "/api/innovation/marine-growth/classify"},
        {"id": "#16", "name": "Expert Crowdsourcing", "endpoint": "/api/innovation/expert/annotate"},
    ], "total_features": 8, "platform": "NautiCAI Innovation Suite v1.0"}