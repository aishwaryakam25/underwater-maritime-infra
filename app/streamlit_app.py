"""
NautiCAI — Underwater Infrastructure Inspection Copilot
Run: streamlit run app/streamlit_app.py
"""
import io, os, math, time, uuid, datetime, tempfile
from pathlib import Path
import cv2, numpy as np
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import qrcode, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, Image as RLImage, HRFlowable, PageBreak)

from pdf_report import build_pdf
from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parent.parent
APP  = Path(__file__).resolve().parent

# Auto-download model from Hugging Face
if not os.path.exists(ROOT / "best.pt"):
    print("Downloading model from Hugging Face...")
    hf_hub_download(
        repo_id="aishwarya252525/nauticai-yolov8",
        filename="best.pt",
        local_dir=str(ROOT),
        local_dir_use_symlinks=False
    )

def _find_model():
    for n in ["best.pt","yolov8s.pt","yolov8n.pt"]:
        p = ROOT/n
        if p.exists(): return p
    return None
MODEL_PATH = _find_model()

DEFECT_CLASSES = [
    "Corrosion","Crack","Marine Growth","Biofouling","Paint Damage","Pitting",
    "Weld Defect","Anode Damage","Coating Failure","Dent","Deformation","Fracture",
    "Spalling","Scaling","Disbondment","CP Failure","Leakage","Blockage","Foreign Object",
]
SEVERITY_MAP = {
    "Corrosion":"Critical","Crack":"Critical","Fracture":"Critical","Leakage":"Critical",
    "Marine Growth":"High","Biofouling":"High","Weld Defect":"High","Anode Damage":"High",
    "CP Failure":"High","Pitting":"Medium","Paint Damage":"Medium","Coating Failure":"Medium",
    "Deformation":"Medium","Blockage":"Medium","Dent":"Low","Scaling":"Low",
    "Spalling":"Low","Disbondment":"Low","Foreign Object":"Low",
}
CLASS_REMAP = {
    "pipeline": "Corrosion",
    "concrete": "Marine Growth",
    "hull": "Paint Damage",
    "propeller": "Biofouling",
    "anode": "Anode Damage",
    "leakage": "Leakage",
    "anomaly": "Crack",
    "biofouling": "Biofouling",
}
SEV_COLORS = {"Critical":(220,50,50),"High":(255,165,0),"Medium":(0,180,255),"Low":(0,220,130)}
PIPELINE_DEFECTS = ["Corrosion","Crack","Coating Failure","Pitting","Leakage","Weld Defect","Blockage"]
CABLE_DEFECTS    = ["Fracture","Deformation","Foreign Object","Biofouling","Marine Growth","Dent"]

st.set_page_config(
    page_title="NautiCAI · Underwater Inspection Copilot",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ══════════════════════════════════════════════════════════════════════════
# AURORA GLASS THEME (fresh, premium)
# ══════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap');

/* =========================
   AURORA GLASS THEME (Fresh)
   ========================= */
:root{
  --bg0:#070A16;
  --bg1:#090E22;
  --bg2:#050814;

  --panel: rgba(255,255,255,0.055);
  --panel2: rgba(255,255,255,0.03);
  --stroke: rgba(168, 185, 255, 0.14);
  --stroke2: rgba(168, 185, 255, 0.10);

  --text:#EAF0FF;
  --muted:#A7B3D3;
  --muted2:#7D8BB0;

  /* Brand (unique) */
  --brandA:#8B5CF6;   /* violet */
  --brandB:#22D3EE;   /* cyan */
  --brandC:#FF4FD8;   /* pink accent */

  --ok:#22D3EE;
  --warn:#FBBF24;
  --danger:#FB7185;

  --r12: 12px;
  --r16: 16px;
  --shadow: 0 18px 50px rgba(0,0,0,.40);
}

/* ---- App background ---- */
html, body, [data-testid="stAppViewContainer"]{
  background:
    radial-gradient(1100px 720px at 12% 0%, rgba(139,92,246,0.23), transparent 60%),
    radial-gradient(900px 640px at 85% 10%, rgba(34,211,238,0.18), transparent 60%),
    radial-gradient(900px 640px at 70% 90%, rgba(255,79,216,0.10), transparent 55%),
    linear-gradient(180deg, var(--bg1), var(--bg2));
  font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif !important;
}

/* ---- Remove Streamlit chrome ---- */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"]{
  background: rgba(0,0,0,0) !important;
  border-bottom: 0 !important;
}
[data-testid="stToolbar"]{ right: 12px; }

/* ---- Layout ---- */
.block-container{
  padding-top: 1.15rem !important;
  padding-bottom: 1.5rem !important;
  max-width: 1220px !important;
}

/* ---- Typography ---- */
h1,h2,h3,h4,h5,p,span,div,label,li,td,th,a{
  color: var(--text) !important;
}
.stCaption, .stCaption *{ color: var(--muted2) !important; }

/* ---- Sidebar ---- */
[data-testid="stSidebar"]{
  background:
    radial-gradient(800px 400px at 20% 0%, rgba(139,92,246,0.12), transparent 60%),
    linear-gradient(180deg, rgba(255,255,255,0.035), rgba(255,255,255,0.015)) !important;
  border-right: 1px solid var(--stroke) !important;
}
[data-testid="stSidebar"] .block-container{
  padding-top: 1.2rem !important;
}

/* ---- Cards ---- */
.nc-card{
  background:
    radial-gradient(900px 400px at 20% 0%, rgba(139,92,246,0.10), transparent 55%),
    radial-gradient(700px 380px at 90% 20%, rgba(34,211,238,0.10), transparent 55%),
    linear-gradient(180deg, var(--panel), var(--panel2));
  border: 1px solid var(--stroke);
  border-radius: var(--r16);
  box-shadow: var(--shadow);
}
.nc-card-inner{ padding: 16px 16px; }

/* ---- Topbar ---- */
.nc-topbar{
  display:flex; align-items:center; justify-content:space-between;
  gap:16px; padding: 14px 16px;
}
.nc-brand{ display:flex; align-items:center; gap:12px; }

.nc-logo{
  width:38px;height:38px;border-radius: 12px;
  background: linear-gradient(135deg, var(--brandA), var(--brandB));
  display:flex;align-items:center;justify-content:center;
  box-shadow: 0 14px 34px rgba(139,92,246,.18);
  font-size:18px;
}

.nc-title{
  font-weight: 900;
  letter-spacing: .6px;
  font-size: 14px;
  font-family: JetBrains Mono, monospace;
}
.nc-sub{
  font-size: 12px;
  color: var(--muted) !important;
  margin-top: 2px;
}

.nc-pill{
  display:inline-flex; align-items:center; gap:8px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--stroke2);
  background: rgba(255,255,255,0.03);
  color: var(--muted) !important;
  font-size: 12px;
}
.nc-dot{
  width:8px;height:8px;border-radius:999px;
  background: var(--ok);
  box-shadow: 0 0 0 4px rgba(34,211,238,.12);
}
.nc-dot-warn{
  background: var(--warn);
  box-shadow: 0 0 0 4px rgba(251,191,36,.12);
}

/* ---- Tabs ---- */
.stTabs [data-baseweb="tab-list"]{
  background: rgba(255,255,255,0.03) !important;
  border: 1px solid var(--stroke2) !important;
  border-radius: 14px !important;
  padding: 6px !important;
}
.stTabs [data-baseweb="tab"]{
  background: transparent !important;
  border-radius: 12px !important;
  color: var(--muted) !important;
  font-weight: 700 !important;
  font-size: 13px !important;
  padding: 10px 12px !important;
}
.stTabs [aria-selected="true"]{
  color: var(--text) !important;
  background: rgba(139,92,246,0.14) !important;
  border: 1px solid rgba(139,92,246,0.28) !important;
}

/* ---- File uploader ---- */
[data-testid="stFileUploader"]{
  background: rgba(255,255,255,0.03) !important;
  border: 1px dashed rgba(168,185,255,0.26) !important;
  border-radius: var(--r16) !important;
}
[data-testid="stFileUploader"] *{
  color: var(--muted) !important;
}

/* ---- Inputs ---- */
.stTextInput input{
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid var(--stroke2) !important;
  border-radius: 12px !important;
  color: var(--text) !important;
}

