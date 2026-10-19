import React, { useState, useRef, useCallback } from "react";
import { motion } from "framer-motion";
import { downloadSonarReportPdf, runSonarAnalyze } from "./api";
import { getApiBaseUrl } from "./apiConfig";
import { isLikelyImageFile } from "./imageFiles";

const SEVERITY_COLORS = {
  critical: { bg: "#FF1744", text: "#fff" },
  high: { bg: "#FF6D00", text: "#fff" },
  medium: { bg: "#FFD600", text: "#000" },
  low: { bg: "#00E676", text: "#000" },
  info: { bg: "#2979FF", text: "#fff" },
};

const CLASS_ICONS = {
  pipeline: "\u{1F527}", cable: "\u{1F50C}", debris: "\u26A0\uFE0F",
  rock: "\u{1FAA8}", wreck: "\u{1F6A2}", other: "\u2753",
};

function SeverityBadge({ severity }) {
  const s = SEVERITY_COLORS[severity] || SEVERITY_COLORS.info;
  return (
    <span style={{ padding:"3px 10px", borderRadius:12, fontSize:11, fontWeight:700, background:s.bg, color:s.text, textTransform:"uppercase", letterSpacing:"0.5px" }}>
      {severity}
    </span>
  );
}

function ImageWithDetections({ imageUrl, detections, width, height }) {
  return (
    <div style={{ position:"relative", width:"100%", marginBottom:20 }}>
      <img src={imageUrl} alt="Sonar scan" style={{ width:"100%", borderRadius:8, display:"block", background:"#000" }} />
      <svg style={{ position:"absolute", top:0, left:0, width:"100%", height:"100%", pointerEvents:"none" }} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        {detections.map((det) => {
          const [x1, y1, x2, y2] = det.bbox;
          const s = SEVERITY_COLORS[det.severity] || SEVERITY_COLORS.info;
          const px1 = x1 * width, py1 = y1 * height;
          const pw = (x2 - x1) * width, ph = (y2 - y1) * height;
          return (
            <g key={det.id}>
              <rect x={px1} y={py1} width={pw} height={ph} fill="none" stroke={s.bg} strokeWidth={3} rx={4} />
              <rect x={px1} y={Math.max(py1 - 22, 0)} width={Math.max(pw, 140)} height={22} fill={s.bg} rx={4} opacity={0.9} />
              <text x={px1 + 6} y={Math.max(py1 - 6, 14)} fill={s.text} fontSize={13} fontWeight="bold" fontFamily="monospace">
                {det.class_name} {(det.confidence * 100).toFixed(0)}% [{det.severity}]
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export default function SonarAnalysis({ vesselName = "", inspector: inspectorProp = "" }) {
  const [files, setFiles] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("upload");
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [confThreshold, setConfThreshold] = useState(0.25);
  const [isDragging, setIsDragging] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);

  const handleFiles = useCallback((fileList) => {
    const raw = Array.from(fileList || []);
    const newFiles = raw.filter(isLikelyImageFile);
    if (!newFiles.length) {
      if (raw.length) setError("No supported images found — try JPG, PNG, BMP, TIFF, or WebP (folder picks on Windows often omit file types).");
      return;
    }
    setFiles((prev) => [...prev, ...newFiles]);
    const newPreviews = newFiles.map((f) => URL.createObjectURL(f));
    setPreviews((prev) => [...prev, ...newPreviews]);
    setError("");
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  }, [handleFiles]);

  const removeFile = (idx) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
    setPreviews((prev) => prev.filter((_, i) => i !== idx));
    if (selectedIdx >= files.length - 1) setSelectedIdx(Math.max(0, files.length - 2));
  };

  const clearAll = () => {
    setFiles([]); setPreviews([]); setResults([]);
    setSelectedIdx(0); setError("");
  };

  const formatNetErr = (e, fallbackLabel) => {
    const serverDetail = () => {
      const data = e.response?.data;
      if (data == null) return null;
      if (typeof data === "string") {
        try {
          const j = JSON.parse(data);
          if (typeof j.detail === "string") return j.detail;
          if (Array.isArray(j.detail)) return j.detail.map((x) => x.msg || JSON.stringify(x)).join("; ");
        } catch {
          return data.length < 800 ? data : null;
        }
      }
      if (typeof data === "object" && !Array.isArray(data)) {
        const d = data.detail;
        if (typeof d === "string") return d;
        if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join("; ");
      }
      return null;
    };
    const fromApi = serverDetail();
    if (fromApi) return fromApi;

    const m = (e && e.message) || String(e);
    if (m === "Failed to fetch" || m === "Network Error" || /network/i.test(m)) {
      const configured = getApiBaseUrl();
      const display = configured || `${typeof window !== "undefined" ? window.location.origin : ""} (dev proxy → :8000)`;
      return (
        `${fallbackLabel}: cannot reach the API (${display}). ` +
        "Start the backend: open a terminal in the project folder and run " +
        "`python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`. " +
        "If you use `npm start` on port 3000, requests are proxied to port 8000 (see frontend/package.json). " +
        "Override with REACT_APP_API_BASE_URL if the API is elsewhere."
      );
    }
    return m || fallbackLabel;
  };

  const analyzeAll = async () => {
    if (!files.length) return;
    setLoading(true);
    setError("");
    try {
      const allResults = [];
      for (const file of files) {
        const data = await runSonarAnalyze(file, confThreshold);
        allResults.push(data);
      }
      setResults(allResults);
      setSelectedIdx(0);
      setActiveTab("results");
    } catch (e) {
      setError(formatNetErr(e, `Failed to analyze ${files[0]?.name || "image"}`));
    } finally {
      setLoading(false);
    }
  };

  const selectedResult = results[selectedIdx] || null;
  const selectedPreview = previews[selectedIdx] || null;
  const totalDetections = results.reduce((s, r) => s + r.total_detections, 0);
  const totalCritical = results.reduce((s, r) => s + r.critical_count, 0);
  const totalHigh = results.reduce((s, r) => s + r.high_count, 0);

  const downloadPDF = async () => {
    if (files.length !== results.length) {
      alert(
        `Cannot build PDF: ${files.length} file(s) selected but ${results.length} analysis result(s). ` +
          "Use Analyze All again without clearing uploads, then download PDF.",
      );
      return;
    }
    setPdfLoading(true);
    try {
      await downloadSonarReportPdf(files, results, {
        vessel_name: vesselName || "",
        inspector: inspectorProp || "NautiCAI AutoScan v1.0",
        inspection_mode: "General Inspection",
      });
    } catch (e) {
      alert("PDF generation failed: " + formatNetErr(e, "PDF request failed"));
    } finally {
      setPdfLoading(false);
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="section-header fade-up">
        <div className="section-crumb">Module &middot; Sonar Analysis</div>
        <h2 className="section-title">Sonar Analysis</h2>
        <div className="section-rule" />
      </div>

      {/* Tab Navigation */}
      <div style={{ display:"flex", gap:8, marginBottom:24 }}>
        {["upload", "results", "history"].map((t) => (
          <button key={t} className={`btn ${activeTab === t ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setActiveTab(t)}
            disabled={t === "results" && !results.length}
            style={{ opacity: t === "results" && !results.length ? 0.4 : 1 }}>
            {t === "upload" ? "\ud83d\udcc1 Upload" : t === "results" ? "\ud83d\udcca Results" : "\ud83d\udccf History"}
          </button>
        ))}
      </div>

      {/* UPLOAD TAB */}
      {activeTab === "upload" && (
        <motion.div initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }}>
          {/* Drop zone */}
          <div className="card mb-20">
            <div className="card-title">Sonar Image Upload</div>
            <div className="dropzone"
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              style={{ borderColor: isDragging ? "#22d3ee" : undefined, background: isDragging ? "rgba(34,211,238,0.05)" : undefined }}>
              <div className="dz-icon">{"\ud83d\udd0d"}</div>
              <div className="dz-label">
                {files.length ? `${files.length} image(s) uploaded \u2014 click or drop to add more` : "Drop Side-Scan Sonar images here, or click to browse"}
              </div>
              <div className="dz-hint">Supports PNG, JPG, TIFF, BMP &middot; Multiple images + folder upload</div>
            </div>
            <div className="row" style={{ gap:10, marginTop:12, flexWrap:"wrap" }}>
              <button className="btn btn-ghost" onClick={() => fileInputRef.current?.click()}>+ Add Images</button>
              <button className="btn btn-ghost" onClick={() => folderInputRef.current?.click()}>{"\ud83d\udcc2"} Upload Folder</button>
              {files.length > 0 && <button className="btn btn-ghost" onClick={clearAll}>{"\u2716"} Clear All</button>}
            </div>
            <input ref={fileInputRef} type="file" accept="image/*,.jpg,.jpeg,.png,.bmp,.webp,.tif,.tiff" multiple hidden onChange={(e) => { handleFiles(e.target.files); e.target.value = ""; }} />
            <input ref={folderInputRef} type="file" accept="image/*,.jpg,.jpeg,.png,.bmp,.webp,.tif,.tiff" multiple hidden onChange={(e) => { handleFiles(e.target.files); e.target.value = ""; }} webkitdirectory="" directory="" />
          </div>

          {/* Filmstrip */}
          {files.length > 0 && (
            <div className="card mb-20">
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:14 }}>
                <div className="card-title" style={{ margin:0 }}>Uploaded Images ({files.length})</div>
                <div style={{ fontSize:12, opacity:0.65, padding:"8px 12px", border:"1px solid rgba(255,255,255,0.08)", borderRadius:8 }}>
                  {selectedIdx + 1} / {files.length}
                </div>
              </div>
              <div style={{ display:"grid", gridTemplateColumns:"180px 1fr", gap:14, minHeight:300 }}>
                <div style={{ display:"flex", flexDirection:"column", gap:8, maxHeight:400, overflowY:"auto", paddingRight:4 }}>
                  {files.map((f, idx) => (
                    <button key={idx} onClick={() => setSelectedIdx(idx)}
                      style={{ width:"100%", textAlign:"left", border: idx === selectedIdx ? "2px solid #22d3ee" : "1px solid rgba(255,255,255,0.08)", borderRadius:10, padding:6,
                        background: idx === selectedIdx ? "rgba(34,211,238,0.08)" : "rgba(255,255,255,0.02)", cursor:"pointer", display:"flex", gap:8, alignItems:"center" }}>
                      <img src={previews[idx]} alt="" style={{ width:58, height:42, objectFit:"cover", borderRadius:6, flexShrink:0, background:"#000" }} />
                      <div style={{ minWidth:0, flex:1 }}>
                        <div style={{ fontSize:11, fontWeight:700, color: idx === selectedIdx ? "#22d3ee" : "rgba(255,255,255,0.88)", marginBottom:2 }}>Image {idx + 1}</div>
                        <div style={{ fontSize:10, color:"rgba(255,255,255,0.5)", whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis" }}>{f.name}</div>
                      </div>
                      <button onClick={(e) => { e.stopPropagation(); removeFile(idx); }}
                        style={{ background:"none", border:"none", color:"rgba(255,255,255,0.3)", cursor:"pointer", fontSize:14, padding:"2px 6px" }}>{"\u2716"}</button>
                    </button>
                  ))}
                </div>
                <div style={{ position:"relative", borderRadius:12, overflow:"hidden", background:"#000", minHeight:300, display:"flex", alignItems:"center", justifyContent:"center" }}>
                  <img src={previews[selectedIdx]} alt="" style={{ width:"100%", height:"100%", maxHeight:400, objectFit:"contain", display:"block" }} />
                  <div style={{ position:"absolute", top:12, left:12, display:"flex", gap:8 }}>
                    <div style={{ background:"rgba(0,0,0,0.65)", padding:"6px 10px", borderRadius:6, fontSize:12, color:"#22d3ee", fontWeight:700 }}>#{selectedIdx + 1}</div>
                    <div style={{ background:"rgba(0,0,0,0.65)", padding:"6px 10px", borderRadius:6, fontSize:11, color:"rgba(255,255,255,0.7)" }}>{files[selectedIdx]?.name}</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Confidence threshold */}
          <div className="card mb-20">
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
              <div>
                <div style={{ fontWeight:600, fontSize:14 }}>Confidence Threshold</div>
                <div style={{ fontSize:12, opacity:0.5 }}>Minimum confidence to report a detection</div>
              </div>
              <div style={{ display:"flex", alignItems:"center", gap:12 }}>
                <input type="range" min="0.1" max="0.9" step="0.05" value={confThreshold}
                  onChange={(e) => setConfThreshold(parseFloat(e.target.value))} style={{ width:150 }} />
                <span style={{ fontFamily:"monospace", fontWeight:700, color:"#22d3ee", minWidth:40 }}>
                  {(confThreshold * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>

          {/* Action buttons */}
          <div className="row mb-20" style={{ gap:10, flexWrap:"wrap" }}>
            <button className="btn btn-primary" disabled={!files.length || loading} onClick={analyzeAll}>
              {loading ? "\u23F3 Analyzing..." : `\ud83d\udd0d Analyze ${files.length > 1 ? `All ${files.length} Images` : "Sonar Image"}`}
            </button>
          </div>

          {error && <div className="alert alert-error" style={{ marginTop:12 }}>{error}</div>}
        </motion.div>
      )}

      {/* RESULTS TAB */}
      {activeTab === "results" && results.length > 0 && (
        <motion.div initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }}>
          {/* Batch summary */}
          {results.length > 1 && (
            <div className="card mb-20" style={{ borderLeft: totalCritical > 0 ? "4px solid #FF1744" : totalHigh > 0 ? "4px solid #FF6D00" : "4px solid #00E676" }}>
              <div style={{ fontSize:18, fontWeight:700, marginBottom:8 }}>
                {"\ud83d\udcca"} Batch Summary &mdash; {results.length} Images Analyzed
              </div>
              <div style={{ display:"grid", gridTemplateColumns:"repeat(4, 1fr)", gap:12 }}>
                <div style={{ textAlign:"center" }}><div style={{ fontSize:28, fontWeight:700, color:"#22d3ee" }}>{totalDetections}</div><div style={{ fontSize:11, opacity:0.5 }}>Total Detections</div></div>
                <div style={{ textAlign:"center" }}><div style={{ fontSize:28, fontWeight:700, color:"#FF1744" }}>{totalCritical}</div><div style={{ fontSize:11, opacity:0.5 }}>Critical</div></div>
                <div style={{ textAlign:"center" }}><div style={{ fontSize:28, fontWeight:700, color:"#FF6D00" }}>{totalHigh}</div><div style={{ fontSize:11, opacity:0.5 }}>High</div></div>
                <div style={{ textAlign:"center" }}><div style={{ fontSize:28, fontWeight:700, color:"#00E676" }}>{results.filter((r) => r.overall_status === "healthy").length}</div><div style={{ fontSize:11, opacity:0.5 }}>Healthy</div></div>
              </div>
            </div>
          )}

          {/* Image selector for results */}
          {results.length > 1 && (
            <div className="card mb-20">
              <div className="card-title" style={{ marginBottom:12 }}>Select Image to View</div>
              <div style={{ display:"flex", gap:6, flexWrap:"wrap" }}>
                {results.map((r, idx) => (
                  <button key={idx} onClick={() => setSelectedIdx(idx)}
                    style={{ padding:"8px 14px", borderRadius:8, cursor:"pointer", fontSize:12, fontWeight: idx === selectedIdx ? 700 : 400,
                      background: idx === selectedIdx ? "rgba(34,211,238,0.15)" : "rgba(255,255,255,0.03)",
                      border: idx === selectedIdx ? "1px solid #22d3ee" : "1px solid rgba(255,255,255,0.08)",
                      color: idx === selectedIdx ? "#22d3ee" : "rgba(255,255,255,0.6)" }}>
                    <span style={{ display:"inline-block", width:8, height:8, borderRadius:"50%", marginRight:6,
                      background: r.overall_status === "critical" ? "#FF1744" : r.overall_status === "warning" ? "#FF6D00" : "#00E676" }} />
                    Image {idx + 1} ({r.total_detections} det)
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Selected image result */}
          {selectedResult && (
            <>
              <div className="card mb-20" style={{ borderLeft: `4px solid ${selectedResult.overall_status === "critical" ? "#FF1744" : selectedResult.overall_status === "warning" ? "#FF6D00" : "#00E676"}` }}>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                  <div>
                    <div style={{ fontSize:18, fontWeight:700 }}>
                      {selectedResult.overall_status === "critical" ? "\ud83d\udea8 CRITICAL" : selectedResult.overall_status === "warning" ? "\u26A0\uFE0F WARNING" : "\u2705 HEALTHY"}
                      {" \u2014 "}{selectedResult.filename}
                    </div>
                    <div style={{ fontSize:13, opacity:0.6, marginTop:4 }}>{selectedResult.summary}</div>
                  </div>
                  <div style={{ textAlign:"right", fontSize:12, opacity:0.5 }}>
                    <div>ID: {selectedResult.image_id}</div>
                    <div>{"\u23F1"} {selectedResult.processing_time_ms.toFixed(0)}ms</div>
                    <div>{selectedResult.image_width} &times; {selectedResult.image_height}px</div>
                  </div>
                </div>
              </div>

              <div style={{ display:"grid", gridTemplateColumns:"repeat(4, 1fr)", gap:12, marginBottom:20 }}>
                <div className="card" style={{ textAlign:"center", padding:"16px 10px" }}><div style={{ fontSize:22, fontWeight:700, color:"#22d3ee" }}>{selectedResult.total_detections}</div><div style={{ fontSize:10, opacity:0.45, marginTop:4, textTransform:"uppercase", letterSpacing:1 }}>Detections</div></div>
                <div className="card" style={{ textAlign:"center", padding:"16px 10px" }}><div style={{ fontSize:22, fontWeight:700, color:"#FF1744" }}>{selectedResult.critical_count}</div><div style={{ fontSize:10, opacity:0.45, marginTop:4, textTransform:"uppercase", letterSpacing:1 }}>Critical</div></div>
                <div className="card" style={{ textAlign:"center", padding:"16px 10px" }}><div style={{ fontSize:22, fontWeight:700, color:"#FF6D00" }}>{selectedResult.high_count}</div><div style={{ fontSize:10, opacity:0.45, marginTop:4, textTransform:"uppercase", letterSpacing:1 }}>High</div></div>
                <div className="card" style={{ textAlign:"center", padding:"16px 10px" }}><div style={{ fontSize:22, fontWeight:700, color:"#FFD600" }}>{selectedResult.medium_count + selectedResult.low_count}</div><div style={{ fontSize:10, opacity:0.45, marginTop:4, textTransform:"uppercase", letterSpacing:1 }}>Medium / Low</div></div>
              </div>

              {/* Detection overlay */}
              {selectedPreview && (
                <div className="card mb-20">
                  <div className="card-title" style={{ marginBottom:12 }}>Detection Overlay</div>
                  <ImageWithDetections imageUrl={selectedPreview} detections={selectedResult.detections} width={selectedResult.image_width} height={selectedResult.image_height} />
                </div>
              )}

              {/* Detection list */}
              <div className="card mb-20">
                <div className="card-title" style={{ marginBottom:16 }}>Detection Details ({selectedResult.total_detections})</div>
                {selectedResult.detections.length === 0 ? (
                  <div style={{ textAlign:"center", padding:24, opacity:0.4 }}>No detections &mdash; seabed appears clear</div>
                ) : (
                  selectedResult.detections.map((det) => (
                    <div key={det.id} style={{ display:"flex", alignItems:"center", gap:12, padding:"12px 16px", background:"rgba(255,255,255,0.03)", borderRadius:8, marginBottom:8,
                      borderLeft:`3px solid ${(SEVERITY_COLORS[det.severity] || SEVERITY_COLORS.info).bg}` }}>
                      <span style={{ fontSize:24 }}>{CLASS_ICONS[det.class_name] || "\u2754"}</span>
                      <div style={{ flex:1 }}>
                        <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:4 }}>
                          <span style={{ fontWeight:700, fontSize:14, textTransform:"capitalize" }}>{det.class_name.replace("_", " ")}</span>
                          <SeverityBadge severity={det.severity} />
                          <span style={{ fontFamily:"monospace", fontSize:12, color:"#22d3ee" }}>{(det.confidence * 100).toFixed(1)}%</span>
                        </div>
                        <div style={{ fontSize:12, opacity:0.5 }}>{det.description}</div>
                      </div>
                      <div style={{ fontFamily:"monospace", fontSize:11, opacity:0.4, textAlign:"right" }}>
                        <div>{det.id}</div>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Model info */}
              <div className="card mb-20">
                <div className="card-title" style={{ marginBottom:12 }}>Model Information</div>
                <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:12, fontSize:13 }}>
                  <div><span style={{ opacity:0.5 }}>Detector: </span><span style={{ color:"#22d3ee" }}>{selectedResult.model_info.detector}</span></div>
                  <div><span style={{ opacity:0.5 }}>Classifier: </span><span style={{ color:"#22d3ee" }}>{selectedResult.model_info.classifier}</span></div>
                  <div><span style={{ opacity:0.5 }}>Version: </span><span style={{ color:"#22d3ee" }}>{selectedResult.model_info.version}</span></div>
                </div>
              </div>
            </>
          )}

          {/* Action buttons */}
          <div className="row mb-20" style={{ gap:10, flexWrap:"wrap" }}>
            <button className="btn btn-primary" onClick={() => { clearAll(); setActiveTab("upload"); }}>{"\ud83d\udcc1"} Analyze More Images</button>
            <button className="btn btn-primary" onClick={downloadPDF} disabled={pdfLoading}
              style={{ background: pdfLoading ? "#1e3a5f" : "#0EA5E9" }}>
              {pdfLoading ? "\u23F3 Generating PDF..." : "\ud83d\udcc4 Download PDF Report"}
            </button>
          </div>
        </motion.div>
      )}

      {/* HISTORY TAB */}
      {activeTab === "history" && (
        <motion.div initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }}>
          <div className="card">
            <div className="card-title">Analysis History</div>
            <div style={{ textAlign:"center", padding:32, opacity:0.4 }}>
              History loads from /api/sonar/history endpoint.<br />Analyze images to populate history.
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}
