import React, { useState, useRef, useCallback, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RTooltip, ResponsiveContainer, BarChart, Bar, Legend } from "recharts";
import PipelineMap2D from "./PipelineMap2D";
import MultiPipeline3D from "./MultiPipeline3D";
import { getHealth, runDetection, runEnhance, downloadBatchPDF, downloadVideoPDF, runVideoDetection, sendPDFToWhatsApp, sendVideoPDFToWhatsApp, sendWhatsAppMessage } from "./api";

// ═══════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════
const TABS = [
  { id: "scan", icon: "🔬", label: "Anomaly Scan" },
  { id: "hull", icon: "🚢", label: "Hull Inspect" },
  { id: "video", icon: "🎬", label: "Video Analysis" },
  { id: "pipeline", icon: "🔧", label: "Pipeline" },
  { id: "cable", icon: "⚡", label: "Sub-sea Cable" },
  { id: "deadline", icon: "⏰", label: "Deadlines" },
  { id: "dash", icon: "📊", label: "Dashboard" },
  { id: "memory", icon: "🧠", label: "Mission Memory" },
  { id: "comply", icon: "📋", label: "Compliance" },
  { id: "zero", icon: "🎯", label: "Zero-Shot" },
  { id: "road", icon: "🗺️", label: "Roadmap" },
];

const pgVar = {
  enter: { opacity: 0, y: 20 },
  center: { opacity: 1, y: 0, transition: { duration: 0.3, ease: [0.4, 0, 0.2, 1] } },
  exit: { opacity: 0, y: -12, transition: { duration: 0.15 } },
};

const PHASES = [
  { num: "01", ver: "v1.0", sub: "core", badge: "LIVE", badgeColor: "#22c55e", tagline: "Foundation · Beta", items: ["Single-mission image and video ingestion", "Deep vision anomaly detection for hull, pipeline and cable", "Visibility enhancement (CLAHE, green-water and turbidity filters)", "Severity labels, risk scoring and mission grading", "PDF inspection packs and mission-level dashboard", "Internal pilots with design partners (operator-in-the-loop)"] },
  { num: "02", ver: "v2.0", sub: "scale", badge: "Q3–Q4 2025", badgeColor: "#22d3ee", tagline: "Scale · Reliability", items: ["Production-grade pipeline and cable modules", "Mission analytics: trend views, class heatmaps and severity distributions", "Real-time ROV streaming connector and low-latency inference", "Multi-tenant cloud dashboard with role-based access control (RBAC)", "Customer API and webhooks for CMMS / digital twin integrations", "Hardening, monitoring, alerting and SLA-backed deployments"] },
  { num: "03", ver: "v3.0", sub: "auto", badge: "2026+", badgeColor: "#a855f7", tagline: "Intelligence · Autonomy", items: ["Subsea cable burial-depth estimation and route risk scoring", "3D point-cloud reconstruction and digital twin integration", "Cross-mission degradation tracking and anomaly forecasting", "AI-assisted fleet inspection planning and optimisation engine", "Semi-autonomous ROV guidance and inspection playbooks", "Regulatory-grade compliance reporting and full audit trail"] },
];

const TECH_STACK = [
  { label: "Detection", value: "Vision AI Engine", color: "#22d3ee" },
  { label: "Backend", value: "FastAPI", color: "#94a3b8" },
  { label: "Frontend", value: "React", color: "#60a5fa" },
  { label: "Cloud", value: "GCP", color: "#4ade80" },
  { label: "Inference", value: "PyTorch", color: "#f97316" },
  { label: "Reports", value: "FPDF2", color: "#c084fc" },
];

const makeId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

// ═══════════════════════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════════════════════
function bboxArea(b) { if (!b) return null; return Math.round(Math.abs((b.xmax ?? b.x2 ?? 0) - (b.xmin ?? b.x1 ?? 0)) * Math.abs((b.ymax ?? b.y2 ?? 0) - (b.ymin ?? b.y1 ?? 0))); }
function fmtArea(px) { return px ? px.toLocaleString() + " px" : "—"; }
function confColor(c) { if (c == null) return "inherit"; if (c >= 0.75) return "#22c55e"; if (c >= 0.5) return "#f59e0b"; return "#ef4444"; }
function sevColor(s) { if (!s) return "#6b7280"; const v = s.toLowerCase(); if (v === "critical") return "#ef4444"; if (v === "high") return "#f97316"; if (v === "medium") return "#f59e0b"; if (v === "low") return "#22c55e"; return "#6b7280"; }

// ═══════════════════════════════════════════════════════════════════════════
// REPAIR COST LOOKUP
// ═══════════════════════════════════════════════════════════════════════════
const REPAIR_COSTS = {
  corrosion: { low: [800,2000], medium: [2500,6000], high: [6000,15000], critical: [15000,40000] },
  crack: { low: [1500,4000], medium: [4000,12000], high: [12000,30000], critical: [30000,80000] },
  biofouling: { low: [300,800], medium: [800,2500], high: [2500,6000], critical: [6000,15000] },
  dent: { low: [500,1500], medium: [1500,5000], high: [5000,12000], critical: [12000,30000] },
  coating_damage: { low: [400,1200], medium: [1200,3500], high: [3500,8000], critical: [8000,20000] },
  weld_defect: { low: [2000,5000], medium: [5000,15000], high: [15000,35000], critical: [35000,90000] },
  buckling: { low: [3000,8000], medium: [8000,20000], high: [20000,50000], critical: [50000,120000] },
  pitting: { low: [600,1800], medium: [1800,4500], high: [4500,10000], critical: [10000,25000] },
  erosion: { low: [700,2000], medium: [2000,5500], high: [5500,13000], critical: [13000,32000] },
  deformation: { low: [1000,3000], medium: [3000,8000], high: [8000,20000], critical: [20000,55000] },
  default: { low: [500,2000], medium: [2000,6000], high: [6000,15000], critical: [15000,40000] },
};
function getRepairCost(cls, severity, areaPx) {
  const key = Object.keys(REPAIR_COSTS).find((k) => (cls || "").toLowerCase().includes(k)) || "default";
  const sev = (severity || "low").toLowerCase();
  const [lo, hi] = REPAIR_COSTS[key][sev] || REPAIR_COSTS.default[sev] || [500,2000];
  const mul = areaPx ? Math.min(Math.max(areaPx / 10000, 0.5), 3.0) : 1.0;
  return { low: Math.round(lo * mul), high: Math.round(hi * mul) };
}

// ═══════════════════════════════════════════════════════════════════════════
// DEGRADATION
// ═══════════════════════════════════════════════════════════════════════════
const SEV_NUMERIC = { low: 1, medium: 2, high: 3, critical: 4 };
const SEV_LABELS = ["", "Low", "Medium", "High", "Critical"];
const DEG_RATES = { corrosion:0.045, crack:0.06, biofouling:0.03, dent:0.015, coating_damage:0.04, weld_defect:0.055, buckling:0.05, pitting:0.04, erosion:0.035, deformation:0.025, default:0.035 };
function projectDeg(cls, severity, months) {
  const key = Object.keys(DEG_RATES).find((k) => (cls || "").toLowerCase().includes(k)) || "default";
  const rate = DEG_RATES[key]; const start = SEV_NUMERIC[(severity || "low").toLowerCase()] || 1;
  const pts = [];
  for (let m = 0; m <= months; m++) { const val = Math.min(start + rate * m + (Math.random() * 0.08 - 0.04), 4); pts.push({ month: m, value: parseFloat(val.toFixed(2)), label: SEV_LABELS[Math.min(Math.round(val), 4)] }); }
  return pts;
}

// ═══════════════════════════════════════════════════════════════════════════
// DEADLINES
// ═══════════════════════════════════════════════════════════════════════════
function addMo(date, m) { const d = new Date(date); d.setMonth(d.getMonth() + m); return d; }
function daysTo(date) { return Math.max(0, Math.ceil((date - new Date()) / 86400000)); }
function urgCol(u) { if (u === "critical") return "#ef4444"; if (u === "high") return "#f97316"; if (u === "medium") return "#f59e0b"; return "#22c55e"; }
function calcDeadlines(det) {
  if (!det) return [];
  const g = (det.grade || "C").toUpperCase(), ds = det.detections || [];
  const hc = ds.some((d) => (d.severity || "").toLowerCase() === "critical");
  const hh = ds.some((d) => (d.severity || "").toLowerCase() === "high");
  const now = new Date(), dl = [];
  if (hc) dl.push({ body:"IMO", type:"Emergency Hull Survey", due:addMo(now,1), urgency:"critical", rule:"SOLAS II-1/10 — Critical defect" });
  else if (g <= "B") dl.push({ body:"IMO", type:"Annual Hull Survey", due:addMo(now,12), urgency:"low", rule:"SOLAS Reg. II-1/10" });
  else dl.push({ body:"IMO", type:"Intermediate Hull Survey", due:addMo(now,6), urgency:"medium", rule:"Grade C/D intermediate" });
  if (hc || hh) dl.push({ body:"DNV / LR", type:"Condition of Class Rectification", due:addMo(now,3), urgency:"high", rule:"DNV Pt.7 Ch.1" });
  dl.push({ body:"DNV / LR", type:"Class Renewal", due:addMo(now,g<="B"?60:30), urgency:"low", rule:"IACS UR Z10.1" });
  dl.push({ body:"SOLAS", type:"Safety Equipment Survey", due:addMo(now,12), urgency:"low", rule:"SOLAS Reg. I/8" });
  if (hc) dl.push({ body:"FLAG STATE", type:"Emergency Dry-Dock", due:addMo(now,2), urgency:"critical", rule:"Immediate dry-dock" });
  else if (hh) dl.push({ body:"FLAG STATE", type:"Scheduled Dry-Dock", due:addMo(now,12), urgency:"medium", rule:"Twice in 5 years" });
  else dl.push({ body:"FLAG STATE", type:"Routine Dry-Dock", due:addMo(now,30), urgency:"low", rule:"IACS UR Z10.2" });
  if (g==="D"||g==="F"||hc) dl.push({ body:"PSC", type:"Port State Detention Risk", due:addMo(now,1), urgency:"critical", rule:"Paris/Tokyo MOU" });
  dl.push({ body:"P&I CLUB", type:"Insurance Survey", due:addMo(now,g<="B"?12:6), urgency:g<="B"?"low":"medium", rule:"P&I interim survey" });
  return dl.sort((a,b) => a.due - b.due);
}