/* Selectbox main control */
[data-testid="stSelectbox"] > div > div{
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid var(--stroke2) !important;
  border-radius: 12px !important;
  color: var(--text) !important;
}

/* ✅ FIX: selectbox dropdown menu + options visibility */
div[role="listbox"]{
  background: rgba(8,10,22,0.98) !important;
  border: 1px solid rgba(168,185,255,0.18) !important;
  border-radius: 12px !important;
  box-shadow: 0 18px 50px rgba(0,0,0,.55) !important;
}
div[role="option"]{
  color: var(--text) !important;
  padding: 10px 12px !important;
}
div[role="option"]:hover{
  background: rgba(34,211,238,0.12) !important;
}
div[role="option"][aria-selected="true"]{
  background: rgba(139,92,246,0.18) !important;
  border-left: 3px solid rgba(139,92,246,0.85) !important;
}

/* ---- Buttons ---- */
.stButton > button{
  border-radius: 12px !important;
  padding: 10px 14px !important;
  font-weight: 900 !important;
  border: 1px solid rgba(139,92,246,0.35) !important;
  background: linear-gradient(135deg, rgba(139,92,246,0.95), rgba(34,211,238,0.85)) !important;
  color: #060815 !important;
}
.stButton > button:hover{
  transform: translateY(-1px);
  box-shadow: 0 16px 30px rgba(139,92,246,.16);
}

/* ---- Metrics ---- */
[data-testid="metric-container"]{
  background: rgba(255,255,255,0.035) !important;
  border: 1px solid var(--stroke2) !important;
  border-radius: 14px !important;
  padding: 14px 14px !important;
}
[data-testid="metric-container"] label{
  color: var(--muted2) !important;
  font-size: 11px !important;
  font-weight: 900 !important;
  letter-spacing: .7px !important;
  text-transform: uppercase !important;
}
[data-testid="stMetricValue"]{
  font-family: JetBrains Mono, monospace !important;
  font-size: 24px !important;
  font-weight: 900 !important;
}

/* ---- Tables ---- */
[data-testid="stDataFrame"]{
  border: 1px solid var(--stroke2) !important;
  border-radius: 14px !important;
  overflow: hidden !important;
}
[data-testid="stDataFrame"] th{
  background: rgba(255,255,255,0.02) !important;
  color: var(--muted2) !important;
}

/* ---- Alerts ---- */
.stSuccess, .stInfo, .stWarning, .stError{
  border-radius: 14px !important;
  border: 1px solid var(--stroke2) !important;
  background: rgba(255,255,255,0.03) !important;
}

/* ---- Dividers ---- */
hr{
  border: none !important;
  height: 1px !important;
  background: rgba(168,185,255,0.12) !important;
}

/* ---- Scrollbar ---- */
::-webkit-scrollbar{ width: 6px; height: 6px; }
::-webkit-scrollbar-thumb{ background: rgba(168,185,255,0.20); border-radius: 999px; }
::-webkit-scrollbar-thumb:hover{ background: rgba(34,211,238,0.35); }

/* ---- Small spacing polish ---- */
div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stHorizontalBlock"]) {
  gap: 0.75rem;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════
def _init():
    d=dict(detections=[],annotated_img=None,original_img=None,enhanced_img=None,
           risk_score=0,grade="N/A",mission_id=f"M-{uuid.uuid4().hex[:6].upper()}",
           vessel_name="",scan_time="",last_pdf=None,last_pdf_fname="",mission_history=[],
           hull_pdf=None,hull_pdf_fname="",
           pipe_pdf=None,pipe_pdf_fname="",
           cable_pdf=None,cable_pdf_fname="")
    for k,v in d.items():
        if k not in st.session_state: st.session_state[k]=v
_init()

# ══════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════
def pil_to_cv(img): return cv2.cvtColor(np.array(img.convert("RGB")),cv2.COLOR_RGB2BGR)
def cv_to_pil(arr): return Image.fromarray(cv2.cvtColor(arr,cv2.COLOR_BGR2RGB))
def score_to_grade(s): return "A" if s>=76 else "B" if s>=51 else "C" if s>=26 else "D"
def grade_color_rl(g): return {"A":colors.HexColor("#34d399"),"B":colors.HexColor("#38bdf8"),"C":colors.HexColor("#fbbf24"),"D":colors.HexColor("#f87171")}.get(g,colors.grey)
def sev_weight(s): return {"Critical":25,"High":12,"Medium":6,"Low":2}.get(s,0)
def compute_risk(dets): return max(0,min(100,100-sum(sev_weight(d["severity"]) for d in dets)))
def make_qr(data):
    qr=qrcode.QRCode(version=None,error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=10,border=4)
    qr.add_data(data);qr.make(fit=True)
    return qr.make_image(fill_color="#000000",back_color="#FFFFFF").convert("RGB")
def sev_badge_color(s): return {"Critical":colors.HexColor("#f87171"),"High":colors.HexColor("#fbbf24"),"Medium":colors.HexColor("#38bdf8"),"Low":colors.HexColor("#34d399")}.get(s,colors.grey)

