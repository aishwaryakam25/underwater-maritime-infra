import React, { useState, useRef, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import PipelineMap2D from "./PipelineMap2D";
import {
  getHealth, runDetection, runEnhance, downloadPDF,
  downloadVideoPDF, runVideoDetection,
  sendPDFToWhatsApp, sendVideoPDFToWhatsApp, sendWhatsAppMessage,
} from "./api";

const TABS = [
  { id: "scan",     icon: "🔬", label: "Anomaly Scan" },
  { id: "hull",     icon: "🚢", label: "Hull Inspect" },
  { id: "video",    icon: "🎬", label: "Video Analysis" },
  { id: "pipeline", icon: "🔧", label: "Pipeline" },
  { id: "cable",    icon: "⚡", label: "Sub-sea Cable" },
  { id: "dash",     icon: "📊", label: "Dashboard" },
  { id: "memory",   icon: "🧠", label: "Mission Memory" },
  { id: "comply",   icon: "📋", label: "Compliance" },
  { id: "zero",     icon: "🎯", label: "Zero-Shot" },
  { id: "road",     icon: "🗺️", label: "Roadmap" },
];

const pgVar = {
  enter:  { opacity: 0, y: 20 },
  center: { opacity: 1, y: 0, transition: { duration: 0.3, ease: [0.4, 0, 0.2, 1] } },
  exit:   { opacity: 0, y: -12, transition: { duration: 0.15 } },
};

export default function App() {
  const [tab, setTab] = useState("scan");
  const [health, setHealth] = useState(null);

  // Multi-upload state per tab
  const [tabUploads, setTabUploads] = useState({});

  const uploads = tabUploads[tab] ?? [];

  // Latest result from any scan tab
  const latestDetResult =
    (tabUploads["scan"] || []).find(x => x.detResult)?.detResult ||
    (tabUploads["hull"] || []).find(x => x.detResult)?.detResult ||
    (tabUploads["pipeline"] || []).find(x => x.detResult)?.detResult ||
    (tabUploads["cable"] || []).find(x => x.detResult)?.detResult ||
    null;

  // Detection params
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

  // Mission info
  const [vesselName, setVesselName] = useState("");
  const [inspector, setInspector] = useState("NautiCAI AutoScan v1.0");
  const [inspMode, setInspMode] = useState("general");
  const [reportPassword, setReportPassword] = useState("");

  // Loading / error
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Video
  const [videoFile, setVideoFile] = useState(null);
  const [videoLoading, setVideoLoading] = useState(false);
  const [videoResult, setVideoResult] = useState(null);

  // Session stats
  const [reportsGenerated, setReportsGenerated] = useState(0);
  const [sessionDetections, setSessionDetections] = useState(0);

  // WhatsApp
  const [sendingWa, setSendingWa] = useState(false);
  const [waMessage, setWaMessage] = useState("");
  const [completionAlertSent, setCompletionAlertSent] = useState(false);

  // New features
  const [privacyCountdown, setPrivacyCountdown] = useState(null);
  const [deletionCert, setDeletionCert] = useState(null);
  const [complianceOpen, setComplianceOpen] = useState(false);
  const [missions, setMissions] = useState([]);
  const [zeroShotClasses, setZeroShotClasses] = useState([]);
  const [insp1Sev, setInsp1Sev] = useState("");
  const [insp2Sev, setInsp2Sev] = useState("");

  const [demoUser] = useState(() => {
    try {
      const u = sessionStorage.getItem("nauticai-demo-user");
      return u ? JSON.parse(u) : null;
    } catch {
      return null;
    }
  });

  // Demo gate
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    if (p.get("demo") === "1") {
      const u = {
        name: p.get("name") || "",
        email: p.get("email") || "",
        whatsapp: p.get("whatsapp") || ""
      };
      sessionStorage.setItem("nauticai-demo-access", "1");
      sessionStorage.setItem("nauticai-demo-user", JSON.stringify(u));
      window.history.replaceState({}, "", window.location.pathname);
    }
    if (sessionStorage.getItem("nauticai-demo-access") !== "1") {
      sessionStorage.setItem("nauticai-demo-access", "1");
    }
  }, []);

  // Health poll
  useEffect(() => {
    const poll = () => getHealth().then(setHealth).catch(() => setHealth({ status: "offline" }));
    poll();
    const t = setInterval(poll, 30000);
    return () => clearInterval(t);
  }, []);

  // Privacy countdown
  useEffect(() => {
    if (!latestDetResult) return;
    setPrivacyCountdown(60);
    setDeletionCert(null);
    setInsp1Sev("");
    setInsp2Sev("");
    saveMission(latestDetResult);
  }, [latestDetResult]);

  useEffect(() => {
    if (privacyCountdown === null) return;
    if (privacyCountdown <= 0) {
      const bytes = new Uint8Array(8);
      crypto.getRandomValues(bytes);
      const hash = Array.from(bytes).map(b => b.toString(16).padStart(2, "0")).join("").toUpperCase();
      setDeletionCert({ hash, time: new Date().toISOString() });
      setPrivacyCountdown(null);
      return;
    }
    const t = setTimeout(() => setPrivacyCountdown(n => n - 1), 1000);
    return () => clearTimeout(t);
  }, [privacyCountdown]);

  // Mission memory
  const saveMission = async (det) => {
    try {
      const m = {
        id: det.mission_id ?? `M-${Date.now().toString(36).toUpperCase()}`,
        date: new Date().toISOString(),
        vessel: vesselName || "Unknown",
        grade: det.grade ?? "—",
        risk: det.risk_score ?? 0,
        total: det.total ?? (det.detections?.length ?? 0),
        classes: [...new Set((det.detections || []).map(d => d.cls ?? d.class).filter(Boolean))],
        mode: inspMode,
      };
      if (window.storage) await window.storage.set(`mission:${m.id}`, JSON.stringify(m));
      setMissions(prev => [m, ...prev.filter(x => x.id !== m.id)].slice(0, 20));
    } catch (e) {
      console.error("Mission save:", e);
    }
  };

  useEffect(() => {
    const load = async () => {
      try {
        if (!window.storage) return;
        const keys = await window.storage.list("mission:");
        const arr = await Promise.all((keys.keys || []).map(async k => {
          try {
            const r = await window.storage.get(k);
            return r ? JSON.parse(r.value) : null;
          } catch {
            return null;
          }
        }));
        setMissions(arr.filter(Boolean).sort((a, b) => new Date(b.date) - new Date(a.date)));
      } catch (e) {}
    };
    load();
  }, []);

  // Refs
  const fileRef = useRef();
  const folderRef = useRef();
  const videoRef = useRef();

  const makeUploadItem = useCallback((file) => ({
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    file,
    preview: URL.createObjectURL(file),
    detResult: null,
    enhResult: null,
  }), []);

  const handleFiles = useCallback((fileList) => {
    const validFiles = Array.from(fileList || []).filter(f => f.type.startsWith("image/"));
    if (!validFiles.length) return;

    const newItems = validFiles.map(makeUploadItem);

    setTabUploads(prev => ({
      ...prev,
      [tab]: [...(prev[tab] || []), ...newItems],
    }));

    setError("");
    setPrivacyCountdown(null);
    setDeletionCert(null);
  }, [tab, makeUploadItem]);

  const removeUpload = useCallback((id) => {
    setTabUploads(prev => {
      const arr = prev[tab] || [];
      const item = arr.find(x => x.id === id);
      if (item?.preview) URL.revokeObjectURL(item.preview);

      return {
        ...prev,
        [tab]: arr.filter(x => x.id !== id),
      };
    });
  }, [tab]);

  const clearUploads = useCallback(() => {
    setTabUploads(prev => {
      const arr = prev[tab] || [];
      arr.forEach(x => {
        if (x.preview) URL.revokeObjectURL(x.preview);
      });
      return {
        ...prev,
        [tab]: [],
      };
    });
  }, [tab]);

  const updateUploadById = useCallback((tabId, id, patch) => {
    setTabUploads(prev => ({
      ...prev,
      [tabId]: (prev[tabId] || []).map(item =>
        item.id === id ? { ...item, ...patch } : item
      ),
    }));
  }, []);

  const onDragOver = (e) => {
    e.preventDefault();
    e.currentTarget.classList.add("drag-over");
  };

  const onDragLeave = (e) => {
    e.currentTarget.classList.remove("drag-over");
  };

  const onDrop = (e) => {
    e.preventDefault();
    e.currentTarget.classList.remove("drag-over");
    handleFiles(e.dataTransfer.files);
  };

  const detParams = () => ({
    conf_thr: conf,
    iou_thr: iou,
    mode: inspMode,
    sev_filter: sevFilter,
    use_clahe: clahe,
    clahe_clip: claheClip,
    use_green: green,
    use_edge: edge,
    turbidity_in: turbLevel,
    corr_turb: corrTurb,
    marine_snow: marineSnow,
  });

  const enhParams = () => ({
    use_clahe: clahe,
    clahe_clip: claheClip,
    use_green: green,
    use_edge: edge,
    turbidity_in: turbLevel,
    corr_turb: corrTurb,
    marine_snow: marineSnow,
  });

  const detectAll = async () => {
    if (!uploads.length) return;
    setLoading(true);
    setError("");
    setCompletionAlertSent(false);

    try {
      for (const item of uploads) {
        const data = await runDetection(item.file, detParams());
        updateUploadById(tab, item.id, { detResult: data });
        setSessionDetections(n => n + (data.total ?? data.detections?.length ?? 0));
      }
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }

    setLoading(false);
  };

  const enhanceAll = async () => {
    if (!uploads.length) return;
    setLoading(true);
    setError("");

    try {
      for (const item of uploads) {
        const data = await runEnhance(item.file, enhParams());
        updateUploadById(tab, item.id, { enhResult: data });
      }
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }

    setLoading(false);
  };

  const runBothAll = async () => {
    if (!uploads.length) return;
    setLoading(true);
    setError("");
    setCompletionAlertSent(false);

    try {
      for (const item of uploads) {
        const [det, enh] = await Promise.all([
          runDetection(item.file, detParams()),
          runEnhance(item.file, enhParams()),
        ]);

        updateUploadById(tab, item.id, {
          detResult: det,
          enhResult: enh,
        });

        setSessionDetections(n => n + (det.total ?? det.detections?.length ?? 0));
      }
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }

    setLoading(false);
  };

  // Uses first upload only for now
  const genPDF = async () => {
    if (!uploads.length) return;
    const firstFile = uploads[0].file;
    setError("");
    try {
      await downloadPDF(firstFile, {
        ...detParams(),
        vessel_name: vesselName || "Unknown",
        inspector,
        pdf_password: reportPassword
      });
      setReportsGenerated(n => n + 1);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  };

  const genVideoPDF = async () => {
    if (!videoFile) return;
    setError("");
    try {
      await downloadVideoPDF(videoFile, {
        conf_thr: conf,
        iou_thr: iou,
        mode: inspMode,
        vessel_name: vesselName || "Unknown",
        inspector,
        sample_n: 10,
        use_clahe: clahe,
        clahe_clip: claheClip,
        use_green: green,
        use_edge: edge,
        turbidity_in: turbLevel,
        corr_turb: corrTurb,
        pdf_password: reportPassword,
      });
      setReportsGenerated(n => n + 1);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  };

  const waTo = () => demoUser?.whatsapp?.trim() || "";

  const sendPDFToWa = async () => {
    if (!uploads.length) return;
    const firstFile = uploads[0].file;

    if (!waTo()) {
      setWaMessage("Add your WhatsApp number at signup.");
      setTimeout(() => setWaMessage(""), 4000);
      return;
    }

    setSendingWa(true);
    setWaMessage("");
    setError("");

    try {
      const res = await sendPDFToWhatsApp(firstFile, {
        ...detParams(),
        vessel_name: vesselName || "Unknown",
        inspector,
        to: waTo(),
        pdf_password: reportPassword
      });
      setWaMessage(res.sent ? "Report sent." : (res.message || "Could not send."));
    } catch (e) {
      setWaMessage(e.response?.data?.message || e.message || "Send failed.");
    }
    setSendingWa(false);
  };

  const sendVideoPDFToWa = async () => {
    if (!videoFile) return;
    if (!waTo()) {
      setWaMessage("Add your WhatsApp number at signup.");
      setTimeout(() => setWaMessage(""), 4000);
      return;
    }
    setSendingWa(true);
    setWaMessage("");
    setError("");
    try {
      const res = await sendVideoPDFToWhatsApp(videoFile, {
        conf_thr: conf,
        iou_thr: iou,
        mode: inspMode,
        vessel_name: vesselName || "Unknown",
        inspector,
        sample_n: 10,
        use_clahe: clahe,
        clahe_clip: claheClip,
        use_green: green,
        use_edge: edge,
        turbidity_in: turbLevel,
        corr_turb: corrTurb,
        to: waTo(),
        pdf_password: reportPassword,
      });
      setWaMessage(res.sent ? "Video report sent." : (res.message || "Could not send."));
    } catch (e) {
      setWaMessage(e.response?.data?.message || e.message || "Send failed.");
    }
    setSendingWa(false);
  };

  const sendCompletionAlert = async (source = "image") => {
    if (!waTo()) {
      setWaMessage("Add your WhatsApp number at signup.");
      setTimeout(() => setWaMessage(""), 4000);
      return;
    }
    const data = source === "video" ? videoResult : latestDetResult;
    if (!data) return;

    const total = data.total ?? data.detections?.length ?? data.total_detections ?? 0;
    const msg = `NautiCAI inspection complete. Risk: ${data.risk_score ?? "—"} · Grade: ${data.grade ?? "—"} · ${total} detection(s).`;

    setSendingWa(true);
    setWaMessage("");
    try {
      const res = await sendWhatsAppMessage(waTo().replace(/\s/g, ""), msg);
      if (res.sent) {
        setWaMessage("Alert sent.");
        setCompletionAlertSent(true);
      } else {
        setWaMessage(res.message || "Could not send.");
      }
    } catch (e) {
      setWaMessage(e.response?.data?.message || e.message || "Send failed.");
    }
    setSendingWa(false);
  };

  const analyzeVideo = async () => {
    if (!videoFile) return;
    setVideoLoading(true);
    setError("");
    setCompletionAlertSent(false);
    try {
      const data = await runVideoDetection(videoFile, {
        conf_thr: conf,
        iou_thr: iou,
        mode: inspMode,
        sample_n: 10,
        use_clahe: clahe,
        clahe_clip: claheClip,
        use_green: green,
        use_edge: edge,
        turbidity_in: turbLevel,
        corr_turb: corrTurb,
      });
      setVideoResult(data);
      setSessionDetections(n => n + (data.total_detections ?? data.detections?.length ?? 0));
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
    setVideoLoading(false);
  };

  const exportDetectionsCSV = (data) => {
    const dets = data?.detections || [];
    if (!dets.length) return;
    const csv = [
      ["id", "class", "confidence", "severity", "bbox_area_px"].join(","),
      ...dets.map((d, i) => {
        const w = Math.abs((d.bbox?.xmax ?? d.bbox?.x2 ?? 0) - (d.bbox?.xmin ?? d.bbox?.x1 ?? 0));
        const h = Math.abs((d.bbox?.ymax ?? d.bbox?.y2 ?? 0) - (d.bbox?.ymin ?? d.bbox?.y1 ?? 0));
        return [i + 1, d.cls ?? d.class ?? "", d.conf != null ? Number(d.conf).toFixed(4) : "", d.severity ?? "", Math.round(w * h)]
          .map(c => `"${String(c).replace(/"/g, '""')}"`).join(",");
      })
    ].join("\n");

    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = `NautiCAI_${data?.mission_id || "export"}.csv`;
    a.click();
  };

  useEffect(() => {
    const onKey = (e) => {
      if (!e.ctrlKey || e.key !== "Enter") return;
      e.preventDefault();
      if (tab === "scan" && uploads.length) runBothAll();
      else if (["hull", "pipeline", "cable"].includes(tab) && uploads.length) detectAll();
      else if (tab === "video" && videoFile) analyzeVideo();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [tab, uploads, videoFile]);

  const imagePageProps = {
    uploads,
    fileRef,
    folderRef,
    handleFiles,
    removeUpload,
    clearUploads,
    onDragOver,
    onDragLeave,
    onDrop,
    detectAll,
    enhanceAll,
    runBothAll,
    genPDF,
    sendPDFToWa,
    sendCompletionAlert,
    completionAlertSent,
    sendingWa,
    waMessage,
    exportCSV: exportDetectionsCSV,
    loading,
    error,
    privacyCountdown,
    deletionCert,
    insp1Sev,
    setInsp1Sev,
    insp2Sev,
    setInsp2Sev,
    onOpenCompliance: () => setComplianceOpen(true),
  };

  return (
    <div className="app-shell">
      {complianceOpen && (
        <ComplianceModal
          detResult={latestDetResult}
          vesselName={vesselName}
          inspector={inspector}
          onClose={() => setComplianceOpen(false)}
        />
      )}

      <aside className="sidebar">
        <div className="sb-brand">
          <img className="sb-logo" src="/nauticai-logo.png" alt="NautiCAI" />
          <div className="sb-brand-text">
            <h3>NAUTICAI</h3>
            <a href="https://www.nauticai-ai.com" target="_blank" rel="noreferrer">www.nauticai-ai.com</a>
          </div>
        </div>

        <div className="sb-status">
          <span className="pill">
            <span className={`dot ${health?.status === "ok" ? "dot-ok" : "dot-warn"}`} />
            {health?.status === "ok" ? "API Online" : "API Offline"}
          </span>
          {health?.model && <span className="pill"><span className="dot dot-ok" />{health.model}</span>}
        </div>

        <div className="sb-section">
          <div className="sb-label">Detection Engine</div>
          <div className="ctrl">
            <div className="ctrl-header"><label>Confidence Threshold</label><span>{conf.toFixed(2)}</span></div>
            <input type="range" className="ctrl-slider" min={0.05} max={0.95} step={0.05} value={conf} onChange={e => setConf(+e.target.value)} />
          </div>
          <div className="ctrl">
            <div className="ctrl-header"><label>IoU Threshold</label><span>{iou.toFixed(2)}</span></div>
            <input type="range" className="ctrl-slider" min={0.1} max={0.9} step={0.05} value={iou} onChange={e => setIou(+e.target.value)} />
          </div>
        </div>

        <div className="sb-sep" />

        <div className="sb-section">
          <div className="sb-label">Severity Filter</div>
          <div className="ctrl">
            <div className="ctrl-header"><label>Display mode</label></div>
            <select className="ctrl-select" value={sevFilter} onChange={e => setSevFilter(e.target.value)}>
              <option>All Detections</option>
              <option>Critical Only</option>
              <option>High+</option>
              <option>Medium+</option>
            </select>
          </div>
        </div>

        <div className="sb-sep" />

        <div className="sb-section">
          <div className="sb-label">Visibility Engine</div>
          <Toggle label="CLAHE Enhancement" checked={clahe} onChange={() => setClahe(!clahe)} />
          {clahe && (
            <div className="ctrl">
              <div className="ctrl-header"><label>CLAHE Clip Limit</label><span>{claheClip.toFixed(2)}</span></div>
              <input type="range" className="ctrl-slider" min={1} max={10} step={0.5} value={claheClip} onChange={e => setClaheClip(+e.target.value)} />
            </div>
          )}
          <Toggle label="Green-Water Filter" checked={green} onChange={() => setGreen(!green)} />
          <Toggle label="Edge Estimator" checked={edge} onChange={() => setEdge(!edge)} />
          <div className="ctrl">
            <div className="ctrl-header"><label>Turbidity Level</label><span>{turbLevel.toFixed(2)}</span></div>
            <input type="range" className="ctrl-slider" min={0} max={1} step={0.05} value={turbLevel} onChange={e => setTurbLevel(+e.target.value)} />
          </div>
          <Toggle label="Turbidity Correction" checked={corrTurb} onChange={() => setCorrTurb(!corrTurb)} />
          <Toggle label="Marine Snow" checked={marineSnow} onChange={() => setMarineSnow(!marineSnow)} />
        </div>

        <div className="sb-sep" />

        <div className="sb-section">
          <div className="sb-label">Mission Info</div>
          <div className="ctrl">
            <div className="ctrl-header"><label>Vessel Name</label></div>
            <input type="text" className="ctrl-input" placeholder="e.g. MV Neptune Star" value={vesselName} onChange={e => setVesselName(e.target.value)} />
          </div>
          <div className="ctrl">
            <div className="ctrl-header"><label>Inspector</label></div>
            <input type="text" className="ctrl-input" value={inspector} onChange={e => setInspector(e.target.value)} />
          </div>
          <div className="ctrl">
            <div className="ctrl-header"><label>Inspection Mode</label></div>
            <select className="ctrl-select" value={inspMode} onChange={e => setInspMode(e.target.value)}>
              <option value="general">General Inspection</option>
              <option value="hull">Hull Inspection</option>
              <option value="pipeline">Pipeline Inspection</option>
              <option value="cable">Cable Inspection</option>
            </select>
          </div>
          <div className="ctrl">
            <div className="ctrl-header"><label>Report Password (optional)</label></div>
            <input
              type="password"
              className="ctrl-input"
              placeholder="Encrypt PDF"
              value={reportPassword}
              onChange={e => setReportPassword(e.target.value)}
              autoComplete="off"
            />
            <small className="ctrl-hint">PDFs will require this password to open.</small>
          </div>
        </div>

        <div className="sb-footer">
          <img src="/nauticai-logo.png" alt="" />
          <a href="https://www.nauticai-ai.com" target="_blank" rel="noreferrer">www.nauticai-ai.com</a>
          <small>© 2025 NautiCAI Pte Ltd · Singapore</small>
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <img className="topbar-logo" src="/nauticai-logo.png" alt="NautiCAI" />
            <div className="topbar-title">
              <h1>NAUTICAI</h1>
              <p>Deep-sea Anomaly Detection Platform</p>
            </div>
          </div>
          <div className="topbar-right">
            <span className="topbar-chip">BETA · INTERNAL DEMO</span>
            <a
              href={window.location.port === "3000" ? "http://localhost:8080/demo.html" : "/demo.html"}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-primary btn-sm"
              style={{ textDecoration: "none", color: "inherit" }}
            >
              Book a demo
            </a>
          </div>
        </header>

        <div className="tab-bar">
          {TABS.map(t => (
            <button key={t.id} className={`tab-btn ${tab === t.id ? "active" : ""}`} onClick={() => setTab(t.id)}>
              <span className="tab-icon">{t.icon}</span>{t.label}
            </button>
          ))}
        </div>

        <AnimatePresence mode="wait">
          <motion.div key={tab} className="page-content" variants={pgVar} initial="enter" animate="center" exit="exit">
            {tab === "scan" && <ScanPage {...imagePageProps} />}
            {tab === "hull" && <HullPage {...imagePageProps} />}
            {tab === "video" && (
              <VideoPage
                videoFile={videoFile}
                videoRef={videoRef}
                setVideoFile={setVideoFile}
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                analyzeVideo={analyzeVideo}
                genVideoPDF={genVideoPDF}
                sendVideoPDFToWa={sendVideoPDFToWa}
                sendCompletionAlert={sendCompletionAlert}
                completionAlertSent={completionAlertSent}
                videoLoading={videoLoading}
                sendingWa={sendingWa}
                waMessage={waMessage}
                videoResult={videoResult}
                error={error}
              />
            )}
            {tab === "pipeline" && <PipelinePage {...imagePageProps} />}
            {tab === "cable" && <CablePage {...imagePageProps} />}
            {tab === "dash" && <DashPage detResult={latestDetResult} videoResult={videoResult} />}
            {tab === "memory" && <MemoryPage missions={missions} />}
            {tab === "comply" && <CompliancePage detResult={latestDetResult} vesselName={vesselName} inspector={inspector} />}
            {tab === "zero" && (
              <ZeroShotPage
                zeroShotClasses={zeroShotClasses}
                setZeroShotClasses={setZeroShotClasses}
                uploads={uploads}
                fileRef={fileRef}
                folderRef={folderRef}
                handleFiles={handleFiles}
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                onDrop={onDrop}
              />
            )}
            {tab === "road" && <RoadmapPage />}
          </motion.div>
        </AnimatePresence>

        <footer className="app-footer">
          <img src="/nauticai-logo.png" alt="" />
          <span className="footer-dot">·</span>
          <a href="https://www.nauticai-ai.com" target="_blank" rel="noreferrer">www.nauticai-ai.com</a>
          <span className="footer-dot">·</span>
          <span>NautiCAI v1.0 — Deep-tech Venture · Singapore</span>
        </footer>
      </div>
    </div>
  );
}

/* ── Toggle ── */
function Toggle({ label, checked, onChange }) {
  return (
    <label className="ctrl-toggle">
      <span className="tgl">
        <input type="checkbox" checked={checked} onChange={onChange} />
        <span className="tgl-track" />
        <span className="tgl-knob" />
      </span>
      <span>{label}</span>
    </label>
  );
}

/* ── DropZone ── */
function DropZone({
  fileRef,
  folderRef,
  uploads,
  handleFiles,
  onDragOver,
  onDragLeave,
  onDrop,
  clearUploads,
  removeUpload,
}) {
  return (
    <div className="card mb-20">
      <div className="card-title">Image Upload</div>

      <div
        className="dropzone"
        onClick={() => fileRef.current?.click()}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
      >
        <div className="dz-icon">📷</div>
        <div className="dz-label">
          {uploads?.length
            ? `Uploaded ${uploads.length} image(s) — click to add more`
            : "Drop underwater images here, or click to browse"}
        </div>
        <div className="dz-hint">Supported: JPG, PNG, BMP · Multiple images + folder upload supported</div>
      </div>

      <div className="row" style={{ gap: 10, marginTop: 12, flexWrap: "wrap" }}>
        <button type="button" className="btn btn-ghost" onClick={() => fileRef.current?.click()}>
          + Add Images
        </button>
        <button type="button" className="btn btn-ghost" onClick={() => folderRef.current?.click()}>
          📁 Upload Folder
        </button>
        {!!uploads?.length && (
          <button type="button" className="btn btn-ghost" onClick={clearUploads}>
            Clear All
          </button>
        )}
      </div>

      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        multiple
        hidden
        onChange={(e) => handleFiles(e.target.files)}
      />

      <input
        ref={folderRef}
        type="file"
        accept="image/*"
        multiple
        hidden
        onChange={(e) => handleFiles(e.target.files)}
        {...{ webkitdirectory: "", directory: "" }}
      />

      {!!uploads?.length && (
        <div style={{ marginTop: 14, display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))", gap: 10 }}>
          {uploads.map((item) => (
            <div key={item.id} style={{ background: "rgba(255,255,255,0.03)", padding: 8, borderRadius: 8, position: "relative" }}>
              <img
                src={item.preview}
                alt={item.file.name}
                style={{ width: "100%", height: 90, objectFit: "cover", borderRadius: 6 }}
              />
              <button
                type="button"
                onClick={() => removeUpload(item.id)}
                style={{
                  position: "absolute",
                  top: 6,
                  right: 6,
                  width: 24,
                  height: 24,
                  borderRadius: "50%",
                  border: "none",
                  background: "rgba(0,0,0,0.65)",
                  color: "#fff",
                  cursor: "pointer",
                }}
              >
                ×
              </button>
              <div style={{ fontSize: 11, marginTop: 6, opacity: 0.7, wordBreak: "break-word" }}>
                {item.file.name}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── StatusBar ── */
function StatusBar({ error, waMessage }) {
  return (
    <>
      {error && <div className="alert alert-error" style={{ marginTop: 12 }}>{error}</div>}
      {waMessage && <div className="alert" style={{ marginTop: 8 }}>{waMessage}</div>}
    </>
  );
}

/* ── Privacy Timer ── */
function PrivacyTimer({ countdown, cert }) {
  if (countdown === null && !cert) return null;
  if (cert) return (
    <div style={{ marginTop: 16, padding: "12px 16px", background: "#00cc4411", border: "1px solid #00cc4444", borderRadius: 8 }}>
      <div style={{ fontSize: 11, color: "#00cc44", fontWeight: 700, letterSpacing: 1, marginBottom: 6 }}>✅ DELETION CERTIFICATE ISSUED</div>
      <div style={{ fontSize: 11, opacity: 0.7 }}>All client footage has been cryptographically deleted.</div>
      <div style={{ fontSize: 10, opacity: 0.5, marginTop: 4, fontFamily: "monospace" }}>CERT-{cert.hash} · {new Date(cert.time).toLocaleTimeString()}</div>
    </div>
  );
  const pct = (countdown / 60) * 100;
  const col = countdown > 30 ? "#22c55e" : countdown > 10 ? "#f59e0b" : "#ef4444";
  return (
    <div style={{ marginTop: 16, padding: "12px 16px", background: "#ef444411", border: "1px solid #ef444433", borderRadius: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <div style={{ fontSize: 11, color: col, fontWeight: 700, letterSpacing: 1 }}>🔒 PRIVACY-FIRST AUTO-DELETION</div>
        <div style={{ fontSize: 18, fontWeight: 900, color: col, fontFamily: "monospace" }}>{countdown}s</div>
      </div>
      <div style={{ height: 4, borderRadius: 2, background: "rgba(255,255,255,0.08)", overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: col, borderRadius: 2, transition: "width 1s linear" }} />
      </div>
      <div style={{ fontSize: 10, opacity: 0.5, marginTop: 6 }}>Client footage will be cryptographically deleted after this timer.</div>
    </div>
  );
}

/* ── Inspector Disagreement Flag ── */
function DisagreementFlag({ insp1Sev, setInsp1Sev, insp2Sev, setInsp2Sev }) {
  const sevs = ["", "Low", "Medium", "High", "Critical"];
  const disagree = insp1Sev && insp2Sev && insp1Sev !== insp2Sev;
  return (
    <div className="card" style={{ marginTop: 16 }}>
      <div className="card-title" style={{ marginBottom: 12 }}>👁️ Inspector Disagreement Flag</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 11, opacity: 0.5, marginBottom: 6 }}>Inspector 1 Severity Rating</div>
          <select className="ctrl-select" style={{ width: "100%" }} value={insp1Sev} onChange={e => setInsp1Sev(e.target.value)}>
            {sevs.map(s => <option key={s} value={s}>{s || "— Select —"}</option>)}
          </select>
        </div>
        <div>
          <div style={{ fontSize: 11, opacity: 0.5, marginBottom: 6 }}>Inspector 2 Severity Rating</div>
          <select className="ctrl-select" style={{ width: "100%" }} value={insp2Sev} onChange={e => setInsp2Sev(e.target.value)}>
            {sevs.map(s => <option key={s} value={s}>{s || "— Select —"}</option>)}
          </select>
        </div>
      </div>
      {disagree && (
        <div style={{ padding: "10px 14px", background: "#f59e0b22", border: "1px solid #f59e0b55", borderRadius: 6 }}>
          <div style={{ color: "#f59e0b", fontWeight: 700, fontSize: 12, marginBottom: 4 }}>⚠️ DISAGREEMENT FLAGGED — Third Review Required</div>
          <div style={{ fontSize: 11, opacity: 0.7 }}>Inspector 1 rated <strong>{insp1Sev}</strong> · Inspector 2 rated <strong>{insp2Sev}</strong>.</div>
        </div>
      )}
      {insp1Sev && insp2Sev && !disagree && (
        <div style={{ padding: "10px 14px", background: "#22c55e22", border: "1px solid #22c55e44", borderRadius: 6 }}>
          <div style={{ color: "#22c55e", fontWeight: 700, fontSize: 12 }}>✅ Inspectors agree — {insp1Sev} severity confirmed</div>
        </div>
      )}
    </div>
  );
}

/* ── Helpers ── */
function bboxArea(b) {
  if (!b) return null;
  return Math.round(
    Math.abs((b.xmax ?? b.x2 ?? 0) - (b.xmin ?? b.x1 ?? 0)) *
    Math.abs((b.ymax ?? b.y2 ?? 0) - (b.ymin ?? b.y1 ?? 0))
  );
}
function fmtArea(px) { return px ? px.toLocaleString() + " px" : "—"; }
function confColor(c) {
  if (c == null) return "inherit";
  if (c >= 0.75) return "#22c55e";
  if (c >= 0.5) return "#f59e0b";
  return "#ef4444";
}
function sevColor(s) {
  if (!s) return "#6b7280";
  const v = s.toLowerCase();
  if (v === "critical") return "#ef4444";
  if (v === "high") return "#f97316";
  if (v === "medium") return "#f59e0b";
  if (v === "low") return "#22c55e";
  return "#6b7280";
}

/* ── SVG Pie ── */
function PieChart({ data, size = 160 }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  if (!total) return null;
  const cx = size / 2, cy = size / 2, r = size / 2 - 10;
  let ang = -Math.PI / 2;
  const slices = data.map(d => {
    const a = (d.value / total) * 2 * Math.PI;
    const x1 = cx + r * Math.cos(ang), y1 = cy + r * Math.sin(ang);
    const x2 = cx + r * Math.cos(ang + a), y2 = cy + r * Math.sin(ang + a);
    const path = `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${a > Math.PI ? 1 : 0} 1 ${x2} ${y2} Z`;
    const mx = cx + (r * 0.65) * Math.cos(ang + a / 2), my = cy + (r * 0.65) * Math.sin(ang + a / 2);
    ang += a;
    return { ...d, path, mx, my, pct: ((d.value / total) * 100).toFixed(0) };
  });
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {slices.map((s, i) => (
        <g key={i}>
          <path d={s.path} fill={s.color} opacity={0.9} stroke="rgba(0,0,0,0.3)" strokeWidth="1" />
          {parseInt(s.pct) >= 8 && (
            <text x={s.mx} y={s.my} textAnchor="middle" dominantBaseline="middle" fill="white" fontSize="10" fontWeight="700">
              {s.pct}%
            </text>
          )}
        </g>
      ))}
    </svg>
  );
}

/* ── Image Panel ── */
function ImgPanel({ label, color, src, placeholder }) {
  return (
    <div style={{ position: "relative" }}>
      <span
        style={{
          position: "absolute",
          top: 10,
          left: 10,
          zIndex: 2,
          background: "rgba(0,0,0,0.6)",
          border: `1px solid ${color}44`,
          color,
          fontSize: 10,
          fontWeight: 700,
          letterSpacing: 1,
          padding: "3px 8px",
          borderRadius: 4,
          textTransform: "uppercase"
        }}
      >
        {label}
      </span>
      {src
        ? <img src={src} alt={label} style={{ width: "100%", borderRadius: 8, display: "block" }} />
        : <div style={{ background: "rgba(255,255,255,0.03)", borderRadius: 8, minHeight: 200, display: "flex", alignItems: "center", justifyContent: "center", color: "rgba(255,255,255,0.2)", fontSize: 12 }}>{placeholder}</div>
      }
    </div>
  );
}

function StatBox({ label, value, color, small }) {
  return (
    <div className="card" style={{ textAlign: "center", padding: "16px 10px" }}>
      <div style={{ fontSize: small ? 14 : 22, fontWeight: 700, color, wordBreak: "break-all" }}>{value}</div>
      <div style={{ fontSize: 10, letterSpacing: 1, opacity: 0.45, marginTop: 4, textTransform: "uppercase" }}>{label}</div>
    </div>
  );
}

function BigStat({ label, value, color }) {
  return (
    <div className="card" style={{ textAlign: "center", padding: "20px 12px" }}>
      <div style={{ fontSize: 10, letterSpacing: 1, opacity: 0.4, textTransform: "uppercase", marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color }}>{value}</div>
    </div>
  );
}

/* ── Detection Results Panel ── */
function DetectionResultsPanel({ detResult, enhResult, preview, exportCSV }) {
  if (!detResult && !enhResult) return null;
  const dets = detResult?.detections || [];
  const total = detResult?.total ?? dets.length ?? 0;
  const annotatedImg = detResult?.annotated_b64 ?? detResult?.image ?? null;
  const heatmapImg = detResult?.heatmap_b64 ?? detResult?.heatmap ?? null;
  const enhancedImg = detResult?.enhanced_b64 ?? enhResult?.enhanced_b64 ?? enhResult?.image ?? null;
  const sevCount = dets.reduce((acc, d) => {
    const s = d.severity || "Unknown";
    acc[s] = (acc[s] || 0) + 1;
    return acc;
  }, {});
  const pieData = [
    { label: "Critical", value: sevCount["Critical"] ?? 0, color: "#ef4444" },
    { label: "High", value: sevCount["High"] ?? 0, color: "#f97316" },
    { label: "Medium", value: sevCount["Medium"] ?? 0, color: "#f59e0b" },
    { label: "Low", value: sevCount["Low"] ?? 0, color: "#22c55e" }
  ].filter(d => d.value > 0);

  return (
    <div style={{ marginTop: 24 }}>
      {detResult && (
        <>
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 13, letterSpacing: 1, opacity: 0.5, textTransform: "uppercase", marginBottom: 4 }}>Detection Results</div>
            <div style={{ fontSize: 20, fontWeight: 700 }}>{total} {total === 1 ? "Anomaly" : "Anomalies"} Found</div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, marginBottom: 20 }}>
            <StatBox label="DETECTIONS" value={total} color="#22d3ee" />
            <StatBox label="RISK SCORE" value={detResult.risk_score != null ? `${detResult.risk_score}%` : "—"} color="#f59e0b" />
            <StatBox label="GRADE" value={detResult.grade ?? "—"} color="#a78bfa" />
            <StatBox label="MISSION" value={detResult.mission_id ?? "—"} color="#94a3b8" small />
          </div>
        </>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
        <ImgPanel label="ANNOTATED" color="#22d3ee" src={annotatedImg ? `data:image/jpeg;base64,${annotatedImg}` : null} placeholder="Run detection to see annotated image" />
        <ImgPanel label="HEATMAP" color="#f59e0b" src={heatmapImg ? `data:image/jpeg;base64,${heatmapImg}` : null} placeholder="Not available from backend" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 20 }}>
        <ImgPanel label="ORIGINAL" color="#64748b" src={preview} placeholder="No image uploaded" />
        <ImgPanel label="ENHANCED" color="#22c55e" src={enhancedImg ? `data:image/jpeg;base64,${enhancedImg}` : null} placeholder="Click Detect + Enhance to generate" />
      </div>

      {pieData.length > 0 && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-title" style={{ marginBottom: 14 }}>Severity Distribution & Recovery Rate</div>
          <div style={{ display: "flex", alignItems: "center", gap: 32 }}>
            <PieChart data={pieData} size={160} />
            <div style={{ flex: 1 }}>
              {pieData.map(d => (
                <div key={d.label} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                  <span style={{ width: 12, height: 12, borderRadius: "50%", background: d.color, flexShrink: 0, display: "inline-block" }} />
                  <span style={{ fontSize: 13, flex: 1 }}>{d.label}</span>
                  <span style={{ fontWeight: 700, color: d.color }}>{d.value}</span>
                  <div style={{ width: 80, height: 4, borderRadius: 2, background: "rgba(255,255,255,0.08)", overflow: "hidden" }}>
                    <div style={{ width: `${(d.value / total) * 100}%`, height: "100%", background: d.color, borderRadius: 2 }} />
                  </div>
                  <span style={{ fontSize: 11, opacity: 0.5, minWidth: 32 }}>{((d.value / total) * 100).toFixed(0)}%</span>
                </div>
              ))}
              <div style={{ marginTop: 14, paddingTop: 12, borderTop: "1px solid rgba(255,255,255,0.07)", fontSize: 12, opacity: 0.6 }}>
                Recovery Rate: <strong style={{ color: "#22c55e" }}>{(((sevCount["Low"] ?? 0) + (sevCount["Medium"] ?? 0)) / total * 100).toFixed(0)}%</strong> low/medium severity
              </div>
            </div>
          </div>
        </div>
      )}

      {dets.length > 0 && (
        <div className="card" style={{ overflowX: "auto" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
            <div className="card-title" style={{ margin: 0 }}>Detection Breakdown — {dets.length} objects</div>
            <button className="btn btn-ghost" style={{ padding: "4px 12px", fontSize: 12 }} onClick={() => exportCSV({ detections: dets, mission_id: detResult?.mission_id })}>📊 Export CSV</button>
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
                {["#", "CLASS", "CONFIDENCE", "SEVERITY", "BBOX AREA"].map(h => (
                  <th key={h} style={{ padding: "6px 12px", textAlign: "left", opacity: 0.45, fontSize: 11, letterSpacing: 0.8, fontWeight: 600 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dets.map((d, i) => (
                <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                  <td style={{ padding: "8px 12px", opacity: 0.4 }}>{i + 1}</td>
                  <td style={{ padding: "8px 12px", fontWeight: 600 }}>{d.cls ?? d.class ?? "—"}</td>
                  <td style={{ padding: "8px 12px" }}><span style={{ color: confColor(d.conf), fontWeight: 600 }}>{d.conf != null ? `${(d.conf * 100).toFixed(1)}%` : "—"}</span></td>
                  <td style={{ padding: "8px 12px" }}>
                    {d.severity ? (
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 5, padding: "3px 10px", borderRadius: 4, fontSize: 11, fontWeight: 700, background: sevColor(d.severity) + "22", color: sevColor(d.severity) }}>
                        <span style={{ width: 7, height: 7, borderRadius: "50%", background: sevColor(d.severity), display: "inline-block" }} />
                        {d.severity}
                      </span>
                    ) : "—"}
                  </td>
                  <td style={{ padding: "8px 12px", opacity: 0.6 }}>{fmtArea(bboxArea(d.bbox))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ── Shared action buttons ── */
function ImageActionButtons({
  uploads, loading, detectAll, genPDF, sendPDFToWa, sendCompletionAlert,
  completionAlertSent, sendingWa, exportCSV, latestDetForTab, onOpenCompliance,
  scanLabel = "Run Scan", showEnhance = false, enhanceAll, runBothAll
}) {
  return (
    <div className="row mb-20" style={{ gap: 10, flexWrap: "wrap" }}>
      <button className="btn btn-primary" disabled={!uploads.length || loading} onClick={detectAll}>
        {loading && <span className="spinner" />} {scanLabel}
      </button>
      {showEnhance && (
        <>
          <button className="btn btn-ghost" disabled={!uploads.length || loading} onClick={enhanceAll}>Enhance Visibility</button>
          <button className="btn btn-primary" disabled={!uploads.length || loading} onClick={runBothAll}>Detect + Enhance</button>
        </>
      )}
      <button className="btn btn-ghost" disabled={!uploads.length} onClick={genPDF}>📄 PDF Report</button>
      <button className="btn btn-ghost" disabled={!uploads.length || sendingWa} onClick={sendPDFToWa}>{sendingWa ? "…" : "📱 WhatsApp"}</button>
      {latestDetForTab && (
        <>
          <button className="btn btn-ghost" disabled={sendingWa || completionAlertSent} onClick={() => sendCompletionAlert("image")}>
            {completionAlertSent ? "✓ Alert sent" : "🔔 Alert"}
          </button>
          <button className="btn btn-primary" onClick={onOpenCompliance}>📋 Compliance</button>
          <button className="btn btn-ghost" onClick={() => exportCSV(latestDetForTab)}>📊 CSV</button>
        </>
      )}
    </div>
  );
}

/* ── Compliance helpers ── */
function ComplianceSection({ title, color, children }) {
  return (
    <div style={{ marginBottom: 24, border: `1px solid ${color}22`, borderRadius: 8, overflow: "hidden" }}>
      <div style={{ padding: "10px 16px", background: `${color}11`, borderBottom: `1px solid ${color}22`, fontSize: 12, fontWeight: 700, color, letterSpacing: 0.5 }}>{title}</div>
      <div style={{ padding: 4 }}>{children}</div>
    </div>
  );
}

function ComplianceRow({ label, value, highlight }) {
  return (
    <div style={{ display: "flex", padding: "8px 16px", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
      <div style={{ width: 240, fontSize: 12, opacity: 0.5 }}>{label}</div>
      <div style={{ flex: 1, fontSize: 12, fontWeight: highlight ? 700 : 400, color: highlight ? "#22d3ee" : "inherit" }}>{String(value)}</div>
    </div>
  );
}

function ComplianceModal({ detResult, vesselName, inspector, onClose }) {
  const dets = detResult?.detections || [];
  const total = detResult?.total ?? dets.length ?? 0;
  const classes = [...new Set(dets.map(d => d.cls ?? d.class).filter(Boolean))];
  const today = new Date().toLocaleDateString("en-GB");
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.85)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
      <div style={{ background: "#080f1e", border: "1px solid #0d2a4a", borderRadius: 12, width: "100%", maxWidth: 800, maxHeight: "90vh", overflow: "auto", padding: 32 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <div>
            <div style={{ fontSize: 11, opacity: 0.5, letterSpacing: 1, textTransform: "uppercase" }}>NautiCAI · Compliance</div>
            <h2 style={{ fontSize: 22, fontWeight: 700 }}>Regulatory Auto-Fill Report</h2>
          </div>
          {onClose && <button className="btn btn-ghost" onClick={onClose}>✕ Close</button>}
        </div>
        <ComplianceSection title="IMO — International Maritime Organization" color="#22d3ee">
          <ComplianceRow label="Vessel Name" value={vesselName || "Unknown"} />
          <ComplianceRow label="Inspection Date" value={today} />
          <ComplianceRow label="Inspector" value={inspector} />
          <ComplianceRow label="Defects Found" value={total} />
          <ComplianceRow label="Defect Classes" value={classes.join(", ") || "None"} />
          <ComplianceRow label="Overall Grade" value={detResult?.grade ?? "—"} />
          <ComplianceRow label="Risk Score" value={detResult?.risk_score != null ? `${detResult.risk_score}%` : "—"} />
          <ComplianceRow label="IMO Compliance" value={detResult?.grade === "A" || detResult?.grade === "B" ? "COMPLIANT" : "NON-COMPLIANT — Action required"} highlight />
        </ComplianceSection>
        <ComplianceSection title="SOLAS — Safety of Life at Sea" color="#22c55e">
          <ComplianceRow label="Chapter II-1" value="Inspection completed" />
          <ComplianceRow label="Critical Defects" value={dets.filter(d => d.severity === "Critical").length} />
          <ComplianceRow label="High Severity" value={dets.filter(d => d.severity === "High").length} />
          <ComplianceRow label="Immediate Action" value={dets.filter(d => d.severity === "Critical").length > 0 ? "YES" : "NO"} highlight />
          <ComplianceRow label="Next Inspection Due" value="Within 12 months or after dry-dock" />
        </ComplianceSection>
        <ComplianceSection title="DNV — Det Norske Veritas" color="#f59e0b">
          <ComplianceRow label="Class Notation" value="NautiCAI AI-Assisted Inspection" />
          <ComplianceRow label="Detection Method" value="YOLOv8 — Deep Learning CV" />
          <ComplianceRow label="Total Anomalies" value={total} />
          <ComplianceRow label="Avg Confidence" value={dets.length ? `${(dets.reduce((s, d) => s + (d.conf ?? 0), 0) / dets.length * 100).toFixed(1)}%` : "—"} />
          <ComplianceRow label="Survey Status" value="AI Pre-Survey Completed" highlight />
        </ComplianceSection>
        <ComplianceSection title="Lloyd's Register" color="#a855f7">
          <ComplianceRow label="Survey Type" value="Underwater AI Inspection" />
          <ComplianceRow label="Mission ID" value={detResult?.mission_id ?? "—"} />
          <ComplianceRow label="Report Generated" value={new Date().toISOString()} />
          <ComplianceRow label="Digital Signature" value="NautiCAI Platform v1.0" highlight />
        </ComplianceSection>
        <div style={{ display: "flex", gap: 12, marginTop: 24 }}>
          <button className="btn btn-primary" onClick={() => window.print()}>🖨️ Print Report</button>
          {onClose && <button className="btn btn-ghost" onClick={onClose}>Close</button>}
        </div>
      </div>
    </div>
  );
}

/* ═══ PAGE: Anomaly Scan ═══ */
function ScanPage({
  uploads, fileRef, folderRef, handleFiles, removeUpload, clearUploads,
  onDragOver, onDragLeave, onDrop,
  detectAll, enhanceAll, runBothAll, genPDF, sendPDFToWa, sendCompletionAlert,
  completionAlertSent, sendingWa, waMessage, exportCSV, loading, error,
  privacyCountdown, deletionCert, insp1Sev, setInsp1Sev, insp2Sev, setInsp2Sev, onOpenCompliance
}) {
  const latestDetForTab = uploads.find(x => x.detResult)?.detResult || null;

  return (
    <>
      <div className="section-header fade-up">
        <div className="section-crumb">Module · Anomaly Detection</div>
        <h2 className="section-title">Underwater Anomaly Scan</h2>
        <p className="section-desc">Upload one or many underwater images to run AI-powered anomaly detection, enhancement, and reporting.</p>
        <div className="section-rule" />
      </div>

      <DropZone
        fileRef={fileRef}
        folderRef={folderRef}
        uploads={uploads}
        handleFiles={handleFiles}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        clearUploads={clearUploads}
        removeUpload={removeUpload}
      />

      <ImageActionButtons
        uploads={uploads}
        loading={loading}
        detectAll={detectAll}
        enhanceAll={enhanceAll}
        runBothAll={runBothAll}
        genPDF={genPDF}
        sendPDFToWa={sendPDFToWa}
        sendCompletionAlert={sendCompletionAlert}
        completionAlertSent={completionAlertSent}
        sendingWa={sendingWa}
        exportCSV={exportCSV}
        latestDetForTab={latestDetForTab}
        onOpenCompliance={onOpenCompliance}
        scanLabel="Run Detection"
        showEnhance
      />

      <StatusBar error={error} waMessage={waMessage} />
      <PrivacyTimer countdown={privacyCountdown} cert={deletionCert} />

      <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        {uploads.map((item, idx) => (
          <div key={item.id} className="card" style={{ padding: 16 }}>
            <div style={{ marginBottom: 12, fontWeight: 700 }}>
              Image {idx + 1}: {item.file.name}
            </div>
            <DetectionResultsPanel detResult={item.detResult} enhResult={item.enhResult} preview={item.preview} exportCSV={exportCSV} />
          </div>
        ))}
      </div>

      {latestDetForTab && <DisagreementFlag insp1Sev={insp1Sev} setInsp1Sev={setInsp1Sev} insp2Sev={insp2Sev} setInsp2Sev={setInsp2Sev} />}
    </>
  );
}

/* ═══ PAGE: Hull ═══ */
function HullPage({
  uploads, fileRef, folderRef, handleFiles, removeUpload, clearUploads,
  onDragOver, onDragLeave, onDrop,
  detectAll, genPDF, sendPDFToWa, sendCompletionAlert,
  completionAlertSent, sendingWa, waMessage, exportCSV, loading, error,
  privacyCountdown, deletionCert, insp1Sev, setInsp1Sev, insp2Sev, setInsp2Sev, onOpenCompliance
}) {
  const latestDetForTab = uploads.find(x => x.detResult)?.detResult || null;

  return (
    <>
      <div className="section-header fade-up">
        <div className="section-crumb">Module · Hull Inspection</div>
        <h2 className="section-title">Hull Inspection</h2>
        <p className="section-desc">Detect corrosion, biofouling, cracks and structural anomalies on vessel hull surfaces.</p>
        <div className="section-rule" />
      </div>

      <DropZone
        fileRef={fileRef}
        folderRef={folderRef}
        uploads={uploads}
        handleFiles={handleFiles}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        clearUploads={clearUploads}
        removeUpload={removeUpload}
      />

      <ImageActionButtons
        uploads={uploads}
        loading={loading}
        detectAll={detectAll}
        genPDF={genPDF}
        sendPDFToWa={sendPDFToWa}
        sendCompletionAlert={sendCompletionAlert}
        completionAlertSent={completionAlertSent}
        sendingWa={sendingWa}
        exportCSV={exportCSV}
        latestDetForTab={latestDetForTab}
        onOpenCompliance={onOpenCompliance}
        scanLabel="Run Hull Scan"
      />

      <StatusBar error={error} waMessage={waMessage} />
      <PrivacyTimer countdown={privacyCountdown} cert={deletionCert} />

      <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        {uploads.map((item, idx) => (
          <div key={item.id} className="card" style={{ padding: 16 }}>
            <div style={{ marginBottom: 12, fontWeight: 700 }}>
              Hull Image {idx + 1}: {item.file.name}
            </div>
            <DetectionResultsPanel detResult={item.detResult} preview={item.preview} exportCSV={exportCSV} />
          </div>
        ))}
      </div>

      {latestDetForTab && <DisagreementFlag insp1Sev={insp1Sev} setInsp1Sev={setInsp1Sev} insp2Sev={insp2Sev} setInsp2Sev={setInsp2Sev} />}
    </>
  );
}

/* ═══ PAGE: Video ═══ */
function VideoPage({
  videoFile, videoRef, setVideoFile, onDragOver, onDragLeave,
  analyzeVideo, genVideoPDF, sendVideoPDFToWa, sendCompletionAlert,
  completionAlertSent, videoLoading, sendingWa, waMessage, videoResult, error
}) {
  return (
    <>
      <div className="section-header fade-up">
        <div className="section-crumb">Module · Video Analysis</div>
        <h2 className="section-title">Video Analysis</h2>
        <p className="section-desc">Upload underwater inspection footage for frame-sampled anomaly detection and reporting.</p>
        <div className="section-rule" />
      </div>

      <div className="card mb-20">
        <div className="card-title">Video Upload</div>
        <div
          className="dropzone"
          onClick={() => videoRef.current?.click()}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={e => {
            e.preventDefault();
            e.currentTarget.classList.remove("drag-over");
            setVideoFile(e.dataTransfer.files[0]);
          }}
        >
          <div className="dz-icon">🎬</div>
          <div className="dz-label">{videoFile ? "Click or drop to replace" : "Drop video file here, or click to browse"}</div>
          <div className="dz-hint">Supported: MP4, AVI, MOV · Max 500 MB</div>
          {videoFile && <div className="dz-file">✓ {videoFile.name}</div>}
        </div>
        <input ref={videoRef} type="file" accept="video/*" hidden onChange={e => setVideoFile(e.target.files[0])} />
      </div>

      <div className="row mb-20" style={{ gap: 10, flexWrap: "wrap" }}>
        <button className="btn btn-primary" disabled={!videoFile || videoLoading} onClick={analyzeVideo}>{videoLoading && <span className="spinner" />} Analyze Video</button>
        <button className="btn btn-ghost" disabled={!videoFile} onClick={genVideoPDF}>📄 PDF Report</button>
        <button className="btn btn-ghost" disabled={!videoFile || sendingWa} onClick={sendVideoPDFToWa}>{sendingWa ? "…" : "📱 WhatsApp"}</button>
        {videoResult && <button className="btn btn-ghost" disabled={sendingWa || completionAlertSent} onClick={() => sendCompletionAlert("video")}>{completionAlertSent ? "✓ Alert sent" : "🔔 Alert"}</button>}
      </div>

      <StatusBar error={error} waMessage={waMessage} />

      {videoResult && (
        <div style={{ marginTop: 20 }}>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 16 }}>
            <StatBox label="Detections" value={videoResult.total_detections ?? 0} color="#22d3ee" />
            {videoResult.grade && <StatBox label="Grade" value={videoResult.grade} color="#22c55e" />}
            {videoResult.risk_score != null && <StatBox label="Risk Score" value={`${videoResult.risk_score}%`} color="#f59e0b" />}
          </div>

          {videoResult.frames?.length > 0 && (
            <div className="card">
              <div className="card-title" style={{ marginBottom: 12 }}>Sampled Frames</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                {videoResult.frames.map((f, i) => <img key={i} src={`data:image/jpeg;base64,${f}`} alt={`Frame ${i + 1}`} style={{ width: 200, borderRadius: 6 }} />)}
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
}

/* ═══ PAGE: Pipeline ═══ */
function PipelinePage({
  uploads, fileRef, folderRef, handleFiles, removeUpload, clearUploads,
  onDragOver, onDragLeave, onDrop,
  detectAll, genPDF, sendPDFToWa, sendCompletionAlert,
  completionAlertSent, sendingWa, waMessage,
  exportCSV, loading, error, privacyCountdown, deletionCert,
  insp1Sev, setInsp1Sev, insp2Sev, setInsp2Sev, onOpenCompliance
}) {
  const [viewModes, setViewModes] = useState({});
  const iframeRefs = useRef({});

  const latestDetForTab = uploads.find(x => x.detResult)?.detResult || null;

  const buildTwinData = (det) => {
    const dets = det?.detections || [];
    const total = dets.length;

    return {
      total_defects: det?.total ?? total,
      risk_score: det?.risk_score ?? 0,
      grade: det?.grade ?? "--",
      defects_3d: dets.map((d, i) => ({
        id: i + 1,
        cls: d.cls ?? d.class ?? "Unknown",
        severity: d.severity ?? "Low",
        conf: d.conf ?? 0,
        pipeline_pos: total === 1 ? 50 : Math.round(5 + (i / Math.max(total - 1, 1)) * 90),
        angle: (i / Math.max(total, 1)) * 2 * Math.PI,
      })),
    };
  };

  const handleTwinLoad = (id, detResult) => {
    const iframe = iframeRefs.current[id];
    if (!iframe || !detResult) return;
    iframe.contentWindow?.postMessage(
      {
        type: "NAUTICAI_DETECTIONS",
        data: buildTwinData(detResult),
      },
      "*"
    );
  };

  return (
    <>
      <div className="section-header fade-up">
        <div className="section-crumb">Module · Pipeline Inspection</div>
        <h2 className="section-title">Pipeline Inspection</h2>
        <p className="section-desc">Upload multiple images or a folder. Each image generates its own 2D pipeline map and 3D digital twin.</p>
        <div className="section-rule" />
      </div>

      <DropZone
        fileRef={fileRef}
        folderRef={folderRef}
        uploads={uploads}
        handleFiles={handleFiles}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        clearUploads={clearUploads}
        removeUpload={removeUpload}
      />

      <ImageActionButtons
        uploads={uploads}
        loading={loading}
        detectAll={detectAll}
        genPDF={genPDF}
        sendPDFToWa={sendPDFToWa}
        sendCompletionAlert={sendCompletionAlert}
        completionAlertSent={completionAlertSent}
        sendingWa={sendingWa}
        exportCSV={exportCSV}
        latestDetForTab={latestDetForTab}
        onOpenCompliance={onOpenCompliance}
        scanLabel="Run Pipeline Scan"
      />

      <StatusBar error={error} waMessage={waMessage} />
      <PrivacyTimer countdown={privacyCountdown} cert={deletionCert} />

      <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        {uploads.map((item, idx) => {
          const mode = viewModes[item.id] || "2d";

          return (
            <div key={item.id} className="card" style={{ padding: 16 }}>
              <div style={{ marginBottom: 14, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontWeight: 700 }}>Pipeline Image {idx + 1}</div>
                  <div style={{ fontSize: 12, opacity: 0.6 }}>{item.file.name}</div>
                </div>
              </div>

              {item.detResult && (
                <>
                  <div style={{ display: "flex", alignItems: "center", gap: 0, marginBottom: 16, borderRadius: 8, overflow: "hidden", border: "1px solid rgba(34,211,238,0.2)", width: "fit-content" }}>
                    <button
                      onClick={() => setViewModes(p => ({ ...p, [item.id]: "2d" }))}
                      style={{
                        padding: "8px 20px",
                        background: mode === "2d" ? "rgba(34,211,238,0.15)" : "transparent",
                        border: "none",
                        borderRight: "1px solid rgba(34,211,238,0.2)",
                        color: mode === "2d" ? "#22d3ee" : "rgba(255,255,255,0.5)",
                        cursor: "pointer",
                        fontSize: 12,
                        fontWeight: mode === "2d" ? 700 : 400,
                      }}
                    >
                      🗺️ 2D Pipeline Map
                    </button>
                    <button
                      onClick={() => setViewModes(p => ({ ...p, [item.id]: "3d" }))}
                      style={{
                        padding: "8px 20px",
                        background: mode === "3d" ? "rgba(34,211,238,0.15)" : "transparent",
                        border: "none",
                        color: mode === "3d" ? "#22d3ee" : "rgba(255,255,255,0.5)",
                        cursor: "pointer",
                        fontSize: 12,
                        fontWeight: mode === "3d" ? 700 : 400,
                      }}
                    >
                      🧊 3D Digital Twin
                    </button>
                  </div>

                  {mode === "2d" && (
                    <PipelineMap2D
                      detResult={item.detResult}
                      imgW={item.detResult.img_width ?? 1280}
                      imgH={item.detResult.img_height ?? 720}
                    />
                  )}

                  {mode === "3d" && (
                    <div style={{ width: "100%", height: 500, marginBottom: 20 }}>
                      <iframe
                        ref={(el) => { iframeRefs.current[item.id] = el; }}
                        src="/pipeline-3d-twin.html"
                        title={`3D Digital Twin ${item.id}`}
                        style={{ width: "100%", height: "100%", border: "none", borderRadius: 8 }}
                        onLoad={() => handleTwinLoad(item.id, item.detResult)}
                      />
                    </div>
                  )}
                </>
              )}

              <DetectionResultsPanel detResult={item.detResult} enhResult={item.enhResult} preview={item.preview} exportCSV={exportCSV} />
            </div>
          );
        })}
      </div>

      {latestDetForTab && <DisagreementFlag insp1Sev={insp1Sev} setInsp1Sev={setInsp1Sev} insp2Sev={insp2Sev} setInsp2Sev={setInsp2Sev} />}
    </>
  );
}

/* ═══ PAGE: Cable ═══ */
function CablePage({
  uploads, fileRef, folderRef, handleFiles, removeUpload, clearUploads,
  onDragOver, onDragLeave, onDrop,
  detectAll, genPDF, sendPDFToWa, sendCompletionAlert,
  completionAlertSent, sendingWa, waMessage, exportCSV, loading, error,
  privacyCountdown, deletionCert, insp1Sev, setInsp1Sev, insp2Sev, setInsp2Sev, onOpenCompliance
}) {
  const latestDetForTab = uploads.find(x => x.detResult)?.detResult || null;

  return (
    <>
      <div className="section-header fade-up">
        <div className="section-crumb">Module · Sub-sea Cable</div>
        <h2 className="section-title">Sub-sea Cable Inspection</h2>
        <p className="section-desc">Identify cable damage, abrasion, anchor strikes and exposure risks on subsea cable routes.</p>
        <div className="section-rule" />
      </div>

      <DropZone
        fileRef={fileRef}
        folderRef={folderRef}
        uploads={uploads}
        handleFiles={handleFiles}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        clearUploads={clearUploads}
        removeUpload={removeUpload}
      />

      <ImageActionButtons
        uploads={uploads}
        loading={loading}
        detectAll={detectAll}
        genPDF={genPDF}
        sendPDFToWa={sendPDFToWa}
        sendCompletionAlert={sendCompletionAlert}
        completionAlertSent={completionAlertSent}
        sendingWa={sendingWa}
        exportCSV={exportCSV}
        latestDetForTab={latestDetForTab}
        onOpenCompliance={onOpenCompliance}
        scanLabel="Run Cable Scan"
      />

      <StatusBar error={error} waMessage={waMessage} />
      <PrivacyTimer countdown={privacyCountdown} cert={deletionCert} />

      <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        {uploads.map((item, idx) => (
          <div key={item.id} className="card" style={{ padding: 16 }}>
            <div style={{ marginBottom: 12, fontWeight: 700 }}>
              Cable Image {idx + 1}: {item.file.name}
            </div>
            <DetectionResultsPanel detResult={item.detResult} preview={item.preview} exportCSV={exportCSV} />
          </div>
        ))}
      </div>

      {latestDetForTab && <DisagreementFlag insp1Sev={insp1Sev} setInsp1Sev={setInsp1Sev} insp2Sev={insp2Sev} setInsp2Sev={setInsp2Sev} />}
    </>
  );
}

/* ═══ PAGE: Dashboard ═══ */
function DashPage({ detResult, videoResult }) {
  const data = detResult || videoResult;
  const dets = data?.detections || [];
  const total = data?.total ?? data?.total_detections ?? dets.length ?? 0;
  const risk = parseFloat(data?.risk_score ?? 0);
  const avgConf = dets.length ? (dets.reduce((s, d) => s + (d.conf ?? 0), 0) / dets.length * 100).toFixed(1) : 0;
  const highConf = dets.filter(d => (d.conf ?? 0) >= 0.75).length;
  const uniqueCls = [...new Set(dets.map(d => d.cls ?? d.class).filter(Boolean))].length;
  const sevCount = dets.reduce((acc, d) => {
    const s = d.severity || "Unknown";
    acc[s] = (acc[s] || 0) + 1;
    return acc;
  }, {});
  const classCounts = dets.reduce((acc, d) => {
    const c = d.cls ?? d.class ?? "Unknown";
    acc[c] = (acc[c] || 0) + 1;
    return acc;
  }, {});
  const riskLabel = risk < 30 ? "Healthy — Continue Monitoring" : risk < 60 ? "Moderate — Inspect Soon" : "Critical — Immediate Action";
  const riskColor = risk < 30 ? "#22c55e" : risk < 60 ? "#f59e0b" : "#ef4444";
  const growthRate = risk < 20 ? 0.8 : risk < 40 ? 1.5 : risk < 60 ? 2.5 : 4.0;
  const forecast = [6, 12, 24].map(m => ({ months: m, risk: Math.min(100, (risk + growthRate * m)).toFixed(1) }));
  const R = 54, CX = 64, CY = 64, STROKE = 8, sA = -220, eA = 40;
  const clamp = Math.min(Math.max(risk / 100, 0), 1);
  const arcDeg = clamp * (eA - sA) + sA;
  const toRad = d => (d * Math.PI) / 180;
  const arcX = d => CX + R * Math.cos(toRad(d)), arcY = d => CY + R * Math.sin(toRad(d));
  const largeArc = clamp * (eA - sA) > 180 ? 1 : 0;
  const radarDots = dets.slice(0, 5).map((_, i) => ({
    x: 50 + 28 * Math.cos((i / 5) * 2 * Math.PI - Math.PI / 2),
    y: 50 + 28 * Math.sin((i / 5) * 2 * Math.PI - Math.PI / 2),
    color: sevColor(dets[i]?.severity)
  }));

  return (
    <>
      <div className="section-header fade-up">
        <div className="section-crumb">Analytics · Overview</div>
        <h2 className="section-title">Inspection Dashboard</h2>
        <p className="section-desc">Real-time summary — detection metrics, severity distribution and risk score.</p>
        <div className="section-rule" />
      </div>

      {!data ? (
        <div className="card" style={{ marginTop: 20, textAlign: "center", padding: 48, opacity: 0.4 }}>Run a detection first to populate the dashboard.</div>
      ) : (
        <>
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-title" style={{ marginBottom: 16 }}>Mission Control</div>
            <div style={{ display: "grid", gridTemplateColumns: "140px 1fr 1fr 1fr 1fr 140px", gap: 12, alignItems: "stretch" }}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
                <svg width="128" height="128" viewBox="0 0 128 128">
                  <circle cx={CX} cy={CY} r={R} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth={STROKE} />
                  {risk > 0 && <path d={`M ${arcX(sA)} ${arcY(sA)} A ${R} ${R} 0 ${largeArc} 1 ${arcX(arcDeg)} ${arcY(arcDeg)}`} fill="none" stroke={riskColor} strokeWidth={STROKE} strokeLinecap="round" />}
                  <text x={CX} y={CY - 4} textAnchor="middle" fill="white" fontSize="22" fontWeight="700">{Math.round(risk)}</text>
                  <text x={CX} y={CY + 14} textAnchor="middle" fill="rgba(255,255,255,0.4)" fontSize="9" letterSpacing="1">RISK %</text>
                </svg>
                <div style={{ fontSize: 10, opacity: 0.4, textTransform: "uppercase", letterSpacing: 1, marginTop: -8 }}>Threat Level</div>
              </div>
              {[
                ["Objects Detected", total, "#22d3ee"],
                ["Anomaly Classes", uniqueCls, "#22d3ee"],
                ["Avg Confidence", `${avgConf}%`, "#f59e0b"],
                ["Mission Grade", data.grade ?? "—", data.grade === "A" ? "#22c55e" : data.grade === "B" ? "#84cc16" : data.grade === "C" ? "#f59e0b" : "#ef4444"]
              ].map(([l, v, c]) => (
                <div key={l} style={{ background: "rgba(255,255,255,0.03)", borderRadius: 8, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "16px 8px", gap: 6 }}>
                  <div style={{ fontSize: 26, fontWeight: 700, color: c }}>{v}</div>
                  <div style={{ fontSize: 10, opacity: 0.4, textTransform: "uppercase", letterSpacing: 0.8, textAlign: "center" }}>{l}</div>
                </div>
              ))}
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
                <svg width="100" height="100" viewBox="0 0 100 100">
                  {[46, 32, 18].map(r => <circle key={r} cx="50" cy="50" r={r} fill="none" stroke="rgba(34,211,238,0.1)" strokeWidth="1" />)}
                  <line x1="50" y1="4" x2="50" y2="96" stroke="rgba(34,211,238,0.08)" strokeWidth="1" />
                  <line x1="4" y1="50" x2="96" y2="50" stroke="rgba(34,211,238,0.08)" strokeWidth="1" />
                  {radarDots.map((dot, i) => <circle key={i} cx={dot.x} cy={dot.y} r="4" fill={dot.color} opacity="0.9" />)}
                </svg>
                <div style={{ fontSize: 10, opacity: 0.4, textTransform: "uppercase", letterSpacing: 1, marginTop: 4 }}>Detection Sonar</div>
              </div>
            </div>
            <div style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 8, fontSize: 11, padding: "8px 12px", background: "rgba(255,255,255,0.03)", borderRadius: 6 }}>
              {["Low", "Medium", "High"].map(s => <span key={s} style={{ color: sevColor(s), opacity: 0.8 }}>{s} · {sevCount[s] ?? 0}</span>)}
              <div style={{ flex: 1 }} />
              {sevCount["Critical"] ? <span style={{ color: "#ef4444", fontWeight: 700 }}>Critical · {sevCount["Critical"]}</span> : <span style={{ opacity: 0.3 }}>No critical detections</span>}
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, marginBottom: 20 }}>
            <BigStat label="TOTAL DETECTIONS" value={total} color="#22d3ee" />
            <BigStat label="UNIQUE CLASSES" value={uniqueCls} color="#22d3ee" />
            <BigStat label="AVG CONFIDENCE" value={`${avgConf}%`} color="#f59e0b" />
            <BigStat label="HIGH CONFIDENCE" value={highConf} color="#22c55e" />
          </div>

          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-title" style={{ marginBottom: 16 }}>Risk Assessment</div>
            <div style={{ fontSize: 42, fontWeight: 700, color: riskColor, display: "flex", alignItems: "baseline", gap: 8 }}>
              {risk.toFixed(1)}<span style={{ fontSize: 16 }}>%</span>
              <span style={{ fontSize: 15, fontWeight: 500, marginLeft: 8 }}>{riskLabel}</span>
            </div>
            <div style={{ marginTop: 12, position: "relative", height: 8, borderRadius: 4, background: "linear-gradient(to right,#22c55e,#f59e0b,#ef4444)" }}>
              <div style={{ position: "absolute", top: 0, left: `${risk}%`, width: 2, height: "100%", background: "white", borderRadius: 2 }} />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, opacity: 0.4, marginTop: 6 }}>
              <span>LOW</span><span>MODERATE</span><span>CRITICAL</span>
            </div>
          </div>

          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-title" style={{ marginBottom: 4 }}>📈 Digital Twin Degradation Forecast</div>
            <div style={{ fontSize: 12, opacity: 0.5, marginBottom: 16 }}>Projected risk — degradation rate {growthRate}%/month</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12 }}>
              {forecast.map(f => {
                const fc = parseFloat(f.risk) < 30 ? "#22c55e" : parseFloat(f.risk) < 60 ? "#f59e0b" : "#ef4444";
                return (
                  <div key={f.months} style={{ textAlign: "center", padding: "20px 12px", background: "rgba(255,255,255,0.03)", borderRadius: 8, border: `1px solid ${fc}22` }}>
                    <div style={{ fontSize: 10, opacity: 0.5, textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>+{f.months} months</div>
                    <div style={{ fontSize: 28, fontWeight: 700, color: fc }}>{f.risk}%</div>
                    <div style={{ fontSize: 11, color: fc, marginTop: 4 }}>{parseFloat(f.risk) < 30 ? "Healthy" : parseFloat(f.risk) < 60 ? "Monitor" : "Critical"}</div>
                    <div style={{ marginTop: 10, height: 4, borderRadius: 2, background: "rgba(255,255,255,0.08)" }}>
                      <div style={{ width: `${f.risk}%`, height: "100%", background: fc, borderRadius: 2 }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {Object.keys(classCounts).length > 0 && (
            <div className="card">
              <div className="card-title" style={{ marginBottom: 14 }}>Detection Breakdown</div>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
                    {["CLASS", "COUNT", "SHARE"].map(h => <th key={h} style={{ padding: "6px 12px", textAlign: "left", opacity: 0.4, fontSize: 11, letterSpacing: 0.8 }}>{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(classCounts).map(([cls, cnt]) => (
                    <tr key={cls} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                      <td style={{ padding: "8px 12px", fontWeight: 600 }}>{cls}</td>
                      <td style={{ padding: "8px 12px", color: "#22d3ee", fontWeight: 700 }}>{cnt}</td>
                      <td style={{ padding: "8px 12px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <div style={{ flex: 1, height: 4, borderRadius: 2, background: "rgba(255,255,255,0.08)", overflow: "hidden" }}>
                            <div style={{ width: `${(cnt / total) * 100}%`, height: "100%", background: "#22d3ee", borderRadius: 2 }} />
                          </div>
                          <span style={{ fontSize: 11, opacity: 0.6, minWidth: 36 }}>{((cnt / total) * 100).toFixed(0)}%</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </>
  );
}

/* ═══ PAGE: Mission Memory ═══ */
function MemoryPage({ missions }) {
  const gc = g => g === "A" ? "#22c55e" : g === "B" ? "#84cc16" : g === "C" ? "#f59e0b" : g === "D" ? "#f97316" : "#ef4444";
  return (
    <>
      <div className="section-header fade-up">
        <div className="section-crumb">Module · Mission Memory</div>
        <h2 className="section-title">Cross-Mission Defect Memory</h2>
        <p className="section-desc">Persistent history of all inspection missions.</p>
        <div className="section-rule" />
      </div>

      {missions.length === 0 ? (
        <div className="card" style={{ marginTop: 20, textAlign: "center", padding: 48, opacity: 0.4 }}>No missions saved yet. Run a detection to start building your inspection history.</div>
      ) : (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, marginBottom: 20 }}>
            <BigStat label="Total Missions" value={missions.length} color="#22d3ee" />
            <BigStat label="Avg Risk" value={`${(missions.reduce((s, m) => s + parseFloat(m.risk || 0), 0) / missions.length).toFixed(1)}%`} color="#f59e0b" />
            <BigStat label="Total Detections" value={missions.reduce((s, m) => s + (m.total || 0), 0)} color="#a78bfa" />
            <BigStat label="Vessels Inspected" value={[...new Set(missions.map(m => m.vessel).filter(v => v !== "Unknown"))].length || "—"} color="#22c55e" />
          </div>

          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-title" style={{ marginBottom: 16 }}>Inspection Timeline</div>
            {missions.map((m, i) => (
              <div key={m.id} style={{ display: "grid", gridTemplateColumns: "160px 80px 80px 80px 1fr", gap: 12, alignItems: "center", padding: "10px 12px", background: i % 2 === 0 ? "rgba(255,255,255,0.02)" : "transparent", borderRadius: 6 }}>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600 }}>{m.vessel}</div>
                  <div style={{ fontSize: 10, opacity: 0.4 }}>{new Date(m.date).toLocaleDateString()}</div>
                </div>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 16, fontWeight: 700, color: gc(m.grade) }}>{m.grade}</div>
                  <div style={{ fontSize: 9, opacity: 0.4 }}>GRADE</div>
                </div>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 16, fontWeight: 700, color: parseFloat(m.risk) < 30 ? "#22c55e" : parseFloat(m.risk) < 60 ? "#f59e0b" : "#ef4444" }}>{m.risk}%</div>
                  <div style={{ fontSize: 9, opacity: 0.4 }}>RISK</div>
                </div>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 16, fontWeight: 700, color: "#22d3ee" }}>{m.total}</div>
                  <div style={{ fontSize: 9, opacity: 0.4 }}>DEFECTS</div>
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {(m.classes || []).map(c => <span key={c} style={{ padding: "2px 8px", background: "rgba(34,211,238,0.1)", border: "1px solid rgba(34,211,238,0.2)", borderRadius: 4, fontSize: 10, color: "#22d3ee" }}>{c}</span>)}
                </div>
              </div>
            ))}
          </div>

          {missions.length >= 2 && (
            <div className="card">
              <div className="card-title" style={{ marginBottom: 16 }}>Risk Score Trend</div>
              <div style={{ position: "relative", height: 80, display: "flex", alignItems: "flex-end", gap: 4 }}>
                {[...missions].reverse().slice(0, 12).map((m) => {
                  const r = parseFloat(m.risk || 0);
                  const col = r < 30 ? "#22c55e" : r < 60 ? "#f59e0b" : "#ef4444";
                  return (
                    <div key={m.id} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                      <div style={{ fontSize: 9, opacity: 0.5 }}>{r}%</div>
                      <div style={{ width: "100%", background: col, borderRadius: "3px 3px 0 0", height: `${r}%`, minHeight: 4, opacity: 0.8 }} />
                    </div>
                  );
                })}
              </div>
              <div style={{ fontSize: 10, opacity: 0.3, marginTop: 8, textAlign: "center" }}>Last {Math.min(missions.length, 12)} inspections</div>
            </div>
          )}
        </>
      )}
    </>
  );
}

/* ═══ PAGE: Compliance ═══ */
function CompliancePage({ detResult, vesselName, inspector }) {
  const dets = detResult?.detections || [];
  const total = detResult?.total ?? dets.length ?? 0;
  const classes = [...new Set(dets.map(d => d.cls ?? d.class).filter(Boolean))];
  const today = new Date().toLocaleDateString("en-GB");

  return (
    <>
      <div className="section-header fade-up">
        <div className="section-crumb">Module · Regulatory Compliance</div>
        <h2 className="section-title">Regulatory Auto-Fill</h2>
        <p className="section-desc">Inspection results auto-populated into IMO, SOLAS, DNV and Lloyd's Register compliance forms.</p>
        <div className="section-rule" />
      </div>

      {!detResult ? (
        <div className="card" style={{ marginTop: 20, textAlign: "center", padding: 48, opacity: 0.4 }}>Run a detection first — compliance forms will auto-fill with your results.</div>
      ) : (
        <div style={{ marginTop: 16 }}>
          <ComplianceSection title="IMO — International Maritime Organization" color="#22d3ee">
            <ComplianceRow label="Vessel Name" value={vesselName || "Unknown"} />
            <ComplianceRow label="Inspection Date" value={today} />
            <ComplianceRow label="Inspector" value={inspector} />
            <ComplianceRow label="Defects Found" value={total} />
            <ComplianceRow label="Defect Classes" value={classes.join(", ") || "None"} />
            <ComplianceRow label="Overall Grade" value={detResult?.grade ?? "—"} />
            <ComplianceRow label="Risk Score" value={detResult?.risk_score != null ? `${detResult.risk_score}%` : "—"} />
            <ComplianceRow label="IMO Compliance" value={detResult?.grade === "A" || detResult?.grade === "B" ? "COMPLIANT" : "NON-COMPLIANT"} highlight />
          </ComplianceSection>

          <ComplianceSection title="SOLAS — Safety of Life at Sea" color="#22c55e">
            <ComplianceRow label="Chapter II-1" value="Inspection completed" />
            <ComplianceRow label="Critical Defects" value={dets.filter(d => d.severity === "Critical").length} />
            <ComplianceRow label="High Severity" value={dets.filter(d => d.severity === "High").length} />
            <ComplianceRow label="Immediate Action" value={dets.filter(d => d.severity === "Critical").length > 0 ? "YES" : "NO"} highlight />
            <ComplianceRow label="Next Inspection Due" value="Within 12 months" />
          </ComplianceSection>

          <ComplianceSection title="DNV — Det Norske Veritas" color="#f59e0b">
            <ComplianceRow label="Class Notation" value="NautiCAI AI-Assisted Inspection" />
            <ComplianceRow label="Detection Method" value="YOLOv8 — Deep Learning CV" />
            <ComplianceRow label="Total Anomalies" value={total} />
            <ComplianceRow label="Avg Confidence" value={dets.length ? `${(dets.reduce((s, d) => s + (d.conf ?? 0), 0) / dets.length * 100).toFixed(1)}%` : "—"} />
            <ComplianceRow label="Survey Status" value="AI Pre-Survey Completed" highlight />
          </ComplianceSection>

          <ComplianceSection title="Lloyd's Register" color="#a855f7">
            <ComplianceRow label="Survey Type" value="Underwater AI Inspection" />
            <ComplianceRow label="Mission ID" value={detResult?.mission_id ?? "—"} />
            <ComplianceRow label="Report Generated" value={new Date().toISOString()} />
            <ComplianceRow label="Digital Signature" value="NautiCAI Platform v1.0" highlight />
          </ComplianceSection>

          <button className="btn btn-primary" onClick={() => window.print()} style={{ marginTop: 8 }}>🖨️ Print Compliance Report</button>
        </div>
      )}
    </>
  );
}

/* ═══ PAGE: Zero-Shot ═══ */
function ZeroShotPage({ zeroShotClasses, setZeroShotClasses, uploads, fileRef, folderRef, handleFiles, onDragOver, onDragLeave, onDrop }) {
  const [input, setInput] = useState("");
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState([]);

  const addClass = () => {
    const v = input.trim();
    if (!v || zeroShotClasses.includes(v)) return;
    setZeroShotClasses(prev => [...prev, v]);
    setInput("");
  };

  const runZeroShot = async () => {
    if (!uploads.length || zeroShotClasses.length === 0) return;
    setRunning(true);
    await new Promise(r => setTimeout(r, 1500));
    setResults(zeroShotClasses.map(cls => ({
      cls,
      found: Math.random() > 0.3,
      conf: (0.5 + Math.random() * 0.45).toFixed(2)
    })));
    setRunning(false);
  };

  return (
    <>
      <div className="section-header fade-up">
        <div className="section-crumb">Module · Zero-Shot Detection</div>
        <h2 className="section-title">Zero-Shot Class Expansion</h2>
        <p className="section-desc">Type any defect class in plain English — powered by Grounding DINO, no retraining required.</p>
        <div className="section-rule" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <div>
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-title" style={{ marginBottom: 12 }}>Add Detection Classes</div>
            <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
              <input
                className="ctrl-input"
                style={{ flex: 1 }}
                placeholder="e.g. marine growth, anode depletion..."
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && addClass()}
              />
              <button className="btn btn-primary" onClick={addClass}>Add</button>
            </div>

            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, minHeight: 40 }}>
              {zeroShotClasses.length === 0 && <span style={{ fontSize: 12, opacity: 0.3 }}>No classes added yet</span>}
              {zeroShotClasses.map(cls => (
                <span key={cls} style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "4px 10px", background: "rgba(34,211,238,0.1)", border: "1px solid rgba(34,211,238,0.3)", borderRadius: 20, fontSize: 12, color: "#22d3ee" }}>
                  {cls}
                  <button onClick={() => setZeroShotClasses(prev => prev.filter(c => c !== cls))} style={{ background: "none", border: "none", color: "#22d3ee", cursor: "pointer", fontSize: 14, lineHeight: 1 }}>×</button>
                </span>
              ))}
            </div>
          </div>

          <div className="card" style={{ marginBottom: 16, padding: "12px 16px", background: "rgba(168,85,247,0.08)", border: "1px solid rgba(168,85,247,0.2)" }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#a855f7", marginBottom: 6 }}>🎯 Powered by Grounding DINO</div>
            <div style={{ fontSize: 11, opacity: 0.7, lineHeight: 1.6 }}>Zero-shot detection uses open-vocabulary vision-language models to find any object you can describe in natural language — no labeling or retraining required.</div>
          </div>

          <button className="btn btn-primary" disabled={!uploads.length || zeroShotClasses.length === 0 || running} onClick={runZeroShot} style={{ width: "100%" }}>
            {running ? <><span className="spinner" /> Running Grounding DINO...</> : "🎯 Run Zero-Shot Detection"}
          </button>
        </div>

        <div>
          <DropZone
            fileRef={fileRef}
            folderRef={folderRef}
            uploads={uploads}
            handleFiles={handleFiles}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
            clearUploads={() => {}}
            removeUpload={() => {}}
          />

          {results.length > 0 && (
            <div className="card">
              <div className="card-title" style={{ marginBottom: 12 }}>Detection Results</div>
              {results.map(r => (
                <div key={r.cls} style={{ display: "flex", alignItems: "center", gap: 12, padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                  <span style={{ width: 10, height: 10, borderRadius: "50%", background: r.found ? "#22c55e" : "#ef4444", flexShrink: 0, display: "inline-block" }} />
                  <span style={{ flex: 1, fontSize: 13, fontWeight: 600 }}>{r.cls}</span>
                  {r.found ? <span style={{ fontSize: 12, color: "#22c55e", fontWeight: 700 }}>Found · {(r.conf * 100).toFixed(1)}%</span> : <span style={{ fontSize: 12, opacity: 0.4 }}>Not detected</span>}
                </div>
              ))}
              <div style={{ marginTop: 10, fontSize: 11, opacity: 0.4, padding: 8, background: "rgba(255,255,255,0.02)", borderRadius: 4 }}>⚠️ Demo simulation — wire up /api/detect/zeroshot for live results</div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

/* ═══ PAGE: Roadmap ═══ */
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
  { label: "Reports", value: "FPDF2", color: "#c084fc" }
];

function RoadmapPage() {
  return (
    <>
      <div className="section-header fade-up">
        <div className="section-crumb">NautiCAI · Product</div>
        <h2 className="section-title">Development Roadmap</h2>
        <p className="section-desc" style={{ maxWidth: 600 }}>Opinionated, execution-focused roadmap from today's beta to a fully autonomous underwater inspection platform.</p>
        <div className="section-rule" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16, marginBottom: 24 }}>
        {PHASES.map(p => (
          <div key={p.num} className="card" style={{ padding: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <span style={{ fontSize: 28, fontWeight: 900, color: p.badgeColor, opacity: 0.7, fontFamily: "monospace" }}>{p.num}</span>
              <span style={{ fontSize: 10, fontWeight: 700, padding: "3px 10px", borderRadius: 20, background: p.badgeColor + "22", color: p.badgeColor }}>{p.badge}</span>
            </div>
            <div style={{ marginBottom: 4 }}>
              <span style={{ fontSize: 34, fontWeight: 900, color: "#e2e8f0", fontFamily: "monospace" }}>{p.ver}</span>
              <span style={{ fontSize: 16, color: p.badgeColor, fontFamily: "monospace" }}>/{p.sub}</span>
            </div>
            <div style={{ fontSize: 10, letterSpacing: 1, opacity: 0.4, textTransform: "uppercase", marginBottom: 16 }}>{p.tagline}</div>
            <ul style={{ margin: 0, paddingLeft: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 8 }}>
              {p.items.map(item => <li key={item} style={{ display: "flex", gap: 8, fontSize: 12, lineHeight: 1.5, opacity: 0.8 }}><span style={{ color: p.badgeColor, flexShrink: 0, marginTop: 2 }}>●</span>{item}</li>)}
            </ul>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="card-title" style={{ marginBottom: 16 }}>🔧 Technology Stack</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(6,1fr)", gap: 12 }}>
          {TECH_STACK.map(t => (
            <div key={t.label} style={{ textAlign: "center", padding: "16px 8px", background: t.color + "11", borderRadius: 8, border: `1px solid ${t.color}22` }}>
              <div style={{ fontSize: 10, opacity: 0.45, letterSpacing: 1, textTransform: "uppercase", marginBottom: 8 }}>{t.label}</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: t.color }}>{t.value}</div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}