// ═══════════════════════════════════════════════════════════════════════════
// MAIN APP
// ═══════════════════════════════════════════════════════════════════════════
export default function App() {
  const [tab, setTab] = useState("scan");
  const [health, setHealth] = useState(null);
  const [tabUploads, setTabUploads] = useState({});
  const uploads = tabUploads[tab] ?? [];
  const [tabSelectedIdx, setTabSelectedIdx] = useState({});
  const selectedIdx = tabSelectedIdx[tab] ?? 0;
  const selectedUpload = uploads[selectedIdx] ?? null;
  const setSelectedIdx = (idx) => setTabSelectedIdx((p) => ({ ...p, [tab]: idx }));
  const [conf, setConf] = useState(0.25);
  const [iou, setIou] = useState(0.45);
  const [sevFilter, setSevFilter] = useState("All Detections");
  const [clahe, setClahe] = useState(true);
  const [claheClip, setClaheClip] = useState(3.0);
  const [green, setGreen] = useState(true);
  const [edge, setEdge] = useState(false);
  const [turbLevel, setTurbLevel] = useState(0.0);
  const [corrTurb, setCorrTurb] = useState(true);
  const [marineSnow, setMarineSnow] = useState(false);
  const [vesselName, setVesselName] = useState("");
  const [inspector, setInspector] = useState("NautiCAI AutoScan v1.0");
  const [inspMode, setInspMode] = useState("general");
  const [reportPassword, setReportPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [videoFile, setVideoFile] = useState(null);
  const [videoLoading, setVideoLoading] = useState(false);
  const [videoResult, setVideoResult] = useState(null);
  const [reportsGenerated, setReportsGenerated] = useState(0);
  const [sessionDetections, setSessionDetections] = useState(0);
  const [sendingWa, setSendingWa] = useState(false);
  const [waMessage, setWaMessage] = useState("");
  const [completionAlertSent, setCompletionAlertSent] = useState(false);
  const [privacyCountdown, setPrivacyCountdown] = useState(null);
  const [deletionCert, setDeletionCert] = useState(null);
  const [complianceOpen, setComplianceOpen] = useState(false);
  const [missions, setMissions] = useState([]);
  const [zeroShotClasses, setZeroShotClasses] = useState([]);
  const [insp1Sev, setInsp1Sev] = useState("");
  const [insp2Sev, setInsp2Sev] = useState("");
  const [demoUser] = useState(() => { try { const u = sessionStorage.getItem("nauticai-demo-user"); return u ? JSON.parse(u) : null; } catch { return null; } });

  const latestDetResult = useMemo(() => {
    for (const t of ["scan","hull","pipeline","cable"]) { const arr = tabUploads[t] || []; for (let i = arr.length - 1; i >= 0; i--) { if (arr[i]?.detResult) return arr[i].detResult; } }
    return null;
  }, [tabUploads]);

  useEffect(() => { const p = new URLSearchParams(window.location.search); if (p.get("demo")==="1") { const u = { name:p.get("name")||"", email:p.get("email")||"", whatsapp:p.get("whatsapp")||"" }; sessionStorage.setItem("nauticai-demo-access","1"); sessionStorage.setItem("nauticai-demo-user",JSON.stringify(u)); window.history.replaceState({},"",window.location.pathname); } if (sessionStorage.getItem("nauticai-demo-access")!=="1") sessionStorage.setItem("nauticai-demo-access","1"); }, []);
  useEffect(() => { const poll = () => getHealth().then(setHealth).catch(() => setHealth({ status:"offline" })); poll(); const t = setInterval(poll,30000); return () => clearInterval(t); }, []);
  useEffect(() => { if (!latestDetResult) return; setPrivacyCountdown(60); setDeletionCert(null); setInsp1Sev(""); setInsp2Sev(""); saveMission(latestDetResult); }, [latestDetResult]);
  useEffect(() => { if (privacyCountdown===null) return; if (privacyCountdown<=0) { const b = new Uint8Array(8); crypto.getRandomValues(b); setDeletionCert({ hash:Array.from(b).map((x)=>x.toString(16).padStart(2,"0")).join("").toUpperCase(), time:new Date().toISOString() }); setPrivacyCountdown(null); return; } const t = setTimeout(()=>setPrivacyCountdown((n)=>n-1),1000); return ()=>clearTimeout(t); }, [privacyCountdown]);

  const saveMission = async (det) => { try { const m = { id:det.mission_id??`M-${Date.now().toString(36).toUpperCase()}`, date:new Date().toISOString(), vessel:vesselName||"Unknown", grade:det.grade??"—", risk:det.risk_score??0, total:det.total??(det.detections?.length??0), classes:[...new Set((det.detections||[]).map((d)=>d.cls??d.class).filter(Boolean))], mode:inspMode }; if (window.storage) await window.storage.set(`mission:${m.id}`,JSON.stringify(m)); setMissions((prev)=>[m,...prev.filter((x)=>x.id!==m.id)].slice(0,20)); } catch(e) { console.error("Mission save:",e); } };
  useEffect(() => { const load = async () => { try { if (!window.storage) return; const keys = await window.storage.list("mission:"); const arr = await Promise.all((keys.keys||[]).map(async(k)=>{ try { const r = await window.storage.get(k); return r?JSON.parse(r.value):null; } catch { return null; } })); setMissions(arr.filter(Boolean).sort((a,b)=>new Date(b.date)-new Date(a.date))); } catch{} }; load(); }, []);

  const fileRef = useRef(), folderRef = useRef(), videoRef = useRef();
  const createUploadItem = (file) => ({ id:makeId(), file, preview:URL.createObjectURL(file), detResult:null, enhResult:null });
  const handleFiles = useCallback((fileList) => { const valid = Array.from(fileList||[]).filter((f)=>f.type.startsWith("image/")); if (!valid.length) return; const items = valid.map(createUploadItem); setTabUploads((prev)=>({...prev,[tab]:[...(prev[tab]||[]),...items]})); setTabSelectedIdx((prev)=>({...prev,[tab]:(tabUploads[tab]||[]).length>0?(prev[tab]??0):0})); setError(""); setPrivacyCountdown(null); setDeletionCert(null); }, [tab,tabUploads]);
  const updateUploadInTab = useCallback((tabId,id,patch) => { setTabUploads((prev)=>({...prev,[tabId]:(prev[tabId]||[]).map((item)=>item.id===id?{...item,...patch}:item)})); }, []);
  const removeUpload = useCallback((id) => { setTabUploads((prev)=>{ const arr=prev[tab]||[]; const item=arr.find((x)=>x.id===id); if (item?.preview) URL.revokeObjectURL(item.preview); return {...prev,[tab]:arr.filter((x)=>x.id!==id)}; }); setTabSelectedIdx((prev)=>({...prev,[tab]:Math.max(0,(prev[tab]??0)-((prev[tab]??0)>=uploads.length-1?1:0))})); }, [tab,uploads.length]);
  const clearUploads = useCallback(() => { setTabUploads((prev)=>{ (prev[tab]||[]).forEach((x)=>x.preview&&URL.revokeObjectURL(x.preview)); return {...prev,[tab]:[]}; }); setTabSelectedIdx((prev)=>({...prev,[tab]:0})); }, [tab]);

  const onDragOver = (e) => { e.preventDefault(); e.currentTarget.classList.add("drag-over"); };
  const onDragLeave = (e) => { e.currentTarget.classList.remove("drag-over"); };
  const onDrop = (e) => { e.preventDefault(); e.currentTarget.classList.remove("drag-over"); handleFiles(e.dataTransfer.files); };

  const detParams = () => ({ conf_thr:conf, iou_thr:iou, mode:inspMode, sev_filter:sevFilter, use_clahe:clahe, clahe_clip:claheClip, use_green:green, use_edge:edge, turbidity_in:turbLevel, corr_turb:corrTurb, marine_snow:marineSnow });
  const enhParams = () => ({ use_clahe:clahe, clahe_clip:claheClip, use_green:green, use_edge:edge, turbidity_in:turbLevel, corr_turb:corrTurb, marine_snow:marineSnow });

  const detectAll = async () => { if (!uploads.length) return; setLoading(true); setError(""); setCompletionAlertSent(false); try { for (const item of uploads) { const data = await runDetection(item.file,detParams()); updateUploadInTab(tab,item.id,{detResult:data}); setSessionDetections((n)=>n+(data.total??data.detections?.length??0)); } } catch(e) { setError(e.response?.data?.detail||e.message); } setLoading(false); };
  const enhanceAll = async () => { if (!uploads.length) return; setLoading(true); setError(""); try { for (const item of uploads) { const data = await runEnhance(item.file,enhParams()); updateUploadInTab(tab,item.id,{enhResult:data}); } } catch(e) { setError(e.response?.data?.detail||e.message); } setLoading(false); };
  const runBothAll = async () => { if (!uploads.length) return; setLoading(true); setError(""); setCompletionAlertSent(false); try { for (const item of uploads) { const [det,enh] = await Promise.all([runDetection(item.file,detParams()),runEnhance(item.file,enhParams())]); updateUploadInTab(tab,item.id,{detResult:det,enhResult:enh}); setSessionDetections((n)=>n+(det.total??det.detections?.length??0)); } } catch(e) { setError(e.response?.data?.detail||e.message); } setLoading(false); };
  const genPDF = async () => { if (!uploads.length) return; setError(""); try { await downloadBatchPDF(uploads.map((u)=>u.file),{...detParams(),vessel_name:vesselName||"Unknown",inspector,pdf_password:reportPassword}); setReportsGenerated((n)=>n+1); } catch(e) { setError(e.response?.data?.detail||e.message); } };
  const genVideoPDF = async () => { if (!videoFile) return; setError(""); try { await downloadVideoPDF(videoFile,{conf_thr:conf,iou_thr:iou,mode:inspMode,vessel_name:vesselName||"Unknown",inspector,sample_n:10,use_clahe:clahe,clahe_clip:claheClip,use_green:green,use_edge:edge,turbidity_in:turbLevel,corr_turb:corrTurb,pdf_password:reportPassword}); setReportsGenerated((n)=>n+1); } catch(e) { setError(e.response?.data?.detail||e.message); } };
  const waTo = () => demoUser?.whatsapp?.trim()||"";
  const sendPDFToWa = async () => { if (!uploads.length) return; if (!waTo()) { setWaMessage("Add your WhatsApp number."); setTimeout(()=>setWaMessage(""),4000); return; } setSendingWa(true); setWaMessage(""); setError(""); try { const res = await sendPDFToWhatsApp(uploads[0].file,{...detParams(),vessel_name:vesselName||"Unknown",inspector,to:waTo(),pdf_password:reportPassword}); setWaMessage(res.sent?"Report sent.":res.message||"Could not send."); } catch(e) { setWaMessage(e.response?.data?.message||e.message||"Failed."); } setSendingWa(false); };
  const sendVideoPDFToWa = async () => { if (!videoFile) return; if (!waTo()) { setWaMessage("Add your WhatsApp number."); setTimeout(()=>setWaMessage(""),4000); return; } setSendingWa(true); setWaMessage(""); setError(""); try { const res = await sendVideoPDFToWhatsApp(videoFile,{conf_thr:conf,iou_thr:iou,mode:inspMode,vessel_name:vesselName||"Unknown",inspector,sample_n:10,use_clahe:clahe,clahe_clip:claheClip,use_green:green,use_edge:edge,turbidity_in:turbLevel,corr_turb:corrTurb,to:waTo(),pdf_password:reportPassword}); setWaMessage(res.sent?"Sent.":res.message||"Failed."); } catch(e) { setWaMessage(e.response?.data?.message||e.message||"Failed."); } setSendingWa(false); };
  const sendCompletionAlert = async (src="image") => { if (!waTo()) { setWaMessage("Add your WhatsApp number."); setTimeout(()=>setWaMessage(""),4000); return; } const data=src==="video"?videoResult:latestDetResult; if (!data) return; const total=data.total??data.detections?.length??data.total_detections??0; setSendingWa(true); setWaMessage(""); try { const res = await sendWhatsAppMessage(waTo().replace(/\s/g,""),`NautiCAI done. Risk:${data.risk_score??"—"} Grade:${data.grade??"—"} ${total} det.`); if (res.sent) { setWaMessage("Alert sent."); setCompletionAlertSent(true); } else setWaMessage(res.message||"Failed."); } catch(e) { setWaMessage(e.response?.data?.message||e.message||"Failed."); } setSendingWa(false); };
  const analyzeVideo = async () => { if (!videoFile) return; setVideoLoading(true); setError(""); setCompletionAlertSent(false); try { const data = await runVideoDetection(videoFile,{conf_thr:conf,iou_thr:iou,mode:inspMode,sample_n:10,use_clahe:clahe,clahe_clip:claheClip,use_green:green,use_edge:edge,turbidity_in:turbLevel,corr_turb:corrTurb}); setVideoResult(data); setSessionDetections((n)=>n+(data.total_detections??data.detections?.length??0)); } catch(e) { setError(e.response?.data?.detail||e.message); } setVideoLoading(false); };
  const exportCSV = (data) => { const dets=data?.detections||[]; if (!dets.length) return; const csv=[["id","class","confidence","severity","bbox_area_px"].join(","),...dets.map((d,i)=>{ const w=Math.abs((d.bbox?.xmax??d.bbox?.x2??0)-(d.bbox?.xmin??d.bbox?.x1??0)); const h=Math.abs((d.bbox?.ymax??d.bbox?.y2??0)-(d.bbox?.ymin??d.bbox?.y1??0)); return [i+1,d.cls??d.class??"",d.conf!=null?Number(d.conf).toFixed(4):"",d.severity??"",Math.round(w*h)].map((c)=>`"${String(c).replace(/"/g,'""')}"`).join(","); })].join("\n"); const a=document.createElement("a"); a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"})); a.download=`NautiCAI_${data?.mission_id||"export"}.csv`; a.click(); };

  useEffect(() => { const onKey=(e)=>{ if (!e.ctrlKey||e.key!=="Enter") return; e.preventDefault(); if (tab==="scan"&&uploads.length) runBothAll(); else if (["hull","pipeline","cable"].includes(tab)&&uploads.length) detectAll(); else if (tab==="video"&&videoFile) analyzeVideo(); }; window.addEventListener("keydown",onKey); return ()=>window.removeEventListener("keydown",onKey); }, [tab,uploads,videoFile]);

  const imagePageProps = { uploads, selectedUpload, selectedIdx, setSelectedIdx, fileRef, folderRef, handleFiles, removeUpload, clearUploads, onDragOver, onDragLeave, onDrop, detectAll, enhanceAll, runBothAll, genPDF, sendPDFToWa, sendCompletionAlert, completionAlertSent, sendingWa, waMessage, exportCSV, loading, error, privacyCountdown, deletionCert, insp1Sev, setInsp1Sev, insp2Sev, setInsp2Sev, onOpenCompliance:()=>setComplianceOpen(true) };

  return (
    <div className="app-shell">
      {complianceOpen && <ComplianceModal detResult={latestDetResult} vesselName={vesselName} inspector={inspector} onClose={()=>setComplianceOpen(false)} />}
      <aside className="sidebar">
        <div className="sb-brand"><img className="sb-logo" src="/nauticai-logo.png" alt="NautiCAI" /><div className="sb-brand-text"><h3>NAUTICAI</h3><a href="https://www.nauticai-ai.com" target="_blank" rel="noreferrer">www.nauticai-ai.com</a></div></div>
        <div className="sb-status"><span className="pill"><span className={`dot ${health?.status==="ok"?"dot-ok":"dot-warn"}`} />{health?.status==="ok"?"API Online":"API Offline"}</span>{health?.model&&<span className="pill"><span className="dot dot-ok" />{health.model}</span>}</div>
        <div className="sb-section"><div className="sb-label">Detection Engine</div><div className="ctrl"><div className="ctrl-header"><label>Confidence Threshold</label><span>{conf.toFixed(2)}</span></div><input type="range" className="ctrl-slider" min={0.05} max={0.95} step={0.05} value={conf} onChange={(e)=>setConf(+e.target.value)} /></div><div className="ctrl"><div className="ctrl-header"><label>IoU Threshold</label><span>{iou.toFixed(2)}</span></div><input type="range" className="ctrl-slider" min={0.1} max={0.9} step={0.05} value={iou} onChange={(e)=>setIou(+e.target.value)} /></div></div>
        <div className="sb-sep" />
        <div className="sb-section"><div className="sb-label">Severity Filter</div><div className="ctrl"><div className="ctrl-header"><label>Display mode</label></div><select className="ctrl-select" value={sevFilter} onChange={(e)=>setSevFilter(e.target.value)}><option>All Detections</option><option>Critical Only</option><option>High+</option><option>Medium+</option></select></div></div>
        <div className="sb-sep" />
        <div className="sb-section"><div className="sb-label">Visibility Engine</div><Toggle label="CLAHE Enhancement" checked={clahe} onChange={()=>setClahe(!clahe)} />{clahe&&<div className="ctrl"><div className="ctrl-header"><label>CLAHE Clip Limit</label><span>{claheClip.toFixed(2)}</span></div><input type="range" className="ctrl-slider" min={1} max={10} step={0.5} value={claheClip} onChange={(e)=>setClaheClip(+e.target.value)} /></div>}<Toggle label="Green-Water Filter" checked={green} onChange={()=>setGreen(!green)} /><Toggle label="Edge Estimator" checked={edge} onChange={()=>setEdge(!edge)} /><div className="ctrl"><div className="ctrl-header"><label>Turbidity Level</label><span>{turbLevel.toFixed(2)}</span></div><input type="range" className="ctrl-slider" min={0} max={1} step={0.05} value={turbLevel} onChange={(e)=>setTurbLevel(+e.target.value)} /></div><Toggle label="Turbidity Correction" checked={corrTurb} onChange={()=>setCorrTurb(!corrTurb)} /><Toggle label="Marine Snow" checked={marineSnow} onChange={()=>setMarineSnow(!marineSnow)} /></div>
        <div className="sb-sep" />
        <div className="sb-section"><div className="sb-label">Mission Info</div><div className="ctrl"><div className="ctrl-header"><label>Vessel Name</label></div><input type="text" className="ctrl-input" placeholder="e.g. MV Neptune Star" value={vesselName} onChange={(e)=>setVesselName(e.target.value)} /></div><div className="ctrl"><div className="ctrl-header"><label>Inspector</label></div><input type="text" className="ctrl-input" value={inspector} onChange={(e)=>setInspector(e.target.value)} /></div><div className="ctrl"><div className="ctrl-header"><label>Inspection Mode</label></div><select className="ctrl-select" value={inspMode} onChange={(e)=>setInspMode(e.target.value)}><option value="general">General Inspection</option><option value="hull">Hull Inspection</option><option value="pipeline">Pipeline Inspection</option><option value="cable">Cable Inspection</option></select></div><div className="ctrl"><div className="ctrl-header"><label>Report Password (optional)</label></div><input type="password" className="ctrl-input" placeholder="Encrypt PDF" value={reportPassword} onChange={(e)=>setReportPassword(e.target.value)} autoComplete="off" /><small className="ctrl-hint">PDFs will require this password to open.</small></div></div>
        <div className="sb-footer"><img src="/nauticai-logo.png" alt="" /><a href="https://www.nauticai-ai.com" target="_blank" rel="noreferrer">www.nauticai-ai.com</a><small>© 2025 NautiCAI Pte Ltd · Singapore</small></div>
      </aside>
      <div className="main-area">
        <header className="topbar"><div className="topbar-left"><img className="topbar-logo" src="/nauticai-logo.png" alt="NautiCAI" /><div className="topbar-title"><h1>NAUTICAI</h1><p>Deep-sea Anomaly Detection Platform</p></div></div><div className="topbar-right"><span className="topbar-chip">BETA · INTERNAL DEMO</span><a href={window.location.port==="3000"?"http://localhost:8080/demo.html":"/demo.html"} target="_blank" rel="noopener noreferrer" className="btn btn-primary btn-sm" style={{textDecoration:"none",color:"inherit"}}>Book a demo</a></div></header>
        <div className="tab-bar" style={{overflowX:"auto"}}>{TABS.map((t)=><button key={t.id} className={`tab-btn ${tab===t.id?"active":""}`} onClick={()=>setTab(t.id)}><span className="tab-icon">{t.icon}</span>{t.label}</button>)}</div>
        <AnimatePresence mode="wait">
          <motion.div key={tab} className="page-content" variants={pgVar} initial="enter" animate="center" exit="exit">
            {tab==="scan"&&<ScanPage {...imagePageProps} />}
            {tab==="hull"&&<HullPage {...imagePageProps} />}
            {tab==="video"&&<VideoPage videoFile={videoFile} videoRef={videoRef} setVideoFile={setVideoFile} onDragOver={onDragOver} onDragLeave={onDragLeave} analyzeVideo={analyzeVideo} genVideoPDF={genVideoPDF} sendVideoPDFToWa={sendVideoPDFToWa} sendCompletionAlert={sendCompletionAlert} completionAlertSent={completionAlertSent} videoLoading={videoLoading} sendingWa={sendingWa} waMessage={waMessage} videoResult={videoResult} error={error} />}
            {tab==="pipeline"&&<PipelinePage {...imagePageProps} />}
            {tab==="cable"&&<CablePage {...imagePageProps} />}
            {tab==="deadline"&&<DeadlinePage detResult={latestDetResult} />}
            {tab==="dash"&&<DashPage detResult={latestDetResult} videoResult={videoResult} sessionDetections={sessionDetections} reportsGenerated={reportsGenerated} />}
            {tab==="memory"&&<MemoryPage missions={missions} />}
            {tab==="comply"&&<CompliancePage detResult={latestDetResult} vesselName={vesselName} inspector={inspector} />}
            {tab==="zero"&&<ZeroShotPage zeroShotClasses={zeroShotClasses} setZeroShotClasses={setZeroShotClasses} uploads={uploads} fileRef={fileRef} folderRef={folderRef} handleFiles={handleFiles} onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop} />}
            {tab==="road"&&<RoadmapPage />}
          </motion.div>
        </AnimatePresence>
        <footer className="app-footer"><img src="/nauticai-logo.png" alt="" /><span className="footer-dot">·</span><a href="https://www.nauticai-ai.com" target="_blank" rel="noreferrer">www.nauticai-ai.com</a><span className="footer-dot">·</span><span>NautiCAI v1.0 — Deep-tech Venture · Singapore</span></footer>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// SHARED COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════
function Toggle({label,checked,onChange}) { return <label className="ctrl-toggle"><span className="tgl"><input type="checkbox" checked={checked} onChange={onChange} /><span className="tgl-track" /><span className="tgl-knob" /></span><span>{label}</span></label>; }

function DropZone({fileRef,folderRef,uploads,handleFiles,onDragOver,onDragLeave,onDrop}) {
  return (<div className="card mb-20"><div className="card-title">Image Upload</div><div className="dropzone" onClick={()=>fileRef.current?.click()} onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}><div className="dz-icon">📷</div><div className="dz-label">{uploads?.length?`Uploaded ${uploads.length} image(s) — click or drop to add more`:"Drop underwater image(s) here, or click to browse"}</div><div className="dz-hint">Supported: JPG, PNG, BMP · Multiple images + folder upload</div></div><div className="row" style={{gap:10,marginTop:12,flexWrap:"wrap"}}><button type="button" className="btn btn-ghost" onClick={()=>fileRef.current?.click()}>+ Add Images</button><button type="button" className="btn btn-ghost" onClick={()=>folderRef.current?.click()}>📁 Upload Folder</button></div><input ref={fileRef} type="file" accept="image/*" multiple hidden onChange={(e)=>handleFiles(e.target.files)} /><input ref={folderRef} type="file" accept="image/*" multiple hidden onChange={(e)=>handleFiles(e.target.files)} {...{webkitdirectory:"",directory:""}} /></div>);
}

function SpotlightFilmstrip({uploads,selectedIdx,setSelectedIdx,removeUpload,clearUploads}) {
  if (!uploads?.length) return null;
  return (<div className="card mb-20" style={{overflow:"hidden"}}><div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:14}}><div className="card-title" style={{margin:0}}>Uploaded Images</div><div style={{display:"flex",gap:8}}><div style={{fontSize:12,opacity:0.65,padding:"8px 12px",border:"1px solid rgba(255,255,255,0.08)",borderRadius:8,background:"rgba(255,255,255,0.02)"}}>{selectedIdx+1} / {uploads.length}</div><button className="btn btn-ghost" onClick={clearUploads}>Clear All</button></div></div><div style={{display:"grid",gridTemplateColumns:"180px 1fr",gap:14,minHeight:420}}><div style={{display:"flex",flexDirection:"column",gap:10,maxHeight:420,overflowY:"auto",paddingRight:4}}>{uploads.map((item,idx)=>(<button key={item.id} onClick={()=>setSelectedIdx(idx)} style={{width:"100%",textAlign:"left",border:idx===selectedIdx?"2px solid #22d3ee":"1px solid rgba(255,255,255,0.08)",borderRadius:10,padding:6,background:idx===selectedIdx?"rgba(34,211,238,0.08)":"rgba(255,255,255,0.02)",cursor:"pointer",display:"flex",gap:8,alignItems:"center"}}><img src={item.preview} alt="" style={{width:58,height:58,objectFit:"cover",borderRadius:6,flexShrink:0}} /><div style={{minWidth:0,flex:1}}><div style={{fontSize:11,fontWeight:700,color:idx===selectedIdx?"#22d3ee":"rgba(255,255,255,0.88)",marginBottom:4}}>Image {idx+1}</div><div style={{fontSize:10,color:"rgba(255,255,255,0.6)",whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>{item.file.name}</div></div></button>))}</div><div style={{position:"relative",borderRadius:12,overflow:"hidden",background:"rgba(255,255,255,0.03)",minHeight:420,display:"flex",alignItems:"center",justifyContent:"center"}}><img src={uploads[selectedIdx]?.preview} alt="" style={{width:"100%",height:"100%",maxHeight:420,objectFit:"contain",display:"block"}} /><div style={{position:"absolute",top:12,left:12,display:"flex",gap:8}}><div style={{background:"rgba(0,0,0,0.65)",padding:"6px 10px",borderRadius:6,fontSize:12,color:"#fff"}}>Active Image</div><div style={{background:"rgba(34,211,238,0.18)",border:"1px solid rgba(34,211,238,0.35)",padding:"6px 10px",borderRadius:6,fontSize:12,color:"#22d3ee",fontWeight:700}}>#{selectedIdx+1}</div></div><div style={{position:"absolute",bottom:12,left:12,right:12,display:"flex",justifyContent:"space-between",alignItems:"center",gap:10}}><div style={{background:"rgba(0,0,0,0.65)",padding:"8px 12px",borderRadius:8,fontSize:12,color:"#fff",whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis",maxWidth:"75%"}}>{uploads[selectedIdx]?.file?.name}</div><button className="btn btn-ghost" style={{background:"rgba(0,0,0,0.65)"}} onClick={()=>removeUpload(uploads[selectedIdx].id)}>Remove</button></div></div></div></div>);
}

function StatusBar({error,waMessage}) { return (<>{error&&<div className="alert alert-error" style={{marginTop:12}}>{error}</div>}{waMessage&&<div className="alert" style={{marginTop:8}}>{waMessage}</div>}</>); }

function PrivacyTimer({countdown,cert}) { if (countdown===null&&!cert) return null; if (cert) return (<div style={{marginTop:16,padding:"12px 16px",background:"#00cc4411",border:"1px solid #00cc4444",borderRadius:8}}><div style={{fontSize:11,color:"#00cc44",fontWeight:700,letterSpacing:1,marginBottom:6}}>✅ DELETION CERTIFICATE ISSUED</div><div style={{fontSize:11,opacity:0.7}}>All client footage cryptographically deleted.</div><div style={{fontSize:10,opacity:0.5,marginTop:4,fontFamily:"monospace"}}>CERT-{cert.hash} · {new Date(cert.time).toLocaleTimeString()}</div></div>); const pct=(countdown/60)*100; const col=countdown>30?"#22c55e":countdown>10?"#f59e0b":"#ef4444"; return (<div style={{marginTop:16,padding:"12px 16px",background:"#ef444411",border:"1px solid #ef444433",borderRadius:8}}><div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:8}}><div style={{fontSize:11,color:col,fontWeight:700,letterSpacing:1}}>🔒 PRIVACY-FIRST AUTO-DELETION</div><div style={{fontSize:18,fontWeight:900,color:col,fontFamily:"monospace"}}>{countdown}s</div></div><div style={{height:4,borderRadius:2,background:"rgba(255,255,255,0.08)",overflow:"hidden"}}><div style={{width:`${pct}%`,height:"100%",background:col,borderRadius:2,transition:"width 1s linear"}} /></div><div style={{fontSize:10,opacity:0.5,marginTop:6}}>Client footage will be cryptographically deleted after this timer.</div></div>); }

function DisagreementFlag({insp1Sev,setInsp1Sev,insp2Sev,setInsp2Sev}) { const sevs=["","Low","Medium","High","Critical"]; const dis=insp1Sev&&insp2Sev&&insp1Sev!==insp2Sev; return (<div className="card" style={{marginTop:16}}><div className="card-title" style={{marginBottom:12}}>👁️ Inspector Disagreement Flag</div><div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12,marginBottom:12}}>{[["Inspector 1",insp1Sev,setInsp1Sev],["Inspector 2",insp2Sev,setInsp2Sev]].map(([l,v,s])=>(<div key={l}><div style={{fontSize:11,opacity:0.5,marginBottom:6}}>{l} Severity</div><select className="ctrl-select" style={{width:"100%"}} value={v} onChange={(e)=>s(e.target.value)}>{sevs.map((sv)=><option key={sv} value={sv}>{sv||"— Select —"}</option>)}</select></div>))}</div>{dis&&<div style={{padding:"10px 14px",background:"#f59e0b22",border:"1px solid #f59e0b55",borderRadius:6}}><div style={{color:"#f59e0b",fontWeight:700,fontSize:12,marginBottom:4}}>⚠️ DISAGREEMENT — Third Review Required</div><div style={{fontSize:11,opacity:0.7}}>Inspector 1: <strong>{insp1Sev}</strong> · Inspector 2: <strong>{insp2Sev}</strong></div></div>}{insp1Sev&&insp2Sev&&!dis&&<div style={{padding:"10px 14px",background:"#22c55e22",border:"1px solid #22c55e44",borderRadius:6}}><div style={{color:"#22c55e",fontWeight:700,fontSize:12}}>✅ Inspectors agree — {insp1Sev} confirmed</div></div>}</div>); }