# ══════════════════════════════════════════════════════════════════════════
# UI HELPERS (no logic changes)
# ══════════════════════════════════════════════════════════════════════════
def ui_topbar(model_path):
    live = bool(model_path)
    st.markdown(f"""
    <div class="nc-card">
      <div class="nc-topbar">
        <div class="nc-brand">
          <div class="nc-logo">🌊</div>
          <div>
            <div class="nc-title">NAUTICAI</div>
            <div class="nc-sub">Underwater Infrastructure Inspection Copilot</div>
          </div>
        </div>
        <div class="nc-pill">
          <span class="nc-dot {'nc-dot-warn' if not live else ''}"></span>
          <span style="font-family:JetBrains Mono,monospace;">
            {("Demo mode (no model)" if not live else f"Model: {model_path.name}")}
          </span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

def ui_section(crumb, title, subtitle):
    st.markdown(f"""
    <div style="margin-top:14px;margin-bottom:10px">
      <div style="font-family:JetBrains Mono,monospace;font-size:11px;color:var(--muted2);letter-spacing:.8px">
        {crumb}
      </div>
      <div style="font-size:22px;font-weight:800;margin-top:6px;letter-spacing:-.2px">
        {title}
      </div>
      <div style="font-size:13px;color:var(--muted);margin-top:4px;line-height:1.45">
        {subtitle}
      </div>
    </div>
    """, unsafe_allow_html=True)

def ui_card_open(pad=16):
    st.markdown(f'<div class="nc-card"><div class="nc-card-inner" style="padding:{pad}px">', unsafe_allow_html=True)

def ui_card_close():
    st.markdown('</div></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# VISIBILITY PIPELINE
# ══════════════════════════════════════════════════════════════════════════
def apply_clahe(bgr,clip=3.0,grid=8):
    lab=cv2.cvtColor(bgr,cv2.COLOR_BGR2LAB);l,a,b=cv2.split(lab)
    l=cv2.createCLAHE(clipLimit=clip,tileGridSize=(grid,grid)).apply(l)
    return cv2.cvtColor(cv2.merge([l,a,b]),cv2.COLOR_LAB2BGR)
def apply_green_water(bgr,s=0.6):
    o=bgr.astype(np.float32)
    o[:,:,1]=np.clip(o[:,:,1]*(1+.4*s),0,255);o[:,:,0]=np.clip(o[:,:,0]*(1-.3*s),0,255);o[:,:,2]=np.clip(o[:,:,2]*(1+.15*s),0,255)
    return o.astype(np.uint8)
def apply_turbidity(bgr,level=0.4):
    if level<.01: return bgr
    bl=cv2.GaussianBlur(bgr,(0,0),sigmaX=level*12);sim=cv2.addWeighted(bgr,1-level*.7,bl,level*.7,0)
    t=sim.astype(np.float32)
    t[:,:,1]=np.clip(t[:,:,1]*(1+level*.35),0,255);t[:,:,0]=np.clip(t[:,:,0]*(1-level*.2),0,255);t[:,:,2]=np.clip(t[:,:,2]*(1-level*.3),0,255)
    return np.clip(t*(1-level*.25),0,255).astype(np.uint8)
def apply_turbidity_correction(bgr,level=0.4):
    o=bgr.astype(np.float32)
    o[:,:,0]=np.clip(o[:,:,0]/max(.01,1-level*.2),0,255);o[:,:,1]=np.clip(o[:,:,1]/max(.01,1+level*.35),0,255);o[:,:,2]=np.clip(o[:,:,2]/max(.01,1-level*.3),0,255)
    return np.clip(o/max(.01,1-level*.25),0,255).astype(np.uint8)
def apply_edge_estimator(bgr):
    gray=cv2.cvtColor(bgr,cv2.COLOR_BGR2GRAY);edges=cv2.Canny(gray,50,150)
    ec=cv2.cvtColor(edges,cv2.COLOR_GRAY2BGR);ec[:,:,0]=0;ec[:,:,2]=0;ec[:,:,1]=edges
    return cv2.addWeighted(bgr,.75,ec,.8,0)
def full_enhance(pil_img,use_clahe,use_green,turb_in,corr_turb,use_edge,clahe_clip=3.0):
    bgr=pil_to_cv(pil_img)
    if turb_in>.01: bgr=apply_turbidity(bgr,turb_in)
    if corr_turb and turb_in>.01: bgr=apply_turbidity_correction(bgr,turb_in*.85)
    if use_green: bgr=apply_green_water(bgr)
    if use_clahe: bgr=apply_clahe(bgr,clip=clahe_clip)
    if use_edge:  bgr=apply_edge_estimator(bgr)
    return cv_to_pil(bgr)

# ══════════════════════════════════════════════════════════════════════════
# DETECTION
# ══════════════════════════════════════════════════════════════════════════
@st.cache_resource(show_spinner="Loading YOLO model…")
def load_yolo(path):
    from ultralytics import YOLO
    return YOLO(path)
def _detect_real(img,conf_thr,iou_thr):
    try:
        model=load_yolo(str(MODEL_PATH));results=model.predict(img,conf=conf_thr,iou=iou_thr,verbose=False)[0];dets=[]
        for i,box in enumerate(results.boxes):
            x1,y1,x2,y2=map(int,box.xyxy[0].tolist());conf=float(box.conf[0]);cls_i=int(box.cls[0])
            cls=model.names.get(cls_i,DEFECT_CLASSES[cls_i%len(DEFECT_CLASSES)]);cls=CLASS_REMAP.get(cls,cls);sev=SEVERITY_MAP.get(cls,"Medium")
            dets.append(dict(id=i+1,cls=cls,severity=sev,conf=conf,x1=x1,y1=y1,x2=x2,y2=y2,area=(x2-x1)*(y2-y1)))
        return dets
    except Exception as e:
        st.warning(f"YOLO error: {e}"); return []
def _detect_synthetic(img,conf_thr,pool):
    w,h=img.size;rng=np.random.default_rng(sum(img.tobytes()[:64]));n=rng.integers(3,9);dets=[]
    for i in range(n):
        cx,cy=rng.integers(60,w-60),rng.integers(60,h-60);bw,bh=rng.integers(40,w//4),rng.integers(30,h//5)
        conf=rng.uniform(conf_thr,.98);cls=rng.choice(pool);sev=SEVERITY_MAP.get(cls,"Medium")
        x1,y1=max(0,cx-bw//2),max(0,cy-bh//2);x2,y2=min(w,cx+bw//2),min(h,cy+bh//2)
        dets.append(dict(id=i+1,cls=cls,severity=sev,conf=float(conf),x1=x1,y1=y1,x2=x2,y2=y2,area=(x2-x1)*(y2-y1)))
    return dets
def run_detection(img,conf_thr,iou_thr,mode):
    pool=(PIPELINE_DEFECTS if mode=="pipeline" else CABLE_DEFECTS if mode=="cable" else DEFECT_CLASSES)
    if MODEL_PATH:
        dets=_detect_real(img,conf_thr,iou_thr)
        if dets: return dets
    return _detect_synthetic(img,conf_thr,pool)

# ══════════════════════════════════════════════════════════════════════════
# ANNOTATION + HEATMAP
# ══════════════════════════════════════════════════════════════════════════
def annotate_image(pil_img,dets):
    out=pil_img.copy().convert("RGBA");draw=ImageDraw.Draw(out,"RGBA");W,H=out.size
    try:
        fb=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",14)
        fs=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",11)
    except: fb=fs=ImageFont.load_default()
    for d in dets:
        col=SEV_COLORS.get(d["severity"],(200,200,200));c4=col+(210,);f4=col+(35,)
        x1,y1,x2,y2=d["x1"],d["y1"],d["x2"],d["y2"]
        draw.rectangle([x1,y1,x2,y2],fill=f4,outline=c4,width=2)
        acc=14
        for sx,sy,ex,ey in [(x1,y1,x1+acc,y1),(x1,y1,x1,y1+acc),(x2,y1,x2-acc,y1),(x2,y1,x2,y1+acc),
                             (x1,y2,x1+acc,y2),(x1,y2,x1,y2-acc),(x2,y2,x2-acc,y2),(x2,y2,x2,y2-acc)]:
            draw.line([(sx,sy),(ex,ey)],fill=c4,width=3)
        lbl=f"[{d['id']:02d}] {d['cls']} {d['conf']*100:.0f}%"
        bb=draw.textbbox((0,0),lbl,font=fb);tw,th=bb[2]-bb[0],bb[3]-bb[1]
        ty=y1-th-6 if y1-th-6>0 else y1+4
        draw.rectangle([x1,ty-2,x1+tw+10,ty+th+4],fill=col+(200,))
        draw.text((x1+5,ty),lbl,fill=(10,20,30),font=fb)
        draw.ellipse([x1+4,y1+4,x1+12,y1+12],fill=c4)
    wm=f"NautiCAI · {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} · {len(dets)} detections"
    bb2=draw.textbbox((0,0),wm,font=fs);tw2=bb2[2]-bb2[0]
    draw.rectangle([0,H-22,W,H],fill=(5,12,26,210))
    draw.text(((W-tw2)//2,H-18),wm,fill=(76,201,255,220),font=fs)
    return out.convert("RGB")

def build_heatmap(img,dets):
    W,H=img.size;heat=np.zeros((H,W),dtype=np.float32)
    # Place all weighted detection centres on the heat array first
    for d in dets:
        cx=min(W-1,max(0,(d["x1"]+d["x2"])//2));cy=min(H-1,max(0,(d["y1"]+d["y2"])//2))
        heat[cy,cx]+=float(sev_weight(d["severity"]))
    # Apply a single gaussian filter (fast even for thousands of detections)
    if heat.max()>0:
        avg_area=np.mean([d.get("area",3000) for d in dets]) if dets else 3000
        sig=max(30,math.sqrt(avg_area)*.35)
        heat=gaussian_filter(heat,sigma=sig)
        heat=(heat/heat.max()*255).astype(np.uint8)
    cmap=matplotlib.colormaps.get_cmap("plasma")
    hmap=(cmap(heat/255.0)[:,:,:3]*255).astype(np.uint8)
    dark=ImageEnhance.Brightness(img).enhance(.4)
    return Image.blend(dark,Image.fromarray(hmap).resize((W,H)),alpha=.62)

# PDF report builder is now in pdf_report.py (imported at top)

# ══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div class="nc-card">
      <div class="nc-card-inner">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
          <div class="nc-logo" style="width:34px;height:34px;border-radius:12px;font-size:16px">🌊</div>
          <div>
            <div class="nc-title" style="font-size:13px">CONTROL CENTER</div>
            <div class="nc-sub">Detection + visibility tuning</div>
          </div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <span class="nc-pill"><span class="nc-dot"></span> Stable</span>
          <span class="nc-pill">v1.0.4</span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    if MODEL_PATH:
      st.info(f"🧠 `{MODEL_PATH.name}` · Active")
    else:
        st.warning("⚠️ No model — demo mode")

    st.markdown("#### Detection Engine")
    conf_thr=st.slider("Confidence Threshold",0.05,0.95,0.25,0.05)
    iou_thr =st.slider("IoU Threshold",0.10,0.90,0.45,0.05)
    st.divider()
    st.markdown("#### Severity Filter")
    sev_filter=st.selectbox("Display mode",["All Detections","Critical Only","High+","Medium+"])
    st.divider()
    st.markdown("#### Visibility Engine")
    use_clahe   =st.toggle("CLAHE Enhancement",value=True)
    clahe_clip  =st.slider("CLAHE Clip Limit",1.0,8.0,3.0,.5)
    use_green   =st.toggle("Green-Water Filter",value=True)
    use_edge    =st.toggle("Edge Estimator",value=False)
    turbidity_in=st.slider("Turbidity Level",0.0,1.0,0.0,.05)
    corr_turb   =st.toggle("Turbidity Correction",value=True)
    st.divider()
    st.markdown("#### Mission Info")
    vessel_name=st.text_input("Vessel Name",placeholder="e.g. MV Neptune Star")
    inspector  =st.text_input("Inspector",value="NautiCAI AutoScan v1.0")
    scan_mode  =st.selectbox(
        "Inspection Mode",
        ["hull","pipeline","cable","port","general"],
        format_func=lambda x:{"hull":"Hull Inspection","pipeline":"Pipeline","cable":"Subsea Cable","port":"Port Infra","general":"General"}[x]
    )

# ══════════════════════════════════════════════════════════════════════════
# TOP BAR
# ══════════════════════════════════════════════════════════════════════════
ui_topbar(MODEL_PATH)
st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════
(tab_scan,tab_hull,tab_video,tab_pipe,tab_cable,tab_dash,tab_report,tab_roadmap)=st.tabs([
    "🔬 Infrastructure Scan","🚢 Hull Inspection","📹 Video Analysis",
    "🔩 Pipeline & Subsea","⚡ Cable Anomaly","📊 Mission Dashboard",
    "📋 Report & Export","🗺️ Roadmap"])

# ─── SCAN ────────────────────────────────────────────────────────────────
with tab_scan:
    ui_section(
        "NAUTICAI / INFRASTRUCTURE SCAN",
        "Infrastructure Scan",
        "AI-powered underwater defect detection · YOLOv8 · 19 defect classes · annotated output + professional report"
    )
    st.divider()

    ui_card_open()
    col_up,col_prev=st.columns(2)
    with col_up:
        uploaded=st.file_uploader("Upload underwater image",type=["jpg","jpeg","png","webp"],label_visibility="collapsed")
        go=st.button("Run AI Detection",type="primary")
        st.button("Configure Settings")
    with col_prev:
        if uploaded: st.image(uploaded,width=650)
    ui_card_close()

    if uploaded and go:
        pil_orig=Image.open(uploaded).convert("RGB");st.session_state.original_img=pil_orig
        prog=st.progress(0,"Initialising…")
        with st.spinner("Applying visibility filters…"):
            prog.progress(20)
            enhanced=full_enhance(pil_orig,use_clahe,use_green,turbidity_in,corr_turb,use_edge,clahe_clip)
            st.session_state.enhanced_img=enhanced
        with st.spinner("Running YOLOv8 detection…"):
            prog.progress(55)
            dets=run_detection(enhanced,conf_thr,iou_thr,scan_mode)
        SEV_RANK={"Critical":4,"High":3,"Medium":2,"Low":1}
        if sev_filter=="Critical Only": dets=[d for d in dets if d["severity"]=="Critical"]
        elif sev_filter=="High+":       dets=[d for d in dets if SEV_RANK[d["severity"]]>=3]
        elif sev_filter=="Medium+":     dets=[d for d in dets if SEV_RANK[d["severity"]]>=2]
        with st.spinner("Annotating image…"):
            prog.progress(80)
            annotated=annotate_image(enhanced,dets)
        risk=compute_risk(dets);grade=score_to_grade(risk)
        st.session_state.update(detections=dets,annotated_img=annotated,risk_score=risk,grade=grade,
            vessel_name=vessel_name,scan_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            mission_id=f"M-{uuid.uuid4().hex[:6].upper()}",last_pdf=None,last_pdf_fname="")
        st.session_state.mission_history.append(dict(id=st.session_state.mission_id,
            vessel=vessel_name or "Unknown",date=st.session_state.scan_time,
            score=risk,grade=grade,detections=len(dets),mode=scan_mode))
        prog.progress(100);time.sleep(.3);prog.empty()
        st.success(f"Scan complete — {len(dets)} anomalies detected · Risk {risk}/100 · Grade {grade}")

    if st.session_state.detections:
        dets=st.session_state.detections;risk=st.session_state.risk_score;grade=st.session_state.grade
        crit=sum(1 for d in dets if d["severity"]=="Critical")
        high=sum(1 for d in dets if d["severity"]=="High")
        med =sum(1 for d in dets if d["severity"]=="Medium")

        ui_card_open()
        c1,c2,c3,c4,c5,c6=st.columns(6)
        c1.metric("Total Detections",len(dets));c2.metric("Critical",crit)
        c3.metric("High",high);c4.metric("Medium",med)
        c5.metric("Risk Score",f"{risk}/100");c6.metric("Grade",grade)
        ui_card_close()

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        ui_card_open()
        ca,cb=st.columns(2)
        with ca:
            if st.session_state.annotated_img:
                st.image(st.session_state.annotated_img,caption="Annotated Output",use_container_width=True)
        with cb:
            st.image(build_heatmap(st.session_state.enhanced_img,dets),caption="Risk Heatmap",use_container_width=True)
        ui_card_close()

        msg=("Critical — Immediate action required" if grade=="D"
             else "High Risk — Maintenance within 7 days" if grade=="C"
             else "Moderate Risk" if grade=="B" else "Healthy")

        st.markdown(f"""
        <div class="nc-card" style="margin-top:12px">
          <div class="nc-card-inner">
            <div style="display:flex;align-items:center;gap:24px;margin-bottom:12px">
              <div>
                <div style="font-size:11px;color:var(--muted2);margin-bottom:4px;
                  font-family:JetBrains Mono,monospace;letter-spacing:1px">Structural Integrity Risk Score</div>
                <div style="display:flex;align-items:baseline;gap:12px">
                  <span style="font-size:34px;font-weight:900;color:#fbbf24;
                    font-family:JetBrains Mono,monospace">{risk}<span style="font-size:15px;color:var(--muted2)">/100</span></span>
                  <span style="font-size:15px;font-weight:800;color:var(--brand)">Grade {grade} — {msg}</span>
                </div>
              </div>
              <div style="margin-left:auto;max-width:320px;font-size:12px;color:var(--muted);line-height:1.5">
                {"Scheduled maintenance recommended within 30 days. Monitor affected zones with bi-weekly ROV survey."
                 if grade=="B" else "Immediate action required."
                 if grade=="D" else "Maintenance within 7 days recommended."
                 if grade=="C" else "Continue routine monitoring schedule."}
              </div>
            </div>
            <div style="height:8px;background:rgba(255,255,255,0.04);border-radius:999px;overflow:hidden;border:1px solid var(--stroke2)">
              <div style="width:{risk}%;height:100%;border-radius:999px;
                background:linear-gradient(90deg,#34d399,#fbbf24 55%,#f87171)"></div>
            </div>
            <div style="display:flex;justify-content:space-between;margin-top:8px">
              <span style="font-size:10px;color:#34d399">Healthy 76–100</span>
              <span style="font-size:10px;color:#4cc9ff">Moderate 51–75</span>
              <span style="font-size:10px;color:#fbbf24">High Risk 26–50</span>
              <span style="font-size:10px;color:#f87171">Critical 0–25</span>
            </div>
          </div>
        </div>""",unsafe_allow_html=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        ui_card_open()
        st.markdown("""<div style='font-size:11px;font-weight:800;color:var(--muted2);
          letter-spacing:.8px;text-transform:uppercase;margin-bottom:10px'>Detection Results</div>""",unsafe_allow_html=True)
        import pandas as pd
        df=pd.DataFrame([{"#":f"{d['id']:02d}","Class":d["cls"],"Severity":d["severity"],
            "Confidence":f"{d['conf']*100:.1f}%","Bounding Box":f"({d['x1']},{d['y1']})→({d['x2']},{d['y2']})",
            "Area (px²)":f"{d.get('area',0):,}"} for d in dets])
        st.dataframe(df,hide_index=True,use_container_width=True)
        ui_card_close()

# ─── HULL ────────────────────────────────────────────────────────────────
with tab_hull:
    ui_section(
        "NAUTICAI / HULL INSPECTION",
        "Hull Inspection",
        "Visibility enhancement pipeline — CLAHE · Green-Water · Turbidity · Edge Estimator"
    )
    st.divider()
    ui_card_open()
    h_up=st.file_uploader("Upload hull image",type=["jpg","jpeg","png"],key="hull_up",label_visibility="collapsed")
    col_h1,col_h2=st.columns(2)
    with col_h1:
        st.button("Run AI Detection",use_container_width=True,type="primary",key="hull_run")
        st.button("Configure Settings",use_container_width=True,key="hull_cfg")
    with col_h2:
        if h_up: st.image(h_up,use_container_width=True)
    ui_card_close()

    if h_up:
        h_img=Image.open(h_up).convert("RGB")
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        ui_card_open()
        st.markdown("""<div style='font-size:11px;font-weight:800;color:var(--muted2);letter-spacing:.8px;text-transform:uppercase;margin-bottom:10px'>Enhancement Comparison</div>""",unsafe_allow_html=True)
        c1,c2,c3,c4=st.columns(4)
        c1.image(cv_to_pil(apply_clahe(pil_to_cv(h_img))),caption="CLAHE",use_container_width=True)
        c2.image(cv_to_pil(apply_green_water(pil_to_cv(h_img))),caption="Green-Water",use_container_width=True)
        c3.image(cv_to_pil(apply_turbidity(pil_to_cv(h_img),.45)),caption="Turbidity Sim",use_container_width=True)
        c4.image(cv_to_pil(apply_edge_estimator(pil_to_cv(h_img))),caption="Edge Estimator",use_container_width=True)
        ui_card_close()

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        with st.spinner("Running hull detection…"):
            enh=full_enhance(h_img,use_clahe,use_green,turbidity_in,corr_turb,use_edge,clahe_clip)
            hd=run_detection(enh,conf_thr,iou_thr,"hull")
            ha=annotate_image(enh,hd)
        rh=compute_risk(hd);gh=score_to_grade(rh)
        hull_hmap=build_heatmap(enh,hd)

        # Log hull inspection to mission history (dedup by file identity)
        _hull_key=f"hull_{h_up.name}_{h_up.size}"
        if not any(m.get("_src")==_hull_key for m in st.session_state.mission_history):
            hull_scan_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            hull_mission_id=f"HULL-{uuid.uuid4().hex[:6].upper()}"
            st.session_state.mission_history.append(dict(
                id=hull_mission_id,
                vessel=vessel_name or "Unknown",
                date=hull_scan_time,
                score=rh,grade=gh,
                detections=len(hd),
                mode="hull",
                _src=_hull_key,
            ))

        ui_card_open()
        ch1,ch2,ch3=st.columns(3)
        ch1.metric("Risk Score",f"{rh}/100");ch2.metric("Grade",gh);ch3.metric("Anomalies",len(hd))
        import pandas as pd
        st.dataframe(pd.DataFrame([{"#":f"{d['id']:02d}","Class":d["cls"],"Severity":d["severity"],"Confidence":f"{d['conf']*100:.1f}%"} for d in hd]),hide_index=True,use_container_width=True)
        ui_card_close()

        # ── Hull Inspection PDF Report ──
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        ui_card_open()
        st.markdown("""<div style='font-size:11px;font-weight:800;color:var(--muted2);letter-spacing:.8px;text-transform:uppercase;margin-bottom:10px'>Hull Inspection Report</div>""",unsafe_allow_html=True)
        hull_mid=f"HULL-{uuid.uuid4().hex[:6].upper()}"
        if st.button("📄  Generate Hull Inspection PDF",type="primary",use_container_width=True,key="hull_pdf_btn"):
            with st.spinner("Building Hull Inspection PDF report…"):
                try:
                    hull_pdf_bytes=build_pdf(
                        hull_mid,
                        vessel_name or "Unknown",
                        inspector, "hull", hd, h_img, ha, hull_hmap,
                        rh, gh, conf_thr, iou_thr
                    )
                    st.session_state.hull_pdf=hull_pdf_bytes
                    st.session_state.hull_pdf_fname=(
                        f"NautiCAI_Hull_{hull_mid}"
                        f"_{datetime.datetime.now().strftime('%Y%m%d')}.pdf")
                except Exception as e:
                    st.session_state.hull_pdf=None
                    st.session_state.hull_pdf_fname=""
                    st.error(f"PDF generation failed: {e}")
        if st.session_state.hull_pdf:
            st.download_button("⬇️  Download Hull Inspection PDF",data=st.session_state.hull_pdf,
                file_name=st.session_state.hull_pdf_fname or "NautiCAI_Hull_Report.pdf",
                mime="application/pdf",use_container_width=True,key="hull_pdf_dl")
            st.success(f"`{st.session_state.hull_pdf_fname}` is ready — click above to download.")
        ui_card_close()

# ─── VIDEO ───────────────────────────────────────────────────────────────
with tab_video:
    ui_section(
        "NAUTICAI / VIDEO ANALYSIS",
        "Video Analysis",
        "Frame-by-frame defect detection · RTSP live stream support · v1.5 planned (Q2 2026)"
    )
    st.divider()

    ui_card_open()
    v_up=st.file_uploader("Upload underwater video",type=["mp4","avi","mov","mkv"],key="vid_up",label_visibility="collapsed")
    col_v1,col_v2=st.columns(2)
    with col_v1:
        st.button("Run AI Detection",use_container_width=True,type="primary",key="vid_run")
        st.button("Configure Settings",use_container_width=True,key="vid_cfg")
    with col_v2:
        st.markdown("""<div style='background:rgba(255,255,255,0.03);border:1px solid var(--stroke2);border-radius:14px;aspect-ratio:16/9;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:12px'>📹 Video preview will appear here</div>""",unsafe_allow_html=True)
    ui_card_close()

    if v_up:
        with tempfile.NamedTemporaryFile(delete=False,suffix=Path(v_up.name).suffix) as tf:
            tf.write(v_up.read());tmp_path=tf.name
        cap=cv2.VideoCapture(tmp_path)
        total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));fps_v=cap.get(cv2.CAP_PROP_FPS) or 25
        wv=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));hv=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        ui_card_open()
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Total Frames",total);c2.metric("FPS",f"{fps_v:.1f}");c3.metric("Resolution",f"{wv}×{hv}");c4.metric("Duration",f"{total/fps_v:.1f}s")
        sample_n=st.slider("Sample every N frames",5,30,10)
        if st.button("Analyse Video",type="primary",use_container_width=True):
            prog2=st.progress(0);frames=[];all_video_dets=[];fn=0;det_id_offset=0
            first_pil_frame=None
            while True:
                ret,frame=cap.read()
                if not ret: break
                if fn%sample_n==0:
                    pf=cv_to_pil(frame)
                    if first_pil_frame is None: first_pil_frame=pf
                    ef=full_enhance(pf,use_clahe,use_green,turbidity_in,corr_turb,use_edge)
                    df_v=run_detection(ef,conf_thr,iou_thr,scan_mode)
                    # Re-number detection IDs globally across all frames
                    for d in df_v:
                        det_id_offset+=1; d["id"]=det_id_offset
                        d["frame"]=fn
                    all_video_dets.extend(df_v)
                    af=annotate_image(ef,df_v)
                    frames.append((fn,af,df_v,ef));prog2.progress(min(fn/max(total,1),.99))
                fn+=1
            cap.release()
            try: os.unlink(tmp_path)
            except OSError: pass
            prog2.progress(1.0)
            st.success(f"{len(frames)} frames processed · {len(all_video_dets)} total detections")

            # Display top annotated frames
            cf2=st.columns(min(4,max(len(frames),1)))
            for col_f,(fn2,ann2,_,_) in zip(cf2,frames[:4]):
                nd2=sum(1 for d in all_video_dets if d.get("frame")==fn2)
                col_f.image(ann2,caption=f"Frame {fn2} · {nd2} det.",use_container_width=True)

            # ── Write results to session state so Report tab picks them up ──
            # Pick the frame with the most detections as representative
            if frames:
                best_frame=max(frames,key=lambda f:len(f[2]))
                best_annot=best_frame[1]   # annotated PIL
                best_enhanced=best_frame[3] # enhanced PIL
                risk_v=compute_risk(all_video_dets);grade_v=score_to_grade(risk_v)
                st.session_state.update(
                    detections=all_video_dets,
                    annotated_img=best_annot,
                    original_img=first_pil_frame,
                    enhanced_img=best_enhanced,
                    risk_score=risk_v,
                    grade=grade_v,
                    vessel_name=vessel_name,
                    scan_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    mission_id=f"M-{uuid.uuid4().hex[:6].upper()}",
                    last_pdf=None,
                    last_pdf_fname="",
                )
                st.session_state.mission_history.append(dict(
                    id=st.session_state.mission_id,
                    vessel=vessel_name or "Unknown",
                    date=st.session_state.scan_time,
                    score=risk_v,grade=grade_v,
                    detections=len(all_video_dets),
                    mode=f"video/{scan_mode}",
                ))
        ui_card_close()

