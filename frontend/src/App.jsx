import React, { useState, useRef, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { getHealth, runDetection, runEnhance, downloadPDF, downloadVideoPDF, runVideoDetection, sendPDFToWhatsApp, sendVideoPDFToWhatsApp, sendWhatsAppMessage } from "./api";

/* ─────────── tab list ─────────── */
const TABS = [
  { id: "scan",     icon: "🔬", label: "Anomaly Scan" },
  { id: "hull",     icon: "🚢", label: "Hull Inspect" },
  { id: "video",    icon: "🎬", label: "Video Analysis" },
  { id: "pipeline", icon: "🔧", label: "Pipeline" },
  { id: "cable",    icon: "⚡", label: "Sub-sea Cable" },
  { id: "dash",     icon: "📊", label: "Dashboard" },
  { id: "road",     icon: "🗺️", label: "Roadmap" },
];

/* page transition variants */
const pgVar = {
  enter:   { opacity: 0, y: 20 },
  center:  { opacity: 1, y: 0, transition: { duration: 0.3, ease: [0.4, 0, 0.2, 1] } },
  exit:    { opacity: 0, y: -12, transition: { duration: 0.15 } },
};

/* ═══════════════════════════════════════════════════
   Main App
   ═══════════════════════════════════════════════════ */
export default function App() {
  const [tab, setTab]         = useState("scan");
  const [health, setHealth]   = useState(null);
  const [file, setFile]       = useState(null);
  const [preview, setPreview] = useState(null);

  /* detection params */
  const [conf, setConf]       = useState(0.25);
  const [iou, setIou]         = useState(0.45);
  const [sevFilter, setSevFilter] = useState("All Detections");

  /* enhancement flags */
  const [clahe, setClahe]           = useState(true);
  const [claheClip, setClaheClip]   = useState(3.0);
  const [green, setGreen]           = useState(true);
  const [edge, setEdge]             = useState(false);
  const [turbLevel, setTurbLevel]   = useState(0.0);
  const [corrTurb, setCorrTurb]     = useState(true);
  const [marineSnow, setMarineSnow] = useState(false);

  /* mission info */
  const [vesselName, setVesselName]   = useState("");
  const [inspector, setInspector]     = useState("NautiCAI AutoScan v1.0");
  const [inspMode, setInspMode]       = useState("general");
  const [reportPassword, setReportPassword] = useState("");

  /* results */
  const [loading, setLoading]   = useState(false);
  const [detResult, setDetResult] = useState(null);
  const [enhResult, setEnhResult] = useState(null);
  const [error, setError]        = useState("");

  /* video */
  const [videoFile, setVideoFile] = useState(null);
  const [videoLoading, setVideoLoading] = useState(false);
  const [videoResult, setVideoResult]  = useState(null);

  /* demo gate: user from signup (sessionStorage) */
  const [demoUser, setDemoUser] = useState(() => {
    try {
      const u = sessionStorage.getItem("nauticai-demo-user");
      return u ? JSON.parse(u) : null;
    } catch { return null; }
  });
  const [sendingWa, setSendingWa] = useState(false);
  const [waMessage, setWaMessage] = useState("");
  const [reportsGenerated, setReportsGenerated] = useState(0);
  const [sessionDetections, setSessionDetections] = useState(0);
  const [completionAlertSent, setCompletionAlertSent] = useState(false);

  /* Demo gate: redirect to signup if no access */
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("demo") === "1") {
      const name = params.get("name");
      const email = params.get("email");
      const whatsapp = params.get("whatsapp");
      if (name || email || whatsapp) {
        const user = { name: name || "", email: email || "", whatsapp: whatsapp || "" };
        sessionStorage.setItem("nauticai-demo-access", "1");
        sessionStorage.setItem("nauticai-demo-user", JSON.stringify(user));
        setDemoUser(user);
        window.history.replaceState({}, "", window.location.pathname);
      }
    }
    const hasAccess = sessionStorage.getItem("nauticai-demo-access") === "1";
    if (!hasAccess && !params.get("demo")) {
      const gate = process.env.REACT_APP_DEMO_GATE_URL || (window.location.port === "3000" ? "http://localhost:8080/demo.html" : "/demo.html");
      window.location.href = gate;
    }
  }, []);

  /* health poll */
  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth({ status: "offline" }));
    const t = setInterval(() => {
      getHealth().then(setHealth).catch(() => setHealth({ status: "offline" }));
    }, 30000);
    return () => clearInterval(t);
  }, []);

  /* file picker */
  const fileRef  = useRef();
  const videoRef = useRef();

  const handleFile = useCallback((f) => {
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setDetResult(null);
    setEnhResult(null);
    setError("");
  }, []);

  /* drag helpers */
  const onDragOver = (e) => { e.preventDefault(); e.currentTarget.classList.add("drag-over"); };
  const onDragLeave = (e) => { e.currentTarget.classList.remove("drag-over"); };
  const onDrop = (e) => { e.preventDefault(); e.currentTarget.classList.remove("drag-over"); handleFile(e.dataTransfer.files[0]); };

  /* ── Run Detection ── */
  const detect = async () => {
    if (!file) return;
    setLoading(true); setError(""); setCompletionAlertSent(false);
    try {
      const data = await runDetection(file, detParams());
      setDetResult(data);
      setSessionDetections((n) => n + (data.total || data.detections?.length || 0));
    } catch (e) { setError(e.response?.data?.detail || e.message); }
    setLoading(false);
  };

  /* shared param builder */
  const detParams = () => ({
    conf_thr: conf, iou_thr: iou, mode: inspMode, sev_filter: sevFilter,
    use_clahe: clahe, clahe_clip: claheClip, use_green: green,
    use_edge: edge, turbidity_in: turbLevel, corr_turb: corrTurb, marine_snow: marineSnow,
  });
  const enhParams = () => ({
    use_clahe: clahe, clahe_clip: claheClip, use_green: green,
    use_edge: edge, turbidity_in: turbLevel, corr_turb: corrTurb, marine_snow: marineSnow,
  });

  /* ── Run Enhancement ── */
  const enhance = async () => {
    if (!file) return;
    setLoading(true); setError("");
    try {
      const data = await runEnhance(file, enhParams());
      setEnhResult(data);
    } catch (e) { setError(e.response?.data?.detail || e.message); }
    setLoading(false);
  };

  /* ── Run Both ── */
  const runBoth = async () => {
    if (!file) return;
    setLoading(true); setError(""); setCompletionAlertSent(false);
    try {
      const [det, enh] = await Promise.all([
        runDetection(file, detParams()),
        runEnhance(file, enhParams()),
      ]);
      setDetResult(det);
      setEnhResult(enh);
      setSessionDetections((n) => n + (det.total || det.detections?.length || 0));
    } catch (e) { setError(e.response?.data?.detail || e.message); }
    setLoading(false);
  };

  /* ── PDF ── */
  const genPDF = async () => {
    if (!file) return;
    setError("");
    try {
      await downloadPDF(file, { ...detParams(), vessel_name: vesselName || "Unknown", inspector, pdf_password: reportPassword });
      setReportsGenerated((n) => n + 1);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  };

  /* ── Video PDF ── */
  const genVideoPDF = async () => {
    if (!videoFile) return;
    setError("");
    try {
      await downloadVideoPDF(videoFile, {
        conf_thr: conf, iou_thr: iou, mode: inspMode,
        vessel_name: vesselName || "Unknown", inspector,
        sample_n: 10, use_clahe: clahe, clahe_clip: claheClip,
        use_green: green, use_edge: edge, turbidity_in: turbLevel, corr_turb: corrTurb,
        pdf_password: reportPassword,
      });
      setReportsGenerated((n) => n + 1);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  };

  /* ── Send PDF to WhatsApp ── */
  const sendPDFToWa = async () => {
    if (!file) return;
    const to = demoUser?.whatsapp?.trim();
    if (!to) {
      setWaMessage("Add your WhatsApp number at signup to receive reports.");
      setTimeout(() => setWaMessage(""), 4000);
      return;
    }
    setSendingWa(true);
    setWaMessage("");
    setError("");
    try {
      const res = await sendPDFToWhatsApp(file, {
        ...detParams(),
        vessel_name: vesselName || "Unknown",
        inspector,
        to,
        pdf_password: reportPassword,
      });
      if (res.sent) {
        setWaMessage("Report sent to your WhatsApp.");
      } else {
        const msg = res.message || "Could not send.";
        setWaMessage(msg.indexOf("not configured") !== -1 || msg.indexOf("TWILIO") !== -1
          ? "WhatsApp not set up. Add Twilio credentials to the backend (see WHATSAPP_SETUP.md) and restart."
          : msg);
      }
    } catch (e) {
      setWaMessage(e.response?.data?.message || e.message || "Send failed.");
    }
    setSendingWa(false);
  };

  const sendVideoPDFToWa = async () => {
    if (!videoFile) return;
    const to = demoUser?.whatsapp?.trim();
    if (!to) {
      setWaMessage("Add your WhatsApp number at signup to receive reports.");
      setTimeout(() => setWaMessage(""), 4000);
      return;
    }
    setSendingWa(true);
    setWaMessage("");
    setError("");
    try {
      const res = await sendVideoPDFToWhatsApp(videoFile, {
        conf_thr: conf, iou_thr: iou, mode: inspMode,
        vessel_name: vesselName || "Unknown", inspector,
        sample_n: 10, use_clahe: clahe, clahe_clip: claheClip,
        use_green: green, use_edge: edge, turbidity_in: turbLevel, corr_turb: corrTurb,
        to,
        pdf_password: reportPassword,
      });
      if (res.sent) {
        setWaMessage("Video report sent to your WhatsApp.");
      } else {
        const msg = res.message || "Could not send.";
        setWaMessage(msg.indexOf("not configured") !== -1 || msg.indexOf("TWILIO") !== -1
          ? "WhatsApp not set up. Add Twilio credentials to the backend (see WHATSAPP_SETUP.md) and restart."
          : msg);
      }
    } catch (e) {
      setWaMessage(e.response?.data?.message || e.message || "Send failed.");
    }
    setSendingWa(false);
  };

  /* ── Video ── */
  const analyzeVideo = async () => {
    if (!videoFile) return;
    setVideoLoading(true); setError(""); setCompletionAlertSent(false);
    try {
      const data = await runVideoDetection(videoFile, { conf_thr: conf, iou_thr: iou, mode: inspMode, sample_n: 10, use_clahe: clahe, clahe_clip: claheClip, use_green: green, use_edge: edge, turbidity_in: turbLevel, corr_turb: corrTurb });
      setVideoResult(data);
      setSessionDetections((n) => n + (data.total_detections || data.detections?.length || 0));
    } catch (e) { setError(e.response?.data?.detail || e.message); }
    setVideoLoading(false);
  };

  /* ── Send completion alert to WhatsApp ── */
  const sendCompletionAlert = async (source = "image") => {
    const to = demoUser?.whatsapp?.trim();
    if (!to) {
      setWaMessage("Add your WhatsApp number at signup for completion alerts.");
      setTimeout(() => setWaMessage(""), 4000);
      return;
    }
    const data = source === "video" ? videoResult : detResult;
    if (!data) return;
    const risk = data.risk_score;
    const grade = data.grade;
    const total = data.total ?? data.detections?.length ?? data.total_detections ?? 0;
    const msg = `NautiCAI inspection complete. Risk: ${risk ?? "—"} · Grade: ${grade ?? "—"} · ${total} detection(s). View in demo.`;
    setSendingWa(true);
    setWaMessage("");
    try {
      const res = await sendWhatsAppMessage(to.replace(/\s/g, ""), msg);
      if (res.sent) {
        setWaMessage("Completion alert sent to WhatsApp.");
        setCompletionAlertSent(true);
      } else {
        const msg = res.message || "Could not send.";
        setWaMessage(msg.indexOf("not configured") !== -1 || msg.indexOf("TWILIO") !== -1
          ? "WhatsApp not set up. Add Twilio credentials to the backend (see WHATSAPP_SETUP.md) and restart."
          : msg);
      }
    } catch (e) {
      setWaMessage(e.response?.data?.message || e.message || "Send failed.");
    }
    setSendingWa(false);
  };

  /* ── Export detections as CSV ── */
  const exportDetectionsCSV = (data) => {
    const dets = data?.detections || [];
    if (!dets.length) return;
    const headers = ["id", "class", "confidence", "severity", "bbox"];
    const rows = dets.map((d) => [
      d.id ?? "",
      d.cls ?? "",
      (d.conf != null ? Number(d.conf).toFixed(4) : ""),
      d.severity ?? "",
      [d.bbox?.xmin, d.bbox?.ymin, d.bbox?.xmax, d.bbox?.ymax].filter((x) => x != null).join(" "),
    ]);
    const csv = [headers.join(","), ...rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `NautiCAI_detections_${data?.mission_id || "export"}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  /* ── Keyboard shortcut: Ctrl+Enter runs detection ── */
  useEffect(() => {
    const onKey = (e) => {
      if (!e.ctrlKey || e.key !== "Enter") return;
      e.preventDefault();
      if (tab === "scan" && file) runBoth();
      else if ((tab === "hull" || tab === "pipeline" || tab === "cable") && file) detect();
      else if (tab === "video" && videoFile) analyzeVideo();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [tab, file, videoFile]);

  /* ═══════════ RENDER ═══════════ */
  return (
    <>
      <div className="app-shell">
        {/* ──────── Sidebar ──────── */}
        <aside className="sidebar">
          {/* brand */}
          <div className="sb-brand">
            <img className="sb-logo" src="/nauticai-logo.png" alt="NautiCAI" />
            <div className="sb-brand-text">
              <h3>NAUTICAI</h3>
              <a href="https://www.nauticai-ai.com" target="_blank" rel="noreferrer">
                www.nauticai-ai.com
              </a>
            </div>
          </div>

          {/* status */}
          <div className="sb-status">
            <span className="pill">
              <span className={`dot ${health?.status === "ok" ? "dot-ok" : "dot-warn"}`} />
              {health?.status === "ok" ? "API Online" : "API Offline"}
            </span>
            {health?.model && (
              <span className="pill">
                <span className="dot dot-ok" />
                {health.model}
              </span>
            )}
          </div>

          {/* Detection Engine */}
          <div className="sb-section">
            <div className="sb-label">Detection Engine</div>
            <div className="ctrl">
              <div className="ctrl-header">
                <label>Confidence Threshold</label>
                <span>{conf.toFixed(2)}</span>
              </div>
              <input type="range" className="ctrl-slider" min={0.05} max={0.95} step={0.05}
                value={conf} onChange={e => setConf(+e.target.value)} />
            </div>
            <div className="ctrl">
              <div className="ctrl-header">
                <label>IoU Threshold</label>
                <span>{iou.toFixed(2)}</span>
              </div>
              <input type="range" className="ctrl-slider" min={0.1} max={0.9} step={0.05}
                value={iou} onChange={e => setIou(+e.target.value)} />
            </div>
          </div>

          <div className="sb-sep" />

          {/* Severity Filter */}
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

          {/* Visibility Engine */}
          <div className="sb-section">
            <div className="sb-label">Visibility Engine</div>
            <label className="ctrl-toggle">
              <span className="tgl">
                <input type="checkbox" checked={clahe} onChange={() => setClahe(!clahe)} />
                <span className="tgl-track" /><span className="tgl-knob" />
              </span>
              <span>CLAHE Enhancement</span>
            </label>
            {clahe && (
              <div className="ctrl">
                <div className="ctrl-header">
                  <label>CLAHE Clip Limit</label>
                  <span>{claheClip.toFixed(2)}</span>
                </div>
                <input type="range" className="ctrl-slider" min={1.0} max={10.0} step={0.5}
                  value={claheClip} onChange={e => setClaheClip(+e.target.value)} />
              </div>
            )}
            <label className="ctrl-toggle">
              <span className="tgl">
                <input type="checkbox" checked={green} onChange={() => setGreen(!green)} />
                <span className="tgl-track" /><span className="tgl-knob" />
              </span>
              <span>Green-Water Filter</span>
            </label>
            <label className="ctrl-toggle">
              <span className="tgl">
                <input type="checkbox" checked={edge} onChange={() => setEdge(!edge)} />
                <span className="tgl-track" /><span className="tgl-knob" />
              </span>
              <span>Edge Estimator</span>
            </label>
            <div className="ctrl">
              <div className="ctrl-header">
                <label>Turbidity Level</label>
                <span>{turbLevel.toFixed(2)}</span>
              </div>
              <input type="range" className="ctrl-slider" min={0} max={1.0} step={0.05}
                value={turbLevel} onChange={e => setTurbLevel(+e.target.value)} />
            </div>
            <label className="ctrl-toggle">
              <span className="tgl">
                <input type="checkbox" checked={corrTurb} onChange={() => setCorrTurb(!corrTurb)} />
                <span className="tgl-track" /><span className="tgl-knob" />
              </span>
              <span>Turbidity Correction</span>
            </label>
            <label className="ctrl-toggle">
              <span className="tgl">
                <input type="checkbox" checked={marineSnow} onChange={() => setMarineSnow(!marineSnow)} />
                <span className="tgl-track" /><span className="tgl-knob" />
              </span>
              <span>Marine Snow</span>
            </label>
          </div>

          <div className="sb-sep" />

          {/* Mission Info */}
          <div className="sb-section">
            <div className="sb-label">Mission Info</div>
            <div className="ctrl">
              <div className="ctrl-header"><label>Vessel Name</label></div>
              <input type="text" className="ctrl-input" placeholder="e.g. MV Neptune Star"
                value={vesselName} onChange={e => setVesselName(e.target.value)} />
            </div>
            <div className="ctrl">
              <div className="ctrl-header"><label>Inspector</label></div>
              <input type="text" className="ctrl-input"
                value={inspector} onChange={e => setInspector(e.target.value)} />
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
              <div className="ctrl-header"><label>Report password (optional)</label></div>
              <input type="password" className="ctrl-input" placeholder="Encrypt PDF &amp; protect data"
                value={reportPassword} onChange={e => setReportPassword(e.target.value)} autoComplete="off" />
              <small className="ctrl-hint">PDFs and WhatsApp reports will require this password to open.</small>
            </div>
          </div>

          {/* footer */}
          <div className="sb-footer">
            <img src="/nauticai-logo.png" alt="" />
            <a href="https://www.nauticai-ai.com" target="_blank" rel="noreferrer">www.nauticai-ai.com</a>
            <small>© 2025 NautiCAI Pte Ltd · Singapore</small>
          </div>
        </aside>

        {/* ──────── Main Area ──────── */}
        <div className="main-area">
          {/* Topbar */}
          <header className="topbar">
            <div className="topbar-left">
              <img className="topbar-logo" src="/nauticai-logo.png" alt="NautiCAI" />
              <div className="topbar-title">
                <h1>NAUTICAI</h1>
                <p>Deep-sea Anomaly Detection Platform</p>
              </div>
            </div>
            <div className="topbar-right">
              <span className="topbar-chip" title="Session stats">
                📄 {reportsGenerated} reports · 🔍 {sessionDetections} detections
              </span>
              <span className="topbar-chip topbar-kbd" title="Keyboard shortcut">Ctrl+Enter Run</span>
              <a href={process.env.REACT_APP_DEMO_GATE_URL || (window.location.port === "3000" ? "http://localhost:8080/demo.html" : "/demo.html")} target="_blank" rel="noopener noreferrer" className="btn btn-primary btn-sm" style={{ textDecoration: "none", color: "inherit" }}>
                Book a demo
              </a>
            </div>
          </header>

          {/* Tab nav */}
          <div className="tab-bar">
            {TABS.map(t => (
              <button key={t.id}
                className={`tab-btn ${tab === t.id ? "active" : ""}`}
                onClick={() => setTab(t.id)}>
                <span className="tab-icon">{t.icon}</span>{t.label}
              </button>
            ))}
          </div>

          {/* Page content */}
          <AnimatePresence mode="wait">
            <motion.div key={tab} className="page-content"
              variants={pgVar} initial="enter" animate="center" exit="exit">
              {tab === "scan" && <ScanPage
                file={file} preview={preview} fileRef={fileRef} handleFile={handleFile}
                onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}
                detect={detect} enhance={enhance} runBoth={runBoth} genPDF={genPDF}
                sendPDFToWa={sendPDFToWa} sendCompletionAlert={sendCompletionAlert} completionAlertSent={completionAlertSent}
                sendingWa={sendingWa} waMessage={waMessage} exportCSV={exportDetectionsCSV}
                loading={loading} detResult={detResult} enhResult={enhResult} error={error}
              />}
              {tab === "hull" && <HullPage
                file={file} preview={preview} fileRef={fileRef} handleFile={handleFile}
                onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}
                detect={detect} genPDF={genPDF} sendPDFToWa={sendPDFToWa} sendCompletionAlert={sendCompletionAlert}
                completionAlertSent={completionAlertSent} sendingWa={sendingWa} waMessage={waMessage} exportCSV={exportDetectionsCSV}
                loading={loading} detResult={detResult} error={error}
              />}
              {tab === "video" && <VideoPage
                videoFile={videoFile} videoRef={videoRef} setVideoFile={setVideoFile}
                onDragOver={onDragOver} onDragLeave={onDragLeave}
                analyzeVideo={analyzeVideo} genVideoPDF={genVideoPDF} sendVideoPDFToWa={sendVideoPDFToWa}
                sendCompletionAlert={sendCompletionAlert} completionAlertSent={completionAlertSent}
                videoLoading={videoLoading} sendingWa={sendingWa} waMessage={waMessage}
                videoResult={videoResult} error={error}
              />}
              {tab === "pipeline" && <PipelinePage
                file={file} preview={preview} handleFile={handleFile}
                onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}
                detect={detect} genPDF={genPDF} sendPDFToWa={sendPDFToWa} sendCompletionAlert={sendCompletionAlert}
                completionAlertSent={completionAlertSent} sendingWa={sendingWa} waMessage={waMessage} exportCSV={exportDetectionsCSV}
                loading={loading} detResult={detResult} error={error}
              />}
              {tab === "cable" && <CablePage
                file={file} preview={preview} handleFile={handleFile}
                onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}
                detect={detect} genPDF={genPDF} sendPDFToWa={sendPDFToWa} sendCompletionAlert={sendCompletionAlert}
                completionAlertSent={completionAlertSent} sendingWa={sendingWa} waMessage={waMessage} exportCSV={exportDetectionsCSV}
                loading={loading} detResult={detResult} error={error}
              />}
              {tab === "dash" && <DashPage detResult={detResult} />}
              {tab === "road" && <RoadmapPage />}
            </motion.div>
          </AnimatePresence>

          {/* Footer */}
          <footer className="app-footer">
            <img src="/nauticai-logo.png" alt="" />
            <span className="footer-dot">·</span>
            <a href="https://www.nauticai-ai.com" target="_blank" rel="noreferrer">www.nauticai-ai.com</a>
            <span className="footer-dot">·</span>
            <span>NautiCAI v1.0 — Deep-tech Venture · Singapore</span>
          </footer>
        </div>
      </div>
    </>
  );
}

/* ═══════════════════════════════════════════════════
   PAGE: Anomaly Scan
   ═══════════════════════════════════════════════════ */
function ScanPage({ file, preview, fileRef, handleFile, onDragOver, onDragLeave, onDrop,
                    detect, enhance, runBoth, genPDF, sendPDFToWa, sendCompletionAlert, completionAlertSent,
                    sendingWa, waMessage, exportCSV, loading, detResult, enhResult, error }) {
  return (
    <>
      <div className="section-header fade-up">
        <div className="section-crumb">Module · Anomaly Detection</div>
        <h2 className="section-title">Underwater Anomaly Scan</h2>
        <p className="section-desc">
          Upload an underwater image to run AI-powered anomaly detection, visibility enhancement, and generate PDF reports.
        </p>
        <div className="section-rule" />
      </div>

      {/* Upload */}
      <div className="card mb-20">
        <div className="card-title">Image Upload</div>
        <div className="dropzone" onClick={() => fileRef.current?.click()}
             onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}>
          <div className="dz-icon">📷</div>
          <div className="dz-label">
            {preview ? "Click or drop to replace" : "Drop underwater image here, or click to browse"}
          </div>
          <div className="dz-hint">Supported: JPG, PNG, BMP · Max 20 MB</div>
          {file && <div className="dz-file">✓ {file.name}</div>}
        </div>
        <input ref={fileRef} type="file" accept="image/*" hidden
          onChange={e => handleFile(e.target.files[0])} />
      </div>

      {/* Action buttons */}
      <div className="row mb-20" style={{ gap: 10, flexWrap: "wrap" }}>
        <button className="btn btn-primary" disabled={!file || loading} onClick={detect}>
          {loading ? <span className="spinner" /> : null}
          Run Detection
        </button>
        <button className="btn btn-ghost" disabled={!file || loading} onClick={enhance}>
          Enhance Visibility
        </button>
        <button className="btn btn-primary" disabled={!file || loading} onClick={runBoth}>
          Detect + Enhance
        </button>
        <button className="btn btn-ghost" disabled={!file} onClick={genPDF}>
          📄 PDF Report
        </button>
        <button className="btn btn-ghost" disabled={!file || sendingWa} onClick={sendPDFToWa} title="Send report to your WhatsApp">
          {sendingWa ? "…" : "📱 Send to WhatsApp"}
        </button>
        {detResult && (
          <>
            <button className="btn btn-ghost" disabled={sendingWa || completionAlertSent} onClick={() => sendCompletionAlert("image")} title="Alert my WhatsApp when inspection is done">
              {completionAlertSent ? "✓ Alert sent" : "🔔 Completion alert"}
            </button>
            <button className="btn btn-ghost" onClick={() => exportCSV(detResult)} title="Export detections as CSV">
              📊 Export CSV
            </button>
          </>
        )}
      </div>
      {waMessage && <div className="alert alert-info">{waMessage}</div>}
      {error && <div className="alert alert-warn">⚠️ {error}</div>}

      {/* Results */}
      {!detResult && !enhResult && preview && (
        <div className="card">
          <div className="card-title">Original Image</div>
          <div className="image-frame">
            <img src={preview} alt="original" />
          </div>
        </div>
      )}

      {detResult && <DetectionResults data={detResult} preview={preview} />}
      {enhResult && <EnhancementResults data={enhResult} />}
    </>
  );
}

/* ═══════════════════════════════════════════════════
   PAGE: Hull Inspect
   ═══════════════════════════════════════════════════ */
function HullPage({ file, preview, fileRef, handleFile, onDragOver, onDragLeave, onDrop,
                    detect, genPDF, sendPDFToWa, sendCompletionAlert, completionAlertSent,
                    sendingWa, waMessage, exportCSV, loading, detResult, error }) {
  return (
    <>
      <div className="section-header fade-up">
        <div className="section-crumb">Module · Hull Inspection</div>
        <h2 className="section-title">Hull & Structure Analysis</h2>
        <p className="section-desc">
          Inspect vessel hulls for biofouling, marine growth, corrosion, and structural anomalies across 9 zones.
        </p>
        <div className="section-rule" />
      </div>

      <div className="card mb-20">
        <div className="card-title">Upload Hull Image</div>
        <div className="dropzone" onClick={() => fileRef.current?.click()}
             onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}>
          <div className="dz-icon">🚢</div>
          <div className="dz-label">{preview ? "Replace image" : "Drop hull image here"}</div>
          <div className="dz-hint">Hull, Propeller, Rudder, Sea-chest, Thruster, etc.</div>
          {file && <div className="dz-file">✓ {file.name}</div>}
        </div>
        <input ref={fileRef} type="file" accept="image/*" hidden
          onChange={e => handleFile(e.target.files[0])} />
      </div>

      <div className="row mb-20" style={{ gap: 10, flexWrap: "wrap" }}>
        <button className="btn btn-primary" disabled={!file || loading} onClick={detect}>
          {loading ? <span className="spinner" /> : null}
          Analyze Hull
        </button>
        <button className="btn btn-ghost" disabled={!file} onClick={genPDF}>
          📄 PDF Report
        </button>
        <button className="btn btn-ghost" disabled={!file || sendingWa} onClick={sendPDFToWa} title="Send to WhatsApp">
          {sendingWa ? "…" : "📱 Send to WhatsApp"}
        </button>
        {detResult && (
          <>
            <button className="btn btn-ghost" disabled={sendingWa || completionAlertSent} onClick={() => sendCompletionAlert("image")}>🔔 Completion alert</button>
            <button className="btn btn-ghost" onClick={() => exportCSV(detResult)}>📊 Export CSV</button>
          </>
        )}
      </div>
      {waMessage && <div className="alert alert-info">{waMessage}</div>}
      {error && <div className="alert alert-warn">⚠️ {error}</div>}
      {detResult && <DetectionResults data={detResult} preview={preview} />}
      {!detResult && (
        <div className="empty-state">
          <div className="es-icon">🚢</div>
          <div className="es-text">Upload a hull image and click <strong>Analyze Hull</strong> to get started.</div>
        </div>
      )}
    </>
  );
}

/* ═══════════════════════════════════════════════════
   PAGE: Video Analysis
   ═══════════════════════════════════════════════════ */
function VideoPage({ videoFile, videoRef, setVideoFile, onDragOver, onDragLeave,
                     analyzeVideo, genVideoPDF, sendVideoPDFToWa, sendCompletionAlert, completionAlertSent,
                     videoLoading, sendingWa, waMessage, videoResult, error }) {
  const handleVid = (e) => { const f = e.dataTransfer?.files[0] || e.target?.files[0]; if(f) setVideoFile(f); };
  return (
    <>
      <div className="section-header fade-up">
        <div className="section-crumb">Module · Video Intelligence</div>
        <h2 className="section-title">ROV Video Analysis</h2>
        <p className="section-desc">
          Upload ROV / AUV footage for frame-by-frame anomaly detection — up to 20 keyframes analysed per clip.
        </p>
        <div className="section-rule" />
      </div>

      <div className="card mb-20">
        <div className="card-title">Video Upload</div>
        <div className="dropzone"
          onClick={() => videoRef.current?.click()}
          onDragOver={onDragOver} onDragLeave={onDragLeave}
          onDrop={e => { e.preventDefault(); handleVid(e); }}>
          <div className="dz-icon">🎬</div>
          <div className="dz-label">{videoFile ? "Replace video" : "Drop video file here"}</div>
          <div className="dz-hint">MP4, AVI, MOV · Max 100 MB</div>
          {videoFile && <div className="dz-file">✓ {videoFile.name}</div>}
        </div>
        <input ref={videoRef} type="file" accept="video/*" hidden onChange={handleVid} />
      </div>

      <div className="row mb-20" style={{ gap: 10, flexWrap: "wrap" }}>
        <button className="btn btn-primary" disabled={!videoFile || videoLoading} onClick={analyzeVideo}>
          {videoLoading ? <span className="spinner" /> : null}
          Analyze Video
        </button>
        <button className="btn btn-ghost" disabled={!videoFile} onClick={genVideoPDF}>
          📄 PDF Report
        </button>
        <button className="btn btn-ghost" disabled={!videoFile || sendingWa} onClick={sendVideoPDFToWa} title="Send to WhatsApp">
          {sendingWa ? "…" : "📱 Send to WhatsApp"}
        </button>
        {videoResult && (
          <button className="btn btn-ghost" disabled={sendingWa || completionAlertSent} onClick={() => sendCompletionAlert("video")}>
            {completionAlertSent ? "✓ Alert sent" : "🔔 Completion alert"}
          </button>
        )}
      </div>
      {waMessage && <div className="alert alert-info">{waMessage}</div>}
      {error && <div className="alert alert-warn">⚠️ {error}</div>}

      {videoResult ? (
        <div className="card">
          <div className="card-title">Video Detection Results</div>
          <div className="metric-grid mb-20">
            <MetricCard label="Frames Processed" value={videoResult.frames_processed || 0} cls="c-cyan" />
            <MetricCard label="Total Detections" value={videoResult.total_detections || 0} cls="c-amber" />
            <MetricCard label="Risk Score" value={videoResult.risk_score !== undefined ? videoResult.risk_score.toFixed(1) + "%" : "—"} cls="c-red" />
            <MetricCard label="Grade" value={videoResult.grade || "—"} cls="c-green" />
          </div>
          {videoResult.video_info && (
            <div className="metric-grid mb-20">
              <MetricCard label="Duration" value={videoResult.video_info.duration + "s"} cls="c-muted" />
              <MetricCard label="FPS" value={videoResult.video_info.fps} cls="c-muted" />
              <MetricCard label="Resolution" value={videoResult.video_info.resolution} cls="c-muted" />
            </div>
          )}
          {videoResult.sample_frames?.length > 0 && (
            <div className="image-grid cols-4">
              {videoResult.sample_frames.map((f, i) => (
                <div className="image-frame" key={i}>
                  <img src={`data:image/png;base64,${f.annotated_b64}`} alt={`frame-${i}`} />
                  <span className="image-badge">F{f.frame_num} · {f.detection_count} det</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="empty-state">
          <div className="es-icon">🎬</div>
          <div className="es-text">Upload ROV/AUV footage to begin video analysis.</div>
        </div>
      )}
    </>
  );
}

/* ═══════════════════════════════════════════════════
   PAGE: Pipeline
   ═══════════════════════════════════════════════════ */
function PipelinePage({ file, preview, handleFile, onDragOver, onDragLeave, onDrop, detect, genPDF, sendPDFToWa, sendCompletionAlert, completionAlertSent, sendingWa, waMessage, exportCSV, loading, detResult, error }) {
  const localRef = useRef();
  return (
    <>
      <div className="section-header fade-up">
        <div className="section-crumb">Module · Subsea Pipeline</div>
        <h2 className="section-title">Pipeline Inspection</h2>
        <p className="section-desc">
          Detect corrosion, dents, free-spans and coating damage on subsea pipelines.
          Upload an image to run the full detection pipeline.
        </p>
        <div className="section-rule" />
      </div>

      {/* Upload zone */}
      <div className="card mt-20">
        <div className="card-title">Upload Pipeline Image</div>
        <div className="dropzone"
          onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}
          onClick={() => localRef.current?.click()}>
          <div className="dz-icon">📤</div>
          <div className="dz-label">
            {preview ? "Click or drop to replace" : "Drop a pipeline image here, or click to browse"}
          </div>
          <div className="dz-hint">Supported: JPG, PNG, BMP · Max 20 MB</div>
          {file && <div className="dz-file">✓ {file.name}</div>}
        </div>
        <input ref={localRef} type="file" accept="image/*" hidden onChange={e => handleFile(e.target.files[0])} />
        <div className="row mt-12" style={{ gap: 10, flexWrap: "wrap" }}>
          <button className="btn btn-primary" onClick={detect} disabled={!file || loading}>
            {loading ? "Analyzing…" : "🔍 Run Pipeline Detection"}
          </button>
          <button className="btn btn-ghost" disabled={!file || loading} onClick={genPDF}>
            📄 PDF Report
          </button>
          <button className="btn btn-ghost" disabled={!file || loading || sendingWa} onClick={sendPDFToWa} title="Send to WhatsApp">
            {sendingWa ? "…" : "📱 Send to WhatsApp"}
          </button>
          {detResult && (
            <>
              <button className="btn btn-ghost" disabled={sendingWa || completionAlertSent} onClick={() => sendCompletionAlert("image")}>🔔 Alert</button>
              <button className="btn btn-ghost" onClick={() => exportCSV(detResult)}>📊 CSV</button>
            </>
          )}
        </div>
      </div>
      {waMessage && <div className="alert alert-info">{waMessage}</div>}
      {error && <div className="alert alert-danger mt-12">⚠️ {error}</div>}

      {detResult && (
        <div className="mt-20">
          <DetectionResults data={detResult} preview={preview} />
        </div>
      )}
    </>
  );
}

/* ═══════════════════════════════════════════════════
   PAGE: Cable
   ═══════════════════════════════════════════════════ */
function CablePage({ file, preview, handleFile, onDragOver, onDragLeave, onDrop, detect, genPDF, sendPDFToWa, sendingWa, waMessage, loading, detResult, error }) {
  const localRef = useRef();
  return (
    <>
      <div className="section-header fade-up">
        <div className="section-crumb">Module · Sub-sea Cable</div>
        <h2 className="section-title">Cable Integrity Analysis</h2>
        <p className="section-desc">
          Monitor submarine power/telecom cable condition — abrasion, burial depth, and marine growth scoring.
        </p>
        <div className="section-rule" />
      </div>

      {/* Upload zone */}
      <div className="card mb-20">
        <div className="card-title">Upload Cable Image</div>
        <div className="dropzone"
          onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}
          onClick={() => localRef.current?.click()}>
          <div className="dz-icon">⚡</div>
          <div className="dz-label">
            {preview ? "Click or drop to replace" : "Drop a cable image here, or click to browse"}
          </div>
          <div className="dz-hint">Supported: JPG, PNG, BMP · Max 20 MB</div>
          {file && <div className="dz-file">✓ {file.name}</div>}
        </div>
        <input ref={localRef} type="file" accept="image/*" hidden onChange={e => handleFile(e.target.files[0])} />
        <div className="row mt-12" style={{ gap: 10, flexWrap: "wrap" }}>
          <button className="btn btn-primary" onClick={detect} disabled={!file || loading}>
            {loading ? "Analyzing…" : "🔍 Run Cable Detection"}
          </button>
          <button className="btn btn-ghost" disabled={!file || loading} onClick={genPDF}>
            📄 PDF Report
          </button>
          <button className="btn btn-ghost" disabled={!file || loading || sendingWa} onClick={sendPDFToWa} title="Send to WhatsApp">
            {sendingWa ? "…" : "📱 Send to WhatsApp"}
          </button>
          {detResult && (
            <>
              <button className="btn btn-ghost" disabled={sendingWa || completionAlertSent} onClick={() => sendCompletionAlert("image")}>🔔 Alert</button>
              <button className="btn btn-ghost" onClick={() => exportCSV(detResult)}>📊 CSV</button>
            </>
          )}
        </div>
      </div>
      {waMessage && <div className="alert alert-info">{waMessage}</div>}
      {error && <div className="alert alert-danger mt-12">⚠️ {error}</div>}

      {detResult && (
        <div className="mt-20">
          <DetectionResults data={detResult} preview={preview} />
        </div>
      )}
    </>
  );
}

/* ═══════════════════════════════════════════════════
   PAGE: Dashboard
   ═══════════════════════════════════════════════════ */
function DashPage({ detResult }) {
  const det = detResult?.detections || [];
  const counts = {};
  det.forEach(d => { counts[d.cls] = (counts[d.cls] || 0) + 1; });
  const classes = Object.entries(counts).sort((a, b) => b[1] - a[1]);

  return (
    <>
      <div className="section-header fade-up">
        <div className="section-crumb">Analytics · Overview</div>
        <h2 className="section-title">Inspection Dashboard</h2>
        <p className="section-desc">
          Real-time summary of the most recent analysis — detection metrics, severity distribution and risk score.
        </p>
        <div className="section-rule" />
      </div>

      {/* ── Mission Control ── */}
      <div className="card mb-20 mission-control">
        <div className="card-title">Mission Control</div>
        <div className="mc-grid">
          {/* Threat Gauge */}
          <div className="mc-gauge-wrap">
            <svg viewBox="0 0 120 120" className="mc-gauge-svg">
              <circle cx="60" cy="60" r="52" fill="none" stroke="rgba(0,229,255,0.08)" strokeWidth="8" />
              <circle cx="60" cy="60" r="52" fill="none"
                stroke={detResult?.risk_score > 70 ? "var(--danger)" : detResult?.risk_score > 40 ? "var(--warn)" : "var(--success)"}
                strokeWidth="8" strokeLinecap="round"
                strokeDasharray={`${(detResult?.risk_score || 0) * 3.27} 327`}
                transform="rotate(-90 60 60)"
                className="mc-gauge-arc"
              />
              <text x="60" y="54" textAnchor="middle" className="mc-gauge-num">
                {detResult?.risk_score?.toFixed(0) || "0"}
              </text>
              <text x="60" y="70" textAnchor="middle" className="mc-gauge-unit">RISK %</text>
            </svg>
            <div className="mc-gauge-label">Threat Level</div>
          </div>

          {/* Live Stats */}
          <div className="mc-stats">
            {[
              { label: "Objects Detected", val: det.length, color: "var(--cyan)" },
              { label: "Anomaly Classes", val: classes.length, color: "var(--success)" },
              { label: "Avg Confidence", val: det.length > 0 ? (det.reduce((s,d) => s+d.conf,0)/det.length*100).toFixed(1)+"%" : "—", color: "var(--warn)" },
              { label: "Mission Grade", val: detResult?.grade || "—", color: detResult?.grade === "A" ? "var(--success)" : "var(--danger)" },
            ].map(s => (
              <div className="mc-stat" key={s.label}>
                <div className="mc-stat-val" style={{ color: s.color }}>{s.val}</div>
                <div className="mc-stat-label">{s.label}</div>
              </div>
            ))}
          </div>

          {/* Sonar Ping */}
          <div className="mc-sonar-wrap">
            <div className="mc-sonar">
              <div className="mc-sonar-ring r1" />
              <div className="mc-sonar-ring r2" />
              <div className="mc-sonar-ring r3" />
              <div className="mc-sonar-sweep" />
              <div className="mc-sonar-center" />
              {det.slice(0, 6).map((d, i) => {
                const angle = (i / Math.max(det.length, 6)) * Math.PI * 2;
                const r = 20 + d.conf * 25;
                return <div key={i} className="mc-sonar-blip" style={{
                  left: `${50 + Math.cos(angle) * r}%`,
                  top: `${50 + Math.sin(angle) * r}%`,
                  background: d.severity === "Critical" ? "var(--danger)" : d.severity === "High" ? "var(--warn)" : "var(--success)",
                }} />;
              })}
            </div>
            <div className="mc-gauge-label">Detection Sonar</div>
          </div>
        </div>

        {/* Severity bar */}
        {det.length > 0 && (
          <div className="mc-sev-bar">
            {["Low","Medium","High","Critical"].map(sev => {
              const cnt = detResult?.sev_counts?.[sev] || 0;
              const pct = det.length > 0 ? (cnt/det.length*100) : 0;
              const colors = { Low: "var(--success)", Medium: "var(--warn)", High: "#FF6B35", Critical: "var(--danger)" };
              return (
                <div className="mc-sev-seg" key={sev} style={{ flex: Math.max(pct, 3) }}>
                  <div className="mc-sev-fill" style={{ background: colors[sev] }} />
                  <div className="mc-sev-txt">{sev} · {cnt}</div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {det.length === 0 ? (
        <div className="empty-state">
          <div className="es-icon">📊</div>
          <div className="es-text">Run a detection first to populate the dashboard.</div>
        </div>
      ) : (
        <>
          {/* metrics */}
          <div className="metric-grid mb-20">
            <MetricCard label="Total Detections" value={det.length} cls="c-cyan" />
            <MetricCard label="Unique Classes" value={classes.length} cls="c-green" />
            <MetricCard label="Avg Confidence"
              value={(det.reduce((s, d) => s + d.conf, 0) / det.length * 100).toFixed(1) + "%"}
              cls="c-amber" />
            <MetricCard label="High Confidence"
              value={det.filter(d => d.conf >= 0.7).length}
              cls="c-red" />
          </div>

          {/* risk */}
          {detResult?.risk_score !== undefined && (
            <div className="card mb-20 risk-panel">
              <div className="card-title">Risk Assessment</div>
              <div className="risk-header">
                <span className="risk-number">{detResult.risk_score.toFixed(1)}<span className="risk-pct">%</span></span>
                <span className="risk-message"
                  style={{ color: detResult.risk_score > 70 ? "var(--danger)" : detResult.risk_score > 40 ? "var(--warn)" : "var(--success)" }}>
                  {detResult.risk_score > 70 ? "Immediate Attention Required" :
                   detResult.risk_score > 40 ? "Moderate Risk — Schedule Repair" : "Healthy — Continue Monitoring"}
                </span>
              </div>
              <div className="risk-bar"><div className="risk-fill" style={{ width: `${detResult.risk_score}%` }} /></div>
              <div className="risk-labels">
                <span style={{ color: "var(--success)" }}>LOW</span>
                <span style={{ color: "var(--warn)" }}>MODERATE</span>
                <span style={{ color: "var(--danger)" }}>CRITICAL</span>
              </div>
            </div>
          )}

          {/* class breakdown */}
          <div className="card">
            <div className="card-title">Detection Breakdown</div>
            <table className="data-table">
              <thead><tr><th>Class</th><th>Count</th><th>Share</th></tr></thead>
              <tbody>
                {classes.map(([cls, cnt]) => (
                  <tr key={cls}>
                    <td className="td-bold">{cls}</td>
                    <td className="td-mono">{cnt}</td>
                    <td className="td-mono">{(cnt / det.length * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}

/* ═══════════════════════════════════════════════════
   PAGE: Roadmap
   ═══════════════════════════════════════════════════ */
function RoadmapPage() {
  return (
    <>
      <div className="section-header fade-up">
        <div className="section-crumb">NautiCAI · Product</div>
        <h2 className="section-title">Development Roadmap</h2>
        <p className="section-desc">
          Opinionated, execution-focused roadmap from today&apos;s beta to a fully autonomous underwater inspection and decision-support platform. Timelines are indicative and will evolve with customer feedback.
        </p>
        <div className="section-rule" />
      </div>

      <div className="phase-grid">
        {/* Phase 1 */}
        <div className="phase-card">
          <div className="phase-top">
            <span className="phase-id c-cyan">01</span>
            <span className="phase-tag live">LIVE</span>
          </div>
          <div className="phase-num">v1.0<span>/core</span></div>
          <div className="phase-sublabel">Foundation · Beta</div>
          <ul className="phase-list">
            {[
              "Single-mission image and video ingestion",
              "Deep vision anomaly detection for hull, pipeline and cable",
              "Visibility enhancement (CLAHE, green-water and turbidity filters)",
              "Severity labels, risk scoring and mission grading",
              "PDF inspection packs and mission-level dashboard",
              "Internal pilots with design partners (operator-in-the-loop)",
            ].map((t, i) => (
              <li key={i}><span className="phase-dot" style={{ background: "var(--success)" }} />{t}</li>
            ))}
          </ul>
        </div>

        {/* Phase 2 */}
        <div className="phase-card">
          <div className="phase-top">
            <span className="phase-id" style={{ color: "var(--warn)" }}>02</span>
            <span className="phase-tag planned">Q3–Q4 2025</span>
          </div>
          <div className="phase-num">v2.0<span>/scale</span></div>
          <div className="phase-sublabel">Scale · Reliability</div>
          <ul className="phase-list">
            {[
              "Production-grade pipeline and cable modules (free-spans, coating, cathodic protection)",
              "Mission analytics: trend views, class heatmaps and severity distributions",
              "Real-time ROV streaming connector and low-latency inference",
              "Multi-tenant cloud dashboard with role-based access control (RBAC)",
              "Customer API and webhooks for CMMS / digital twin integrations",
              "Hardening, monitoring, alerting and SLA-backed deployments",
            ].map((t, i) => (
              <li key={i}><span className="phase-dot" style={{ background: "var(--warn)" }} />{t}</li>
            ))}
          </ul>
        </div>

        {/* Phase 3 */}
        <div className="phase-card">
          <div className="phase-top">
            <span className="phase-id" style={{ color: "var(--violet)" }}>03</span>
            <span className="phase-tag planned">2026+</span>
          </div>
          <div className="phase-num">v3.0<span>/auto</span></div>
          <div className="phase-sublabel">Intelligence · Autonomy</div>
          <ul className="phase-list">
            {[
              "Subsea cable burial-depth estimation and route risk scoring",
              "3D point-cloud reconstruction and digital twin integration",
              "Cross-mission degradation tracking and anomaly forecasting",
              "AI-assisted fleet inspection planning and optimisation engine",
              "Semi-autonomous ROV guidance and inspection playbooks",
              "Regulatory-grade compliance reporting and full audit trail",
            ].map((t, i) => (
              <li key={i}><span className="phase-dot" style={{ background: "var(--violet)" }} />{t}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Technology Stack</div>
        <div className="metric-grid tech-stack-grid">
          {[
            { label: "Detection", value: "Vision AI Engine", cls: "c-cyan" },
            { label: "Backend", value: "FastAPI", cls: "c-green" },
            { label: "Frontend", value: "React", cls: "c-amber" },
            { label: "Cloud", value: "GCP", cls: "c-cyan" },
            { label: "Inference", value: "PyTorch", cls: "c-red" },
            { label: "Reports", value: "FPDF2", cls: "c-muted" },
          ].map(m => <MetricCard key={m.label} {...m} />)}
        </div>
      </div>
    </>
  );
}

/* ═══════════════════════════════════════════════════
   SHARED: Detection Results
   ═══════════════════════════════════════════════════ */
function DetectionResults({ data, preview }) {
  if (!data) return null;
  const det = data.detections || [];

  return (
    <div className="card mb-20">
      <div className="card-title">Detection Results — {det.length} anomalies found</div>

      {/* metrics row */}
      <div className="metric-grid mb-20">
        <MetricCard label="Detections" value={det.length} cls="c-cyan" />
        <MetricCard label="Risk Score" value={data.risk_score !== undefined ? data.risk_score.toFixed(1) + "%" : "—"} cls="c-red" />
        <MetricCard label="Grade" value={data.grade || "—"} cls="c-amber" />
        <MetricCard label="Mission" value={data.mission_id || "—"} cls="c-muted" />
      </div>

      {/* Annotated + Heatmap */}
      <div className="image-grid cols-2 mb-20">
        {data.annotated_b64 && (
          <div className="image-frame">
            <img src={`data:image/png;base64,${data.annotated_b64}`} alt="annotated" />
            <span className="image-badge">ANNOTATED</span>
          </div>
        )}
        {data.heatmap_b64 && (
          <div className="image-frame">
            <img src={`data:image/png;base64,${data.heatmap_b64}`} alt="heatmap" />
            <span className="image-badge">HEATMAP</span>
          </div>
        )}
      </div>

      {/* Enhanced image */}
      {data.enhanced_b64 && (
        <div className="image-grid cols-2 mb-20">
          <div className="image-frame">
            <img src={preview} alt="original" />
            <span className="image-badge">ORIGINAL</span>
          </div>
          <div className="image-frame">
            <img src={`data:image/png;base64,${data.enhanced_b64}`} alt="enhanced" />
            <span className="image-badge">ENHANCED</span>
          </div>
        </div>
      )}

      {/* Detections table */}
      {det.length > 0 && (
        <table className="data-table">
          <thead><tr>
            <th>#</th><th>Class</th><th>Confidence</th><th>Severity</th><th>Bbox Area</th>
          </tr></thead>
          <tbody>
            {det.map((d, i) => {
              const sev = (d.severity || "low").toLowerCase();
              return (
                <tr key={i}>
                  <td className="td-mono">{d.id || i + 1}</td>
                  <td className="td-bold">{d.cls}</td>
                  <td className="td-mono">{(d.conf * 100).toFixed(1)}%</td>
                  <td><span className={`sev-badge sev-${sev}`}>{d.severity || "Low"}</span></td>
                  <td className="td-mono">{d.area ? d.area.toLocaleString() + " px" : "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   SHARED: Enhancement Results
   ═══════════════════════════════════════════════════ */
function EnhancementResults({ data }) {
  if (!data) return null;
  const stepMap = [
    { key: "clahe_b64", label: "CLAHE" },
    { key: "green_b64", label: "GREEN CORRECTION" },
    { key: "turbidity_b64", label: "TURBIDITY FILTER" },
    { key: "edge_b64", label: "EDGE ESTIMATOR" },
    { key: "full_b64", label: "FULLY ENHANCED" },
  ];
  const available = stepMap.filter(s => data[s.key]);

  return (
    <div className="card mb-20">
      <div className="card-title">Visibility Enhancement — {available.length} steps applied</div>
      <div className={`image-grid ${available.length >= 4 ? "cols-4" : "cols-2"}`}>
        {available.map(s => (
          <div className="image-frame" key={s.key}>
            <img src={`data:image/png;base64,${data[s.key]}`} alt={s.label} />
            <span className="image-badge">{s.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   SHARED: Workflow Strip
   ═══════════════════════════════════════════════════ */
function WorkflowStrip({ steps }) {
  return (
    <div className="wf-strip">
      {steps.map((s, i) => (
        <div className="wf-step" key={i}>
          <span className="wf-num">0{i + 1}</span>
          <span className="wf-icon">{s.icon}</span>
          <div className="wf-label">{s.label}</div>
          <div className="wf-sub">{s.sub}</div>
        </div>
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   SHARED: Metric Card
   ═══════════════════════════════════════════════════ */
function MetricCard({ label, value, cls = "c-cyan" }) {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className={`metric-value ${cls}`}>{value}</div>
    </div>
  );
}