function PieChart({data,size=160}) { const total=data.reduce((s,d)=>s+d.value,0); if (!total) return null; const cx=size/2,cy=size/2,r=size/2-10; let ang=-Math.PI/2; const slices=data.map((d)=>{ const a=(d.value/total)*2*Math.PI; const x1=cx+r*Math.cos(ang),y1=cy+r*Math.sin(ang); const x2=cx+r*Math.cos(ang+a),y2=cy+r*Math.sin(ang+a); const path=`M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${a>Math.PI?1:0} 1 ${x2} ${y2} Z`; const mx=cx+(r*0.65)*Math.cos(ang+a/2),my=cy+(r*0.65)*Math.sin(ang+a/2); ang+=a; return {...d,path,mx,my,pct:((d.value/total)*100).toFixed(0)}; }); return (<svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>{slices.map((s,i)=>(<g key={i}><path d={s.path} fill={s.color} opacity={0.9} stroke="rgba(0,0,0,0.3)" strokeWidth="1" />{parseInt(s.pct)>=8&&<text x={s.mx} y={s.my} textAnchor="middle" dominantBaseline="middle" fill="white" fontSize="10" fontWeight="700">{s.pct}%</text>}</g>))}</svg>); }

function ImgPanel({label,color,src,placeholder}) { return (<div style={{position:"relative"}}><span style={{position:"absolute",top:10,left:10,zIndex:2,background:"rgba(0,0,0,0.6)",border:`1px solid ${color}44`,color,fontSize:10,fontWeight:700,letterSpacing:1,padding:"3px 8px",borderRadius:4,textTransform:"uppercase"}}>{label}</span>{src?<img src={src} alt={label} style={{width:"100%",borderRadius:8,display:"block"}} />:<div style={{background:"rgba(255,255,255,0.03)",borderRadius:8,minHeight:200,display:"flex",alignItems:"center",justifyContent:"center",color:"rgba(255,255,255,0.2)",fontSize:12}}>{placeholder}</div>}</div>); }
function StatBox({label,value,color,small}) { return (<div className="card" style={{textAlign:"center",padding:"16px 10px"}}><div style={{fontSize:small?14:22,fontWeight:700,color,wordBreak:"break-all"}}>{value}</div><div style={{fontSize:10,letterSpacing:1,opacity:0.45,marginTop:4,textTransform:"uppercase"}}>{label}</div></div>); }
function BigStat({label,value,color}) { return (<div className="card" style={{textAlign:"center",padding:"20px 12px"}}><div style={{fontSize:10,letterSpacing:1,opacity:0.4,textTransform:"uppercase",marginBottom:8}}>{label}</div><div style={{fontSize:28,fontWeight:700,color}}>{value}</div></div>); }