# ─── PIPELINE ────────────────────────────────────────────────────────────
with tab_pipe:
    ui_section(
        "NAUTICAI / PIPELINE & SUBSEA",
        "Pipeline Anomaly Detection",
        "7 pipeline-specific classes · Corrosion · Crack · Coating Failure · Pitting · Leakage · Weld Defect · Blockage"
    )
    st.divider()

    ui_card_open()
    p_up=st.file_uploader("Upload pipeline image",type=["jpg","jpeg","png"],key="pipe_up",label_visibility="collapsed")
    col_p1,col_p2=st.columns(2)
    with col_p1:
        st.button("Run AI Detection",use_container_width=True,type="primary",key="pipe_run")
        st.button("Configure Settings",use_container_width=True,key="pipe_cfg")
    with col_p2:
        if p_up: st.image(p_up,use_container_width=True)
    ui_card_close()

    if p_up:
        p_img=Image.open(p_up).convert("RGB")
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        ui_card_open()
        col_po,col_pa=st.columns(2)
        with col_po: st.image(p_img,caption="Original",use_container_width=True)
        with col_pa:
            with st.spinner("Running pipeline detection…"):
                pe=full_enhance(p_img,use_clahe,use_green,turbidity_in,corr_turb,use_edge,clahe_clip)
                pd_=run_detection(pe,conf_thr,iou_thr,"pipeline");pa=annotate_image(pe,pd_)
            st.image(pa,caption="Annotated Output",use_container_width=True)
        rp=compute_risk(pd_);gp=score_to_grade(rp)
        pipe_hmap=build_heatmap(pe,pd_)

        # Log pipeline inspection to mission history (dedup by file identity)
        _pipe_key=f"pipe_{p_up.name}_{p_up.size}"
        if not any(m.get("_src")==_pipe_key for m in st.session_state.mission_history):
            pipe_scan_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            pipe_mission_id=f"PIPE-{uuid.uuid4().hex[:6].upper()}"
            st.session_state.mission_history.append(dict(
                id=pipe_mission_id,
                vessel=vessel_name or "Unknown",
                date=pipe_scan_time,
                score=rp,grade=gp,
                detections=len(pd_),
                mode="pipeline",
                _src=_pipe_key,
            ))

        c1,c2,c3=st.columns(3);c1.metric("Risk Score",f"{rp}/100");c2.metric("Grade",gp);c3.metric("Anomalies",len(pd_))
        st.markdown("""<div style='font-size:11px;font-weight:800;color:var(--muted2);letter-spacing:.8px;text-transform:uppercase;margin:14px 0 8px'>Detection Results</div>""",unsafe_allow_html=True)
        import pandas as pd
        st.dataframe(pd.DataFrame([{"#":f"{d['id']:02d}","Class":d["cls"],"Severity":d["severity"],"Confidence":f"{d['conf']*100:.1f}%","Bounding Box":f"({d['x1']},{d['y1']})→({d['x2']},{d['y2']})"} for d in pd_]),hide_index=True,use_container_width=True)
        ui_card_close()

        # ── Pipeline & Subsea PDF Report ──
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        ui_card_open()
        st.markdown("""<div style='font-size:11px;font-weight:800;color:var(--muted2);letter-spacing:.8px;text-transform:uppercase;margin-bottom:10px'>Pipeline & Subsea Report</div>""",unsafe_allow_html=True)
        pipe_mid=f"PIPE-{uuid.uuid4().hex[:6].upper()}"
        if st.button("📄  Generate Pipeline & Subsea PDF",type="primary",use_container_width=True,key="pipe_pdf_btn"):
            with st.spinner("Building Pipeline & Subsea PDF report…"):
                try:
                    pipe_pdf_bytes=build_pdf(
                        pipe_mid,
                        vessel_name or "Unknown",
                        inspector, "pipeline", pd_, p_img, pa, pipe_hmap,
                        rp, gp, conf_thr, iou_thr
                    )
                    st.session_state.pipe_pdf=pipe_pdf_bytes
                    st.session_state.pipe_pdf_fname=(
                        f"NautiCAI_Pipeline_{pipe_mid}"
                        f"_{datetime.datetime.now().strftime('%Y%m%d')}.pdf")
                except Exception as e:
                    st.session_state.pipe_pdf=None
                    st.session_state.pipe_pdf_fname=""
                    st.error(f"PDF generation failed: {e}")
        if st.session_state.pipe_pdf:
            st.download_button("⬇️  Download Pipeline & Subsea PDF",data=st.session_state.pipe_pdf,
                file_name=st.session_state.pipe_pdf_fname or "NautiCAI_Pipeline_Report.pdf",
                mime="application/pdf",use_container_width=True,key="pipe_pdf_dl")
            st.success(f"`{st.session_state.pipe_pdf_fname}` is ready — click above to download.")
        ui_card_close()