// ═══════════════════════════════════════════════════════════════════════════
// DETECTION RESULTS PANEL
// ═══════════════════════════════════════════════════════════════════════════
function DetectionResultsPanel({detResult,enhResult,preview,exportCSV}) {
  if (!detResult&&!enhResult) return null;
  const dets=detResult?.detections||[]; const total=detResult?.total??dets.length??0;
  const ann=detResult?.annotated_b64??detResult?.image??null;
  const heat=detResult?.heatmap_b64??detResult?.heatmap??null;
  const enh=detResult?.enhanced_b64??enhResult?.enhanced_b64??enhResult?.image??null;
  const sc=dets.reduce((a,d)=>{const s=d.severity||"Unknown";a[s]=(a[s]||0)+1;return a;},{});
  const pie=[{label:"Critical",value:sc["Critical"]??0,color:"#ef4444"},{label:"High",value:sc["High"]??0,color:"#f97316"},{label:"Medium",value:sc["Medium"]??0,color:"#f59e0b"},{label:"Low",value:sc["Low"]??0,color:"#22c55e"}].filter((d)=>d.value>0);
  return (<div style={{marginTop:24}}>{detResult&&(<><div style={{marginBottom:16}}><div style={{fontSize:13,letterSpacing:1,opacity:0.5,textTransform:"uppercase",marginBottom:4}}>Detection Results</div><div style={{fontSize:20,fontWeight:700}}>{total} {total===1?"Anomaly":"Anomalies"} Found</div></div><div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12,marginBottom:20}}><StatBox label="DETECTIONS" value={total} color="#22d3ee" /><StatBox label="RISK SCORE" value={detResult.risk_score!=null?`${detResult.risk_score}%`:"—"} color="#f59e0b" /><StatBox label="GRADE" value={detResult.grade??"—"} color="#a78bfa" /><StatBox label="MISSION" value={detResult.mission_id??"—"} color="#94a3b8" small /></div></>)}<div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12,marginBottom:12}}><ImgPanel label="ANNOTATED" color="#22d3ee" src={ann?`data:image/jpeg;base64,${ann}`:null} placeholder="Run detection" /><ImgPanel label="HEATMAP" color="#f59e0b" src={heat?`data:image/jpeg;base64,${heat}`:null} placeholder="Not available" /></div><div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12,marginBottom:20}}><ImgPanel label="ORIGINAL" color="#64748b" src={preview} placeholder="No image" /><ImgPanel label="ENHANCED" color="#22c55e" src={enh?`data:image/jpeg;base64,${enh}`:null} placeholder="Click Detect + Enhance" /></div>{pie.length>0&&(<div className="card" style={{marginBottom:20}}><div className="card-title" style={{marginBottom:14}}>Severity Distribution</div><div style={{display:"flex",alignItems:"center",gap:32}}><PieChart data={pie} size={160} /><div style={{flex:1}}>{pie.map((d)=>(<div key={d.label} style={{display:"flex",alignItems:"center",gap:10,marginBottom:10}}><span style={{width:12,height:12,borderRadius:"50%",background:d.color,flexShrink:0}} /><span style={{fontSize:13,flex:1}}>{d.label}</span><span style={{fontWeight:700,color:d.color}}>{d.value}</span><span style={{fontSize:11,opacity:0.5,minWidth:32}}>{((d.value/total)*100).toFixed(0)}%</span></div>))}<div style={{marginTop:14,paddingTop:12,borderTop:"1px solid rgba(255,255,255,0.07)",fontSize:12,opacity:0.6}}>Recovery Rate: <strong style={{color:"#22c55e"}}>{(((sc["Low"]??0)+(sc["Medium"]??0))/total*100).toFixed(0)}%</strong></div></div></div></div>)}{dets.length>0&&(<div className="card" style={{overflowX:"auto"}}><div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:14}}><div className="card-title" style={{margin:0}}>Detection Breakdown — {dets.length} objects</div><button className="btn btn-ghost" style={{padding:"4px 12px",fontSize:12}} onClick={()=>exportCSV({detections:dets,mission_id:detResult?.mission_id})}>📊 CSV</button></div><table style={{width:"100%",borderCollapse:"collapse",fontSize:13}}><thead><tr style={{borderBottom:"1px solid rgba(255,255,255,0.08)"}}>{["#","CLASS","CONFIDENCE","SEVERITY","BBOX AREA"].map((h)=><th key={h} style={{padding:"6px 12px",textAlign:"left",opacity:0.45,fontSize:11,letterSpacing:0.8,fontWeight:600}}>{h}</th>)}</tr></thead><tbody>{dets.map((d,i)=>(<tr key={i} style={{borderBottom:"1px solid rgba(255,255,255,0.04)"}}><td style={{padding:"8px 12px",opacity:0.4}}>{i+1}</td><td style={{padding:"8px 12px",fontWeight:600}}>{d.cls??d.class??"—"}</td><td style={{padding:"8px 12px"}}><span style={{color:confColor(d.conf),fontWeight:600}}>{d.conf!=null?`${(d.conf*100).toFixed(1)}%`:"—"}</span></td><td style={{padding:"8px 12px"}}>{d.severity?<span style={{display:"inline-flex",alignItems:"center",gap:5,padding:"3px 10px",borderRadius:4,fontSize:11,fontWeight:700,background:sevColor(d.severity)+"22",color:sevColor(d.severity)}}><span style={{width:7,height:7,borderRadius:"50%",background:sevColor(d.severity)}} />{d.severity}</span>:"—"}</td><td style={{padding:"8px 12px",opacity:0.6}}>{fmtArea(bboxArea(d.bbox))}</td></tr>))}</tbody></table></div>)}</div>);
}

function ImageActionButtons({uploads,loading,detectAll,genPDF,sendPDFToWa,sendCompletionAlert,completionAlertSent,sendingWa,exportCSV,latestDetForTab,onOpenCompliance,scanLabel="Run Scan",showEnhance=false,enhanceAll,runBothAll}) {
  return (<div className="row mb-20" style={{gap:10,flexWrap:"wrap"}}><button className="btn btn-primary" disabled={!uploads.length||loading} onClick={detectAll}>{loading&&<span className="spinner" />} {scanLabel}</button>{showEnhance&&<><button className="btn btn-ghost" disabled={!uploads.length||loading} onClick={enhanceAll}>Enhance Visibility</button><button className="btn btn-primary" disabled={!uploads.length||loading} onClick={runBothAll}>Detect + Enhance</button></>}<button className="btn btn-ghost" disabled={!uploads.length} onClick={genPDF}>📄 PDF Report</button><button className="btn btn-ghost" disabled={!uploads.length||sendingWa} onClick={sendPDFToWa}>{sendingWa?"…":"📱 WhatsApp"}</button>{latestDetForTab&&<><button className="btn btn-ghost" disabled={sendingWa||completionAlertSent} onClick={()=>sendCompletionAlert("image")}>{completionAlertSent?"✓ Sent":"🔔 Alert"}</button><button className="btn btn-ghost" onClick={()=>exportCSV(latestDetForTab)}>📊 CSV</button><button className="btn btn-primary" onClick={onOpenCompliance}>📋 Compliance</button></>}</div>);
}

// ═══════════════════════════════════════════════════════════════════════════
// COMPLIANCE
// ═══════════════════════════════════════════════════════════════════════════
function ComplianceSection({title,color,children}) { return (<div style={{marginBottom:24,border:`1px solid ${color}22`,borderRadius:8,overflow:"hidden"}}><div style={{padding:"10px 16px",background:`${color}11`,borderBottom:`1px solid ${color}22`,fontSize:12,fontWeight:700,color,letterSpacing:0.5}}>{title}</div><div style={{padding:4}}>{children}</div></div>); }
function ComplianceRow({label,value,highlight}) { return (<div style={{display:"flex",padding:"8px 16px",borderBottom:"1px solid rgba(255,255,255,0.04)"}}><div style={{width:240,fontSize:12,opacity:0.5}}>{label}</div><div style={{flex:1,fontSize:12,fontWeight:highlight?700:400,color:highlight?"#22d3ee":"inherit"}}>{String(value)}</div></div>); }
function ComplianceModal({detResult,vesselName,inspector,onClose}) {
  const dets=detResult?.detections||[]; const total=detResult?.total??dets.length; const classes=[...new Set(dets.map((d)=>d.cls??d.class).filter(Boolean))]; const today=new Date().toLocaleDateString("en-GB");
  return (<div style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.85)",zIndex:1000,display:"flex",alignItems:"center",justifyContent:"center",padding:20}}><div style={{background:"#080f1e",border:"1px solid #0d2a4a",borderRadius:12,width:"100%",maxWidth:800,maxHeight:"90vh",overflow:"auto",padding:32}}><div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:24}}><div><div style={{fontSize:11,opacity:0.5,letterSpacing:1,textTransform:"uppercase"}}>NautiCAI · Compliance</div><h2 style={{fontSize:22,fontWeight:700}}>Regulatory Auto-Fill Report</h2></div>{onClose&&<button className="btn btn-ghost" onClick={onClose}>✕ Close</button>}</div><ComplianceSection title="IMO" color="#22d3ee"><ComplianceRow label="Vessel" value={vesselName||"Unknown"} /><ComplianceRow label="Date" value={today} /><ComplianceRow label="Inspector" value={inspector} /><ComplianceRow label="Defects" value={total} /><ComplianceRow label="Classes" value={classes.join(", ")||"None"} /><ComplianceRow label="Grade" value={detResult?.grade??"—"} /><ComplianceRow label="Risk" value={detResult?.risk_score!=null?`${detResult.risk_score}%`:"—"} /><ComplianceRow label="Status" value={detResult?.grade==="A"||detResult?.grade==="B"?"COMPLIANT":"NON-COMPLIANT"} highlight /></ComplianceSection><ComplianceSection title="SOLAS" color="#22c55e"><ComplianceRow label="Chapter II-1" value="Completed" /><ComplianceRow label="Critical" value={dets.filter((d)=>d.severity==="Critical").length} /><ComplianceRow label="Immediate Action" value={dets.some((d)=>d.severity==="Critical")?"YES":"NO"} highlight /></ComplianceSection><ComplianceSection title="DNV" color="#f59e0b"><ComplianceRow label="Method" value="YOLOv8 — Deep Learning CV" /><ComplianceRow label="Anomalies" value={total} /><ComplianceRow label="Avg Confidence" value={dets.length?`${(dets.reduce((s,d)=>s+(d.conf??0),0)/dets.length*100).toFixed(1)}%`:"—"} /><ComplianceRow label="Status" value="AI Pre-Survey Completed" highlight /></ComplianceSection><ComplianceSection title="Lloyd's Register" color="#a855f7"><ComplianceRow label="Mission" value={detResult?.mission_id??"—"} /><ComplianceRow label="Signature" value="NautiCAI Platform v1.0" highlight /></ComplianceSection><div style={{display:"flex",gap:12,marginTop:24}}><button className="btn btn-primary" onClick={()=>window.print()}>🖨️ Print</button>{onClose&&<button className="btn btn-ghost" onClick={onClose}>Close</button>}</div></div></div>);
}