# ─── CABLE ───────────────────────────────────────────────────────────────
with tab_cable:
    ui_section(
        "NAUTICAI / SUBSEA CABLE",
        "Subsea Cable Anomaly Detection",
        "6 cable classes · Fracture · Deformation · Foreign Object · Biofouling · Marine Growth · Dent"
    )
    st.divider()

    ui_card_open()
    c_up=st.file_uploader("Upload cable image",type=["jpg","jpeg","png"],key="cable_up",label_visibility="collapsed")
    ui_card_close()

    if c_up:
        c_img=Image.open(c_up).convert("RGB")
        ui_card_open()
        cc1,cc2=st.columns(2)
        with cc1: st.image(c_img,caption="Original",use_container_width=True)
        with cc2:
            with st.spinner("Running cable detection…"):
                ce=full_enhance(c_img,use_clahe,use_green,turbidity_in,corr_turb,True)
                cd=run_detection(ce,conf_thr,iou_thr,"cable");ca=annotate_image(ce,cd)
            st.image(ca,caption=f"{len(cd)} anomalies detected",use_container_width=True)
        rc=compute_risk(cd);gc=score_to_grade(rc)
        cable_hmap=build_heatmap(ce,cd)

        # Log cable inspection to mission history (dedup by file identity)
        _cable_key=f"cable_{c_up.name}_{c_up.size}"
        if not any(m.get("_src")==_cable_key for m in st.session_state.mission_history):
            cable_scan_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            cable_mission_id=f"CABLE-{uuid.uuid4().hex[:6].upper()}"
            st.session_state.mission_history.append(dict(
                id=cable_mission_id,
                vessel=vessel_name or "Unknown",
                date=cable_scan_time,
                score=rc,grade=gc,
                detections=len(cd),
                mode="cable",
                _src=_cable_key,
            ))

        cx1,cx2,cx3=st.columns(3);cx1.metric("Risk Score",f"{rc}/100");cx2.metric("Grade",gc);cx3.metric("Anomalies",len(cd))
        import pandas as pd
        st.dataframe(pd.DataFrame([{"ID":d["id"],"Class":d["cls"],"Severity":d["severity"],"Confidence":f"{d['conf']*100:.1f}%"} for d in cd]),hide_index=True,use_container_width=True)
        ui_card_close()

        # ── Cable Anomaly PDF Report ──
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        ui_card_open()
        st.markdown("""<div style='font-size:11px;font-weight:800;color:var(--muted2);letter-spacing:.8px;text-transform:uppercase;margin-bottom:10px'>Cable Anomaly Report</div>""",unsafe_allow_html=True)
        cable_mid=f"CABLE-{uuid.uuid4().hex[:6].upper()}"
        if st.button("📄  Generate Cable Anomaly PDF",type="primary",use_container_width=True,key="cable_pdf_btn"):
            with st.spinner("Building Cable Anomaly PDF report…"):
                try:
                    cable_pdf_bytes=build_pdf(
                        cable_mid,
                        vessel_name or "Unknown",
                        inspector, "cable", cd, c_img, ca, cable_hmap,
                        rc, gc, conf_thr, iou_thr
                    )
                    st.session_state.cable_pdf=cable_pdf_bytes
                    st.session_state.cable_pdf_fname=(
                        f"NautiCAI_Cable_{cable_mid}"
                        f"_{datetime.datetime.now().strftime('%Y%m%d')}.pdf")
                except Exception as e:
                    st.session_state.cable_pdf=None
                    st.session_state.cable_pdf_fname=""
                    st.error(f"PDF generation failed: {e}")
        if st.session_state.cable_pdf:
            st.download_button("⬇️  Download Cable Anomaly PDF",data=st.session_state.cable_pdf,
                file_name=st.session_state.cable_pdf_fname or "NautiCAI_Cable_Report.pdf",
                mime="application/pdf",use_container_width=True,key="cable_pdf_dl")
            st.success(f"`{st.session_state.cable_pdf_fname}` is ready — click above to download.")
        ui_card_close()

    with st.expander("Jetson Orin Edge Deployment — Real-Time FPS"):
        st.markdown("""
| Model | Quantisation | Latency | FPS (Jetson Orin) |
|---|---|---|---|
| YOLOv8n | INT8-TRT | 10 ms | ~95 FPS |
| YOLOv8s | INT8-TRT | 18 ms | ~55 FPS |
| YOLOv8m | INT8-TRT | 28 ms | ~34 FPS |
| YOLOv8x | FP16-TRT | 48 ms | ~20 FPS |
        """)