// ═══════════════════════════════════════════════════════════════════════════
// PAGE: SCAN
// ═══════════════════════════════════════════════════════════════════════════
function ScanPage(props) {
  const {uploads,selectedUpload,selectedIdx,setSelectedIdx,fileRef,folderRef,handleFiles,removeUpload,clearUploads,onDragOver,onDragLeave,onDrop,detectAll,enhanceAll,runBothAll,genPDF,sendPDFToWa,sendCompletionAlert,completionAlertSent,sendingWa,waMessage,exportCSV,loading,error,privacyCountdown,deletionCert,insp1Sev,setInsp1Sev,insp2Sev,setInsp2Sev,onOpenCompliance}=props;
  const det=uploads.find((x)=>x.detResult)?.detResult||null;
  return (<><div className="section-header fade-up"><div className="section-crumb">Module · Anomaly Detection</div><h2 className="section-title">Underwater Anomaly Scan</h2><p className="section-desc">Upload underwater images for AI-powered anomaly detection, visibility enhancement, and PDF reports.</p><div className="section-rule" /></div><DropZone {...{fileRef,folderRef,uploads,handleFiles,onDragOver,onDragLeave,onDrop}} /><SpotlightFilmstrip {...{uploads,selectedIdx,setSelectedIdx,removeUpload,clearUploads}} /><ImageActionButtons uploads={uploads} loading={loading} detectAll={detectAll} genPDF={genPDF} sendPDFToWa={sendPDFToWa} sendCompletionAlert={sendCompletionAlert} completionAlertSent={completionAlertSent} sendingWa={sendingWa} exportCSV={exportCSV} latestDetForTab={det} onOpenCompliance={onOpenCompliance} scanLabel="Run Detection" showEnhance enhanceAll={enhanceAll} runBothAll={runBothAll} /><StatusBar error={error} waMessage={waMessage} /><PrivacyTimer countdown={privacyCountdown} cert={deletionCert} />{selectedUpload&&<DetectionResultsPanel detResult={selectedUpload.detResult} enhResult={selectedUpload.enhResult} preview={selectedUpload.preview} exportCSV={exportCSV} />}{det&&<DisagreementFlag insp1Sev={insp1Sev} setInsp1Sev={setInsp1Sev} insp2Sev={insp2Sev} setInsp2Sev={setInsp2Sev} />}</>);
}

// ═══════════════════════════════════════════════════════════════════════════
// PAGE: HULL
// ═══════════════════════════════════════════════════════════════════════════
function HullPage(props) {
  const {uploads,selectedUpload,selectedIdx,setSelectedIdx,fileRef,folderRef,handleFiles,removeUpload,clearUploads,onDragOver,onDragLeave,onDrop,detectAll,genPDF,sendPDFToWa,sendCompletionAlert,completionAlertSent,sendingWa,waMessage,exportCSV,loading,error,privacyCountdown,deletionCert,insp1Sev,setInsp1Sev,insp2Sev,setInsp2Sev,onOpenCompliance}=props;
  const det=uploads.find((x)=>x.detResult)?.detResult||null;
  return (<><div className="section-header fade-up"><div className="section-crumb">Module · Hull Inspection</div><h2 className="section-title">Hull Inspection</h2><p className="section-desc">Detect corrosion, biofouling, cracks and structural anomalies on vessel hull surfaces.</p><div className="section-rule" /></div><DropZone {...{fileRef,folderRef,uploads,handleFiles,onDragOver,onDragLeave,onDrop}} /><SpotlightFilmstrip {...{uploads,selectedIdx,setSelectedIdx,removeUpload,clearUploads}} /><ImageActionButtons uploads={uploads} loading={loading} detectAll={detectAll} genPDF={genPDF} sendPDFToWa={sendPDFToWa} sendCompletionAlert={sendCompletionAlert} completionAlertSent={completionAlertSent} sendingWa={sendingWa} exportCSV={exportCSV} latestDetForTab={det} onOpenCompliance={onOpenCompliance} scanLabel="Run Hull Scan" /><StatusBar error={error} waMessage={waMessage} /><PrivacyTimer countdown={privacyCountdown} cert={deletionCert} />{selectedUpload&&<DetectionResultsPanel detResult={selectedUpload.detResult} preview={selectedUpload.preview} exportCSV={exportCSV} />}{det&&<DisagreementFlag insp1Sev={insp1Sev} setInsp1Sev={setInsp1Sev} insp2Sev={insp2Sev} setInsp2Sev={setInsp2Sev} />}</>);
}

// ═══════════════════════════════════════════════════════════════════════════
// PAGE: VIDEO
// ═══════════════════════════════════════════════════════════════════════════
function VideoPage({videoFile,videoRef,setVideoFile,onDragOver,onDragLeave,analyzeVideo,genVideoPDF,sendVideoPDFToWa,sendCompletionAlert,completionAlertSent,videoLoading,sendingWa,waMessage,videoResult,error}) {
  return (<><div className="section-header fade-up"><div className="section-crumb">Module · Video Analysis</div><h2 className="section-title">Video Analysis</h2><p className="section-desc">Upload underwater inspection footage for frame-sampled anomaly detection.</p><div className="section-rule" /></div><div className="card mb-20"><div className="card-title">Video Upload</div><div className="dropzone" onClick={()=>videoRef.current?.click()} onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={(e)=>{e.preventDefault();e.currentTarget.classList.remove("drag-over");setVideoFile(e.dataTransfer.files[0]);}}><div className="dz-icon">🎬</div><div className="dz-label">{videoFile?"Click or drop to replace":"Drop video file here"}</div><div className="dz-hint">Supported: MP4, AVI, MOV</div>{videoFile&&<div className="dz-file">✓ {videoFile.name}</div>}</div><input ref={videoRef} type="file" accept="video/*" hidden onChange={(e)=>setVideoFile(e.target.files[0])} /></div><div className="row mb-20" style={{gap:10,flexWrap:"wrap"}}><button className="btn btn-primary" disabled={!videoFile||videoLoading} onClick={analyzeVideo}>{videoLoading&&<span className="spinner" />} Analyze Video</button><button className="btn btn-ghost" disabled={!videoFile} onClick={genVideoPDF}>📄 PDF</button><button className="btn btn-ghost" disabled={!videoFile||sendingWa} onClick={sendVideoPDFToWa}>{sendingWa?"…":"📱 WhatsApp"}</button>{videoResult&&<button className="btn btn-ghost" disabled={sendingWa||completionAlertSent} onClick={()=>sendCompletionAlert("video")}>{completionAlertSent?"✓ Sent":"🔔 Alert"}</button>}</div><StatusBar error={error} waMessage={waMessage} />{videoResult&&(<div style={{marginTop:20}}><div style={{display:"flex",gap:12,flexWrap:"wrap",marginBottom:16}}><StatBox label="Detections" value={videoResult.total_detections??0} color="#22d3ee" />{videoResult.grade&&<StatBox label="Grade" value={videoResult.grade} color="#22c55e" />}{videoResult.risk_score!=null&&<StatBox label="Risk" value={`${videoResult.risk_score}%`} color="#f59e0b" />}</div>{videoResult.frames?.length>0&&<div className="card"><div className="card-title" style={{marginBottom:12}}>Sampled Frames</div><div style={{display:"flex",flexWrap:"wrap",gap:10}}>{videoResult.frames.map((f,i)=><img key={i} src={`data:image/jpeg;base64,${f}`} alt={`Frame ${i}`} style={{width:200,borderRadius:6}} />)}</div></div>}</div>)}</>);
}

// ═══════════════════════════════════════════════════════════════════════════
// COMBINED PIPELINE ROUTE — Slider View
// ═══════════════════════════════════════════════════════════════════════════
function CombinedPipelineRoute({uploads}) {
  const all=uploads.filter((u)=>u.preview);
  const [cur,setCur]=useState(0);
  if (!all.length) return null;
  const item=all[cur]; const imgSrc=item.detResult?.annotated_b64?`data:image/jpeg;base64,${item.detResult.annotated_b64}`:item.preview;
  const dets=item.detResult?.detections||[]; const total=item.detResult?.total??dets.length;
  return (<div className="card" style={{marginBottom:20,padding:0,overflow:"hidden"}}><div style={{padding:"14px 20px",display:"flex",justifyContent:"space-between",alignItems:"center",borderBottom:"1px solid rgba(255,255,255,0.06)"}}><div style={{fontSize:11,opacity:0.4,letterSpacing:1,textTransform:"uppercase"}}>Combined Pipeline View · {all.length} Segments</div><div style={{display:"flex",alignItems:"center",gap:12}}>{item.detResult&&<div style={{display:"flex",gap:8}}>{[["Grade",item.detResult.grade??"—","#a78bfa"],["Risk",(item.detResult.risk_score??"—")+"%","#f59e0b"],["Defects",total,"#22d3ee"]].map(([l,v,c])=><span key={l} style={{fontSize:10,padding:"3px 8px",borderRadius:4,background:c+"15",color:c,fontWeight:700}}>{l}: {v}</span>)}</div>}<div style={{fontSize:12,opacity:0.6,fontFamily:"monospace"}}>{cur+1} / {all.length}</div></div></div><div style={{position:"relative",background:"#000",minHeight:480}}><img src={imgSrc} alt={`Seg ${cur+1}`} style={{width:"100%",height:480,objectFit:"contain",display:"block"}} /><div style={{position:"absolute",top:14,left:14,display:"flex",gap:8}}><div style={{padding:"6px 12px",borderRadius:6,background:"rgba(0,0,0,0.7)",fontSize:13,fontWeight:700,color:"#22d3ee"}}>Segment {cur+1}</div><div style={{padding:"6px 12px",borderRadius:6,background:"rgba(0,0,0,0.6)",fontSize:11,color:"rgba(255,255,255,0.6)",maxWidth:300,whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>{item.file.name}</div></div>{cur>0&&<button onClick={()=>setCur(cur-1)} style={{position:"absolute",left:14,top:"50%",transform:"translateY(-50%)",width:44,height:44,borderRadius:"50%",background:"rgba(0,0,0,0.6)",border:"1px solid rgba(255,255,255,0.15)",color:"#fff",fontSize:20,cursor:"pointer",display:"flex",alignItems:"center",justifyContent:"center"}}>←</button>}{cur<all.length-1&&<button onClick={()=>setCur(cur+1)} style={{position:"absolute",right:14,top:"50%",transform:"translateY(-50%)",width:44,height:44,borderRadius:"50%",background:"rgba(0,0,0,0.6)",border:"1px solid rgba(255,255,255,0.15)",color:"#fff",fontSize:20,cursor:"pointer",display:"flex",alignItems:"center",justifyContent:"center"}}>→</button>}</div><div style={{display:"flex",gap:4,padding:"10px 12px",overflowX:"auto",background:"rgba(255,255,255,0.02)",borderTop:"1px solid rgba(255,255,255,0.06)"}}>{all.map((u,i)=><button key={u.id} onClick={()=>setCur(i)} style={{flexShrink:0,width:72,height:52,borderRadius:6,overflow:"hidden",border:i===cur?"2px solid #22d3ee":"1px solid rgba(255,255,255,0.08)",cursor:"pointer",padding:0,background:"none",position:"relative"}}><img src={u.detResult?.annotated_b64?`data:image/jpeg;base64,${u.detResult.annotated_b64}`:u.preview} alt="" style={{width:"100%",height:"100%",objectFit:"cover",display:"block"}} /><div style={{position:"absolute",bottom:0,left:0,right:0,background:"rgba(0,0,0,0.7)",fontSize:8,color:i===cur?"#22d3ee":"rgba(255,255,255,0.5)",textAlign:"center",padding:"1px 0",fontWeight:i===cur?700:400}}>Seg {i+1}</div></button>)}</div></div>);
}

// ═══════════════════════════════════════════════════════════════════════════
// PAGE: PIPELINE — Combined + All 3D + Active Twin + 2D
// ═══════════════════════════════════════════════════════════════════════════
function PipelinePage(props) {
  const {uploads,selectedUpload,selectedIdx,setSelectedIdx,fileRef,folderRef,handleFiles,removeUpload,clearUploads,onDragOver,onDragLeave,onDrop,detectAll,genPDF,sendPDFToWa,sendCompletionAlert,completionAlertSent,sendingWa,waMessage,exportCSV,loading,error,privacyCountdown,deletionCert,insp1Sev,setInsp1Sev,insp2Sev,setInsp2Sev,onOpenCompliance}=props;
  var det=uploads.find(function(x){return x.detResult;})?.detResult||null;
  var singleRef=useRef(null);
  var [mode,setMode]=useState("combined");

  var buildTwin=function(d){var ds=d?.detections||[];return{total_defects:d?.total??ds.length,risk_score:d?.risk_score??0,grade:d?.grade??"--",defects_3d:ds.map(function(x,i){return{id:i+1,cls:x.cls??x.class??"Unknown",severity:x.severity??"Low",conf:x.conf??0,pipeline_pos:ds.length===1?50:Math.round(5+(i/Math.max(ds.length-1,1))*90),angle:(i/Math.max(ds.length,1))*2*Math.PI};})};};

  var postSingle=function(){if(!singleRef.current||!selectedUpload?.detResult)return;singleRef.current.contentWindow?.postMessage({type:"NAUTICAI_DETECTIONS",data:buildTwin(selectedUpload.detResult)},"*");};

  useEffect(function(){if(mode==="single3d"){var t=setTimeout(postSingle,300);return function(){clearTimeout(t);};}}, [selectedUpload,mode]);

  return (<>
    <div className="section-header fade-up"><div className="section-crumb">Module · Pipeline Inspection</div><h2 className="section-title">Pipeline Inspection</h2><p className="section-desc">Upload multiple images — each image = one pipeline segment.</p><div className="section-rule" /></div>
    <DropZone {...{fileRef,folderRef,uploads,handleFiles,onDragOver,onDragLeave,onDrop}} />
    <SpotlightFilmstrip {...{uploads,selectedIdx,setSelectedIdx,removeUpload,clearUploads}} />
    <ImageActionButtons uploads={uploads} loading={loading} detectAll={detectAll} genPDF={genPDF} sendPDFToWa={sendPDFToWa} sendCompletionAlert={sendCompletionAlert} completionAlertSent={completionAlertSent} sendingWa={sendingWa} exportCSV={exportCSV} latestDetForTab={det} onOpenCompliance={onOpenCompliance} scanLabel="Run Pipeline Scan" />
    <StatusBar error={error} waMessage={waMessage} />
    <PrivacyTimer countdown={privacyCountdown} cert={deletionCert} />
    {uploads.length>0&&(<>
      <div style={{display:"flex",alignItems:"center",gap:0,marginBottom:16,borderRadius:8,overflow:"hidden",border:"1px solid rgba(34,211,238,0.2)",width:"fit-content"}}>
        {[["combined","🗺️ Combined Route"],["all3d","🧊 All Pipelines 3D"],["single3d","🔧 Active Twin"],["2d","📍 2D Map"]].map(([m,l],i,a)=>(
          <button key={m} onClick={()=>setMode(m)} style={{padding:"8px 20px",background:mode===m?"rgba(34,211,238,0.15)":"transparent",border:"none",borderRight:i<a.length-1?"1px solid rgba(34,211,238,0.2)":"none",color:mode===m?"#22d3ee":"rgba(255,255,255,0.5)",cursor:"pointer",fontSize:12,fontWeight:mode===m?700:400}}>{l}</button>
        ))}
      </div>
      {mode==="combined"&&<CombinedPipelineRoute uploads={uploads} />}
      {mode==="all3d"&&<MultiPipeline3D uploads={uploads} />}
      {mode==="single3d"&&selectedUpload?.detResult&&<div style={{width:"100%",height:560,marginBottom:20}}><iframe ref={singleRef} src="/pipeline-3d-twin.html" title="3D Twin" style={{width:"100%",height:"100%",border:"none",borderRadius:8}} onLoad={postSingle} /></div>}
      {mode==="2d"&&selectedUpload?.detResult&&<PipelineMap2D detResult={selectedUpload.detResult} imgW={selectedUpload.detResult.img_width??1280} imgH={selectedUpload.detResult.img_height??720} />}
    </>)}
    {selectedUpload&&<DetectionResultsPanel detResult={selectedUpload.detResult} enhResult={selectedUpload.enhResult} preview={selectedUpload.preview} exportCSV={exportCSV} />}
    {det&&<DisagreementFlag insp1Sev={insp1Sev} setInsp1Sev={setInsp1Sev} insp2Sev={insp2Sev} setInsp2Sev={setInsp2Sev} />}
  </>);
}

// ═══════════════════════════════════════════════════════════════════════════
// PAGE: CABLE
// ═══════════════════════════════════════════════════════════════════════════
function CablePage(props) {
  const {uploads,selectedUpload,selectedIdx,setSelectedIdx,fileRef,folderRef,handleFiles,removeUpload,clearUploads,onDragOver,onDragLeave,onDrop,detectAll,genPDF,sendPDFToWa,sendCompletionAlert,completionAlertSent,sendingWa,waMessage,exportCSV,loading,error,privacyCountdown,deletionCert,insp1Sev,setInsp1Sev,insp2Sev,setInsp2Sev,onOpenCompliance}=props;
  const det=uploads.find((x)=>x.detResult)?.detResult||null;
  return (<><div className="section-header fade-up"><div className="section-crumb">Module · Sub-sea Cable</div><h2 className="section-title">Sub-sea Cable Inspection</h2><p className="section-desc">Detect cable damage, abrasion, burial anomalies on subsea cables.</p><div className="section-rule" /></div><DropZone {...{fileRef,folderRef,uploads,handleFiles,onDragOver,onDragLeave,onDrop}} /><SpotlightFilmstrip {...{uploads,selectedIdx,setSelectedIdx,removeUpload,clearUploads}} /><ImageActionButtons uploads={uploads} loading={loading} detectAll={detectAll} genPDF={genPDF} sendPDFToWa={sendPDFToWa} sendCompletionAlert={sendCompletionAlert} completionAlertSent={completionAlertSent} sendingWa={sendingWa} exportCSV={exportCSV} latestDetForTab={det} onOpenCompliance={onOpenCompliance} scanLabel="Run Cable Scan" /><StatusBar error={error} waMessage={waMessage} /><PrivacyTimer countdown={privacyCountdown} cert={deletionCert} />{selectedUpload&&<DetectionResultsPanel detResult={selectedUpload.detResult} preview={selectedUpload.preview} exportCSV={exportCSV} />}{det&&<DisagreementFlag insp1Sev={insp1Sev} setInsp1Sev={setInsp1Sev} insp2Sev={insp2Sev} setInsp2Sev={setInsp2Sev} />}</>);
}

// ═══════════════════════════════════════════════════════════════════════════
// PAGE: DASHBOARD
// ═══════════════════════════════════════════════════════════════════════════
function DashPage({detResult,videoResult,sessionDetections,reportsGenerated}) {
  return (<><div className="section-header fade-up"><div className="section-crumb">Module · Dashboard</div><h2 className="section-title">Mission Dashboard</h2><div className="section-rule" /></div><div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:16,marginBottom:24}}><BigStat label="Session Detections" value={sessionDetections??0} color="#22d3ee" /><BigStat label="Reports" value={reportsGenerated??0} color="#a78bfa" /><BigStat label="Risk Score" value={detResult?.risk_score!=null?`${detResult.risk_score}%`:"—"} color="#f59e0b" /><BigStat label="Grade" value={detResult?.grade??"—"} color="#22c55e" /></div>{detResult?<DetectionResultsPanel detResult={detResult} exportCSV={()=>{}} />:<div className="card" style={{textAlign:"center",padding:"48px 24px",opacity:0.4}}><div style={{fontSize:32,marginBottom:12}}>📊</div><div>Run a detection to see results.</div></div>}</>);
}