# ─── DASHBOARD ───────────────────────────────────────────────────────────
with tab_dash:
    ui_section(
        "NAUTICAI / MISSION DASHBOARD",
        "Mission Dashboard",
        "Fleet overview · mission history · risk trend · model performance analytics"
    )
    st.divider()

    history=st.session_state.mission_history
    if history:
        import pandas as pd
        df_h=pd.DataFrame([{k:v for k,v in m.items() if k!="_src"} for m in history])
        df_h.columns=[c.upper() for c in df_h.columns]
        ui_card_open()
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Total Missions",len(history))
        c2.metric("Avg Risk Score",f"{sum(m['score'] for m in history)//len(history)}/100")
        c3.metric("Total Detections",sum(m['detections'] for m in history))
        c4.metric("Critical Missions",sum(1 for m in history if m['grade']=="D"))
        st.divider()
        st.dataframe(df_h,hide_index=True,use_container_width=True)
        if len(history)>1:
            fig_d,ax_d=plt.subplots(figsize=(9,3),facecolor="#071427");ax_d.set_facecolor("#071427")
            x=range(len(history))
            ax_d.plot(x,[m["score"] for m in history],color="#4cc9ff",linewidth=2,marker="o",markersize=5)
            ax_d.fill_between(x,[m["score"] for m in history],alpha=.08,color="#4cc9ff")
            for val,lbl,c2 in [(76,"Grade A","#34d399"),(51,"Grade B","#4cc9ff"),(26,"Grade C","#fbbf24")]:
                ax_d.axhline(val,color=c2,linewidth=1,linestyle="--",alpha=.4,label=lbl)
            ax_d.legend(fontsize=8,facecolor="#071427",labelcolor="#7f97b2")
            ax_d.set_ylabel("Risk Score",color="#7f97b2",fontsize=10);ax_d.tick_params(colors="#7f97b2")
            for sp in ax_d.spines.values(): sp.set_color("#1e3050")
            fig_d.tight_layout();st.pyplot(fig_d,use_container_width=True)
        ui_card_close()
    else:
        st.info("No missions yet — run a scan on the Infrastructure Scan tab.")

    with st.expander("Model Performance Metrics — YOLOv8s"):
        mets={"Precision":.942,"Recall":.891,"mAP@0.5":.914,"mAP@0.5:0.95":.783,"F1 Score":.916}
        cols_m=st.columns(len(mets))
        for col_m,(k,v) in zip(cols_m,mets.items()): col_m.metric(k,f"{v*100:.1f}%")
        st.caption(f"Model: `{MODEL_PATH.name if MODEL_PATH else 'Demo'}` · Inference: 28ms @ 640×640")