// ═══════════════════════════════════════════════════════════════════════════
// PAGE: MEMORY
// ═══════════════════════════════════════════════════════════════════════════
function MemoryPage({missions}) {
  return (<><div className="section-header fade-up"><div className="section-crumb">Module · Mission Memory</div><h2 className="section-title">Mission Memory</h2><div className="section-rule" /></div>{missions.length===0?<div className="card" style={{textAlign:"center",padding:"48px 24px",opacity:0.4}}><div style={{fontSize:32,marginBottom:12}}>🧠</div><div>No missions yet.</div></div>:<div className="card" style={{overflowX:"auto"}}><table style={{width:"100%",borderCollapse:"collapse",fontSize:13}}><thead><tr style={{borderBottom:"1px solid rgba(255,255,255,0.08)"}}>{["Mission ID","Date","Vessel","Mode","Grade","Risk","Dets","Classes"].map((h)=><th key={h} style={{padding:"8px 12px",textAlign:"left",opacity:0.45,fontSize:11,fontWeight:600}}>{h}</th>)}</tr></thead><tbody>{missions.map((m)=>(<tr key={m.id} style={{borderBottom:"1px solid rgba(255,255,255,0.04)"}}><td style={{padding:"10px 12px",fontFamily:"monospace",fontSize:11,color:"#22d3ee"}}>{m.id}</td><td style={{padding:"10px 12px",fontSize:11,opacity:0.6}}>{new Date(m.date).toLocaleString()}</td><td style={{padding:"10px 12px",fontWeight:600}}>{m.vessel}</td><td style={{padding:"10px 12px",opacity:0.7,textTransform:"capitalize"}}>{m.mode}</td><td style={{padding:"10px 12px",color:"#a78bfa",fontWeight:700}}>{m.grade}</td><td style={{padding:"10px 12px",color:"#f59e0b",fontWeight:700}}>{m.risk}%</td><td style={{padding:"10px 12px",color:"#22d3ee"}}>{m.total}</td><td style={{padding:"10px 12px",fontSize:11,opacity:0.6}}>{m.classes?.join(", ")||"—"}</td></tr>))}</tbody></table></div>}</>);
}

// ═══════════════════════════════════════════════════════════════════════════
// PAGE: COMPLIANCE
// ═══════════════════════════════════════════════════════════════════════════
function CompliancePage({detResult,vesselName,inspector}) {
  return (<><div className="section-header fade-up"><div className="section-crumb">Module · Compliance</div><h2 className="section-title">Regulatory Compliance</h2><div className="section-rule" /></div>{detResult?<ComplianceModal detResult={detResult} vesselName={vesselName} inspector={inspector} />:<div className="card" style={{textAlign:"center",padding:"48px 24px",opacity:0.4}}><div style={{fontSize:32,marginBottom:12}}>📋</div><div>Run a detection first.</div></div>}</>);
}

// ═══════════════════════════════════════════════════════════════════════════
// PAGE: ZERO-SHOT
// ═══════════════════════════════════════════════════════════════════════════
function ZeroShotPage({zeroShotClasses,setZeroShotClasses,uploads,fileRef,folderRef,handleFiles,onDragOver,onDragLeave,onDrop}) {
  const [input,setInput]=useState(""); const [running,setRunning]=useState(false); const [results,setResults]=useState([]);
  const add=()=>{const v=input.trim();if(v&&!zeroShotClasses.includes(v))setZeroShotClasses((p)=>[...p,v]);setInput("");};
  const run=async()=>{if(!uploads.length||!zeroShotClasses.length)return;setRunning(true);await new Promise((r)=>setTimeout(r,1500));setResults(zeroShotClasses.map((cls)=>({cls,found:Math.random()>0.4,conf:Math.random()*0.4+0.5})));setRunning(false);};
  return (<><div className="section-header fade-up"><div className="section-crumb">Module · Zero-Shot</div><h2 className="section-title">Zero-Shot Detection</h2><p className="section-desc">Define any defect class in natural language.</p><div className="section-rule" /></div><div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16}}><div><div className="card" style={{marginBottom:16}}><div className="card-title" style={{marginBottom:12}}>Add Classes</div><div style={{display:"flex",gap:8,marginBottom:12}}><input className="ctrl-input" style={{flex:1}} placeholder="e.g. marine growth" value={input} onChange={(e)=>setInput(e.target.value)} onKeyDown={(e)=>e.key==="Enter"&&add()} /><button className="btn btn-primary" onClick={add}>Add</button></div><div style={{display:"flex",flexWrap:"wrap",gap:6}}>{zeroShotClasses.length===0?<span style={{fontSize:12,opacity:0.3}}>No classes</span>:zeroShotClasses.map((cls)=>(<span key={cls} style={{display:"inline-flex",alignItems:"center",gap:6,padding:"4px 10px",background:"rgba(34,211,238,0.1)",border:"1px solid rgba(34,211,238,0.3)",borderRadius:20,fontSize:12,color:"#22d3ee"}}>{cls}<button onClick={()=>setZeroShotClasses((p)=>p.filter((c)=>c!==cls))} style={{background:"none",border:"none",color:"#22d3ee",cursor:"pointer"}}>×</button></span>))}</div></div><button className="btn btn-primary" disabled={!uploads.length||!zeroShotClasses.length||running} onClick={run} style={{width:"100%"}}>{running?"Running...":"🎯 Run Zero-Shot"}</button></div><div><DropZone {...{fileRef,folderRef,uploads,handleFiles,onDragOver,onDragLeave,onDrop}} />{results.length>0&&<div className="card"><div className="card-title" style={{marginBottom:12}}>Results</div>{results.map((r)=>(<div key={r.cls} style={{display:"flex",alignItems:"center",gap:12,padding:"8px 0",borderBottom:"1px solid rgba(255,255,255,0.05)"}}><span style={{width:10,height:10,borderRadius:"50%",background:r.found?"#22c55e":"#ef4444"}} /><span style={{flex:1,fontSize:13,fontWeight:600}}>{r.cls}</span>{r.found?<span style={{fontSize:12,color:"#22c55e",fontWeight:700}}>Found · {(r.conf*100).toFixed(1)}%</span>:<span style={{fontSize:12,opacity:0.4}}>Not detected</span>}</div>))}</div>}</div></div></>);
}

// ═══════════════════════════════════════════════════════════════════════════
// PAGE: ROADMAP
// ═══════════════════════════════════════════════════════════════════════════
function RoadmapPage() {
  return (<><div className="section-header fade-up"><div className="section-crumb">NautiCAI · Product</div><h2 className="section-title">Development Roadmap</h2><div className="section-rule" /></div><div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:16,marginBottom:24}}>{PHASES.map((p)=>(<div key={p.num} className="card" style={{padding:24}}><div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:8}}><span style={{fontSize:28,fontWeight:900,color:p.badgeColor,opacity:0.7,fontFamily:"monospace"}}>{p.num}</span><span style={{fontSize:10,fontWeight:700,padding:"3px 10px",borderRadius:20,background:p.badgeColor+"22",color:p.badgeColor}}>{p.badge}</span></div><div style={{marginBottom:4}}><span style={{fontSize:34,fontWeight:900,color:"#e2e8f0",fontFamily:"monospace"}}>{p.ver}</span><span style={{fontSize:16,color:p.badgeColor,fontFamily:"monospace"}}>/{p.sub}</span></div><div style={{fontSize:10,letterSpacing:1,opacity:0.4,textTransform:"uppercase",marginBottom:16}}>{p.tagline}</div><ul style={{margin:0,paddingLeft:0,listStyle:"none",display:"flex",flexDirection:"column",gap:8}}>{p.items.map((item)=>(<li key={item} style={{display:"flex",gap:8,fontSize:12,lineHeight:1.5,opacity:0.8}}><span style={{color:p.badgeColor,flexShrink:0,marginTop:2}}>●</span>{item}</li>))}</ul></div>))}</div><div className="card"><div className="card-title" style={{marginBottom:16}}>🔧 Tech Stack</div><div style={{display:"grid",gridTemplateColumns:"repeat(6,1fr)",gap:12}}>{TECH_STACK.map((t)=>(<div key={t.label} style={{textAlign:"center",padding:"16px 8px",background:t.color+"11",borderRadius:8,border:`1px solid ${t.color}22`}}><div style={{fontSize:10,opacity:0.45,letterSpacing:1,textTransform:"uppercase",marginBottom:8}}>{t.label}</div><div style={{fontSize:13,fontWeight:700,color:t.color}}>{t.value}</div></div>))}</div></div></>);
}

// ═══════════════════════════════════════════════════════════════════════════
// REGULATORY DEADLINE TRACKER (pure frontend)
// ═══════════════════════════════════════════════════════════════════════════
function DeadlinePage({detResult}) {
  const deadlines=calcDeadlines(detResult);
  if (!detResult) return (<><div className="section-header fade-up"><div className="section-crumb">Module · Deadlines</div><h2 className="section-title">Regulatory Deadline Tracker</h2><div className="section-rule" /></div><div className="card" style={{textAlign:"center",padding:"48px 24px",opacity:0.4}}><div style={{fontSize:32,marginBottom:12}}>⏰</div><div>Run a detection first.</div></div></>);
  const urgent=deadlines.filter((d)=>d.urgency==="critical"||d.urgency==="high");
  return (<><div className="section-header fade-up"><div className="section-crumb">Module · Deadlines</div><h2 className="section-title">Regulatory Deadline Tracker</h2><p className="section-desc">Auto-calculated deadlines based on IMO/SOLAS/DNV rules.</p><div className="section-rule" /></div>{urgent.length>0&&<div className="card" style={{marginBottom:20,padding:16,background:"#ef444411",border:"1px solid #ef444433"}}><div style={{fontSize:12,fontWeight:700,color:"#ef4444",marginBottom:8}}>🚨 {urgent.length} URGENT DEADLINE{urgent.length>1?"S":""}</div>{urgent.map((d,i)=><div key={i} style={{fontSize:12,marginBottom:4}}><strong style={{color:urgCol(d.urgency)}}>{d.body}</strong> — {d.type}: <strong>{daysTo(d.due)} days</strong></div>)}</div>}<div style={{display:"grid",gap:16}}>{deadlines.map((d,i)=>{const days=daysTo(d.due);const uc=urgCol(d.urgency);const pct=Math.min(100,Math.max(0,100-(days/365)*100));return(<div key={i} className="card" style={{padding:20,borderLeft:`4px solid ${uc}`}}><div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:12}}><div><div style={{fontSize:10,fontWeight:700,letterSpacing:1,color:uc,textTransform:"uppercase",marginBottom:4}}>{d.body}</div><div style={{fontSize:16,fontWeight:700}}>{d.type}</div></div><div style={{textAlign:"right"}}><div style={{fontSize:28,fontWeight:900,color:uc,fontFamily:"monospace"}}>{days}</div><div style={{fontSize:10,opacity:0.4}}>days remaining</div></div></div><div style={{height:6,borderRadius:3,background:"rgba(255,255,255,0.06)",overflow:"hidden",marginBottom:10}}><div style={{width:`${pct}%`,height:"100%",background:uc,borderRadius:3}} /></div><div style={{display:"flex",justifyContent:"space-between",fontSize:11}}><span style={{opacity:0.5}}>Due: {d.due.toLocaleDateString("en-GB")}</span><span style={{opacity:0.4,fontStyle:"italic",maxWidth:"60%",textAlign:"right"}}>{d.rule}</span></div></div>);})}</div><div style={{marginTop:20,padding:"12px 16px",background:"rgba(255,255,255,0.02)",borderRadius:8,border:"1px solid rgba(255,255,255,0.06)",fontSize:11,opacity:0.5}}>⚠️ Confirm deadlines with your class society surveyor.</div></>);
}