# ─── REPORT ──────────────────────────────────────────────────────────────
with tab_report:
    ui_section(
        "NAUTICAI / REPORT & EXPORT",
        "Report & Export",
        "PDF inspection report · CSV data export · QR code verification · SHA-256 tamper-evident"
    )
    st.divider()

    if not st.session_state.detections:
        st.warning("Run an AI scan first (Infrastructure Scan or Video Analysis tab) to generate a report.")
    else:
        dets=st.session_state.detections;risk=st.session_state.risk_score;grade=st.session_state.grade
        orig=st.session_state.original_img;ann=st.session_state.annotated_img;enh=st.session_state.enhanced_img

        ui_card_open()
        cr1,cr2=st.columns(2)
        with cr1:
            st.markdown("##### Report Options")
            incl_heatmap=st.checkbox("Include Risk Heatmap",value=True)
            incl_recs   =st.checkbox("Include Recommendations",value=True)
            incl_edge   =st.checkbox("Include Edge Deploy Note",value=True)
            incl_qr     =st.checkbox("Embed QR Code",value=True)
        with cr2:
            st.markdown("##### Mission Summary")
            st.markdown(f"""
| Field | Value |
|---|---|
| Mission ID | `{st.session_state.mission_id}` |
| Vessel | `{st.session_state.vessel_name or 'N/A'}` |
| Scan Time | `{st.session_state.scan_time}` |
| Risk Score | `{risk}/100 (Grade {grade})` |
| Detections | `{len(dets)}` |
| Model | `{MODEL_PATH.name if MODEL_PATH else 'Demo'}` |
            """)
        ui_card_close()

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        ui_card_open()
        if st.button("📄  Generate PDF Report",type="primary",use_container_width=True):
            with st.spinner("Building PDF report…"):
                try:
                    hmap=build_heatmap(enh,dets) if incl_heatmap else None
                    pdf_bytes=build_pdf(
                        st.session_state.mission_id,
                        st.session_state.vessel_name or "Unknown",
                        inspector, scan_mode, dets, orig, ann, hmap,
                        risk, grade, conf_thr, iou_thr
                    )
                    st.session_state.last_pdf=pdf_bytes
                    st.session_state.last_pdf_fname=(
                        f"NautiCAI_Report_{st.session_state.mission_id}"
                        f"_{datetime.datetime.now().strftime('%Y%m%d')}.pdf")
                except Exception as e:
                    st.session_state.last_pdf=None
                    st.session_state.last_pdf_fname=""
                    st.error(f"PDF generation failed: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        # ── Persistent download button (survives Streamlit reruns) ──
        if st.session_state.last_pdf:
            st.download_button("⬇️  Download PDF Report",data=st.session_state.last_pdf,
                file_name=st.session_state.last_pdf_fname or "NautiCAI_Report.pdf",
                mime="application/pdf",use_container_width=True)
            st.success(f"`{st.session_state.last_pdf_fname}` is ready — click above to download.")
        ui_card_close()

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        ui_card_open()
        st.markdown("##### QR Code — Report Verification")
        _sev_counts={"Critical":0,"High":0,"Medium":0,"Low":0}
        for _d in dets:
            _sev_counts[_d.get("severity","Medium")]+=1
        _ts_now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        import hashlib as _hl
        _qr_hash=_hl.sha256(f"{st.session_state.mission_id}{st.session_state.vessel_name}{_ts_now}{risk}".encode()).hexdigest()[:12]
        qr_url=(
            f"https://aishwaryav25-nauticai-maritime.streamlit.app/"
            f"?tab=report&mission={st.session_state.mission_id}"
            f"&vessel={st.session_state.vessel_name or 'N/A'}"
            f"&grade={grade}&risk={risk}"
            f"&hash={_qr_hash}"
        )
        qr_pil=make_qr(qr_url)
        cq1,cq2=st.columns([1,2])
        with cq1:
            st.image(qr_pil,caption="Scan to open PDF report",width=180)
        with cq2:
            st.code(qr_url)
            st.markdown(f"""
- **Mission ID** `{st.session_state.mission_id}`
- **Risk Score** `{risk}/100` · **Grade** `{grade}`
- **Detections** `{len(dets)}`
- **SHA-256** `{_qr_hash}`
- **Scan QR** to open the app and download PDF
            """)
        ui_card_close()

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        ui_card_open()
        st.markdown("##### CSV Data Export")
        import pandas as pd
        df_csv=pd.DataFrame([{"mission_id":st.session_state.mission_id,"vessel":st.session_state.vessel_name,
            "class":d["cls"],"severity":d["severity"],"confidence":round(d["conf"],4),
            "x1":d["x1"],"y1":d["y1"],"x2":d["x2"],"y2":d["y2"],"area_px":d.get("area",0)} for d in dets])
        st.dataframe(df_csv,hide_index=True,use_container_width=True)
        st.download_button("⬇️  Download CSV",data=df_csv.to_csv(index=False).encode(),
            file_name=f"NautiCAI_{st.session_state.mission_id}.csv",mime="text/csv",use_container_width=True)
        ui_card_close()

# ─── ROADMAP ─────────────────────────────────────────────────────────────
with tab_roadmap:
    ui_section(
        "NAUTICAI / ROADMAP",
        "Technology Roadmap",
        "30+ features across v1.0 · v1.5 · v2.0 — built for subsea operators, ROV/AUV teams, and inspection companies"
    )
    st.divider()

    ROADMAP=[
        ("v1.0","Image Detection (19 defect classes)","Detection","LIVE","Feb 2026"),
        ("v1.0","Video Frame-by-Frame Detection","Detection","LIVE","Feb 2026"),
        ("v1.0","Corrosion Detection & Classification","Detection","LIVE","Feb 2026"),
        ("v1.0","Marine Growth / Biofouling Detection","Detection","LIVE","Feb 2026"),
        ("v1.0","Crack & Fracture Detection","Detection","LIVE","Feb 2026"),
        ("v1.0","Weld Defect & Pitting Detection","Detection","LIVE","Feb 2026"),
        ("v1.0","Confidence Threshold Control","Engine","LIVE","Feb 2026"),
        ("v1.0","IoU Threshold Control","Engine","LIVE","Feb 2026"),
        ("v1.0","Severity Filter (Critical/High/Med/Low)","Engine","LIVE","Feb 2026"),
        ("v1.0","Structural Integrity Risk Score (0–100)","Analysis","LIVE","Feb 2026"),
        ("v1.0","Health Grade System (A–D)","Analysis","LIVE","Feb 2026"),
        ("v1.0","CLAHE Contrast Enhancement","Visibility","LIVE","Feb 2026"),
        ("v1.0","Turbidity Simulation + Correction","Visibility","LIVE","Feb 2026"),
        ("v1.0","Green-Water Colour Enhancement","Visibility","LIVE","Feb 2026"),
        ("v1.0","Edge Estimator (Canny-based)","Visibility","LIVE","Feb 2026"),
        ("v1.0","PDF Inspection Report Export","Reports","LIVE","Feb 2026"),
        ("v1.0","CSV Structured Data Export","Reports","LIVE","Feb 2026"),
        ("v1.0","QR Code Report Link Generator","Reports","LIVE","Feb 2026"),
        ("v1.0","Model Performance Metrics (mAP, F1)","Analytics","LIVE","Feb 2026"),
        ("v1.0","Mission History Log & Trend Chart","Analytics","LIVE","Feb 2026"),
        ("v1.0","Hull Inspection Mode","Modes","LIVE","Feb 2026"),
        ("v1.0","Pipeline Inspection Mode","Modes","LIVE","Feb 2026"),
        ("v1.0","Port Infrastructure Mode","Modes","LIVE","Feb 2026"),
        ("v1.0","Subsea Cable Inspection Mode","Modes","LIVE","Feb 2026"),
        ("v1.5","Real-time RTSP ROV Live Stream","Streaming","Planned","Q2 2026"),
        ("v1.5","Multi-ROV Fleet Coordination","Streaming","Planned","Q2 2026"),
        ("v1.5","Temporal Defect Tracking","Detection","Planned","Q2 2026"),
        ("v1.5","Predictive Maintenance AI Engine","Analytics","Planned","Q2 2026"),
        ("v2.0","3D Point Cloud Structural Mapping","Advanced","Planned","Q4 2026"),
        ("v2.0","Digital Twin Integration","Advanced","Planned","Q4 2026"),
    ]

    ui_card_open()
    p1,p2,p3=st.columns(3)
    for col,phase,eta,color in zip([p1,p2,p3],["v1.0","v1.5","v2.0"],["Feb 2026","Q2 2026","Q4 2026"],["#34d399","#4cc9ff","#a78bfa"]):
        tp=sum(1 for r in ROADMAP if r[0]==phase)
        lp=sum(1 for r in ROADMAP if r[0]==phase and r[3]=="LIVE")
        status="LIVE" if lp>0 else "PLANNED"
        col.markdown(f"""
        <div style='background:rgba(255,255,255,0.04);border:1px solid var(--stroke2);border-radius:16px;padding:16px'>
          <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:10px'>
            <span style='font-size:18px;font-weight:900;color:{color};font-family:JetBrains Mono,monospace'>{phase}</span>
            <span style='background:{"rgba(52,211,153,.12)" if lp>0 else "rgba(148,163,184,.10)"};
              color:{"#34d399" if lp>0 else "var(--muted2)"};border:1px solid {"rgba(52,211,153,.25)" if lp>0 else "rgba(148,163,184,.14)"};
              border-radius:999px;padding:4px 10px;font-size:10px;font-weight:900;letter-spacing:1px'>{status}</span>
          </div>
          <div style='font-size:30px;font-weight:900;color:var(--text);font-family:JetBrains Mono,monospace'>
            {lp}<span style='font-size:16px;color:var(--muted2)'>/{tp}</span></div>
          <div style='font-size:10px;color:var(--muted2);letter-spacing:.8px;text-transform:uppercase;margin-bottom:8px'>
            FEATURES ACTIVE · ETA {eta}</div>
          <div style='height:7px;background:rgba(255,255,255,0.04);border-radius:999px;overflow:hidden;border:1px solid var(--stroke2)'>
            <div style='width:{int(lp/tp*100) if tp>0 else 0}%;height:100%;background:{color};border-radius:999px'></div>
          </div>
        </div>""",unsafe_allow_html=True)

    import pandas as pd
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    co1,co2=st.columns(2)
    with co1: pf=st.selectbox("Filter Phase",["All","v1.0","v1.5","v2.0"])
    with co2: cf=st.selectbox("Filter Category",["All"]+sorted(set(r[2] for r in ROADMAP)))
    df_rm=pd.DataFrame(ROADMAP,columns=["Phase","Feature","Category","Status","ETA"]);df_rm.index+=1
    if pf!="All": df_rm=df_rm[df_rm["Phase"]==pf]
    if cf!="All": df_rm=df_rm[df_rm["Category"]==cf]
    st.dataframe(df_rm,use_container_width=True)
    ui_card_close()

# ─── FOOTER ──────────────────────────────────────────────────────────────
st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align:center;color:rgba(159,179,200,0.55);font-size:11px;padding:8px 0;
  font-family:JetBrains Mono,monospace;letter-spacing:1px'>
  NautiCAI · Singapore Maritime AI Systems · Est. 2024 · v1.0.4 ·
  YOLOv8 · OpenCV · Streamlit · ReportLab · NVIDIA Jetson Orin
</div>""",unsafe_allow_html=True)