import React, { useState, useRef } from "react";

import { getApiBaseUrl } from "./apiConfig";

const apiRoot = () => getApiBaseUrl() || window.location.origin.replace(/\/$/, "");

export default function CombinedScan({ combinedParams = {}, vesselName = "", inspector = "" }) {
  const [sonarFiles, setSonarFiles] = useState([]);
  const [anomalyFiles, setAnomalyFiles] = useState([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");
  const [expandedSonar, setExpandedSonar] = useState(null);
  const [expandedAnomaly, setExpandedAnomaly] = useState(null);

  const sonarRef = useRef(null);
  const anomalyRef = useRef(null);

  const appendFormFields = (formData) => {
    const p = combinedParams || {};
    const conf = p.conf_thr ?? p.confidence_threshold ?? 0.25;
    formData.append("confidence_threshold", String(conf));
    formData.append("conf_thr", String(conf));
    formData.append("iou_thr", String(p.iou_thr ?? 0.45));
    formData.append("mode", String(p.mode ?? "general"));
    formData.append("sev_filter", String(p.sev_filter ?? "All Detections"));
  };

  const analyzeCombined = async () => {
    if (sonarFiles.length === 0 && anomalyFiles.length === 0) return;

    setIsAnalyzing(true);
    setError("");

    try {
      const formData = new FormData();
      sonarFiles.forEach((f) => formData.append("sonar_files", f.file));
      anomalyFiles.forEach((f) => formData.append("anomaly_files", f.file));
      appendFormFields(formData);

      const res = await fetch(`${apiRoot()}/api/sonar/analyze-combined-v2`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        let msg = `API error: ${res.status}`;
        try {
          const j = await res.json();
          if (typeof j.detail === "string") msg = j.detail;
          else if (Array.isArray(j.detail)) msg = j.detail.map((x) => x.msg || JSON.stringify(x)).join("; ");
        } catch {
          /* keep msg */
        }
        throw new Error(msg);
      }
      const data = await res.json();
      setResults(data);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setIsAnalyzing(false);
    }
  };

  const downloadPDF = async () => {
    if (!results) return;
    setPdfLoading(true);
    setError("");
    try {
      const vn = vesselName || "Unknown";
      const ins = inspector || "NautiCAI AutoScan v1.0";
      const fd = new FormData();
      fd.append("results_json", JSON.stringify(results));
      fd.append("vessel_name", vn);
      fd.append("inspector", ins);
      sonarFiles.forEach((x) => fd.append("sonar_files", x.file));
      anomalyFiles.forEach((x) => fd.append("anomaly_files", x.file));
      const res = await fetch(`${apiRoot()}/api/sonar/report/combined-pdf`, {
        method: "POST",
        body: fd,
      });
      if (!res.ok) {
        let msg = `PDF failed (${res.status})`;
        try {
          const t = await res.text();
          try {
            const j = JSON.parse(t);
            if (typeof j.detail === "string") msg = j.detail;
          } catch {
            if (t) msg = t.slice(0, 300);
          }
        } catch {
          /* keep msg */
        }
        throw new Error(msg);
      }
      const blob = await res.blob();
      const head = await blob.slice(0, 5).text();
      if (!head.startsWith("%PDF")) {
        const t = await blob.text();
        throw new Error(t.slice(0, 200) || "Response was not a PDF");
      }
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `NautiCAI_Combined_Report_${Date.now()}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      setError("PDF download failed: " + e.message);
    } finally {
      setPdfLoading(false);
    }
  };

  const handleFiles = (files, type) => {
    const fileList = Array.from(files || []).map((f, i) => ({
      id: `${Date.now()}-${i}-${Math.random().toString(36).slice(2, 9)}`,
      file: f,
      preview: URL.createObjectURL(f),
    }));
    if (!fileList.length) return;
    if (type === "sonar") setSonarFiles((prev) => [...prev, ...fileList]);
    else setAnomalyFiles((prev) => [...prev, ...fileList]);
  };

  const clearAll = () => {
    sonarFiles.forEach((x) => URL.revokeObjectURL(x.preview));
    anomalyFiles.forEach((x) => URL.revokeObjectURL(x.preview));
    setSonarFiles([]);
    setAnomalyFiles([]);
    setResults(null);
    setExpandedSonar(null);
    setExpandedAnomaly(null);
  };

  const getSevColor = (sev) => {
    const colors = {
      critical: "#ef4444",
      high: "#f97316",
      medium: "#eab308",
      low: "#22c55e",
      Critical: "#ef4444",
      High: "#f97316",
      Medium: "#eab308",
      Low: "#22c55e",
    };
    return colors[sev] || "#94a3b8";
  };

  const UploadZone = ({ title, files, type, fileRef, color, icon, description }) => (
    <div style={{ flex: 1 }}>
      <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 8, color, display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ fontSize: 20 }}>{icon}</span>
        {title}
      </div>
      <div style={{ fontSize: 11, opacity: 0.6, marginBottom: 12, lineHeight: 1.4 }}>{description}</div>
      <div
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          e.currentTarget.style.borderColor = color;
        }}
        onDragLeave={(e) => {
          e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)";
        }}
        onDrop={(e) => {
          e.preventDefault();
          e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)";
          handleFiles(e.dataTransfer.files, type);
        }}
        style={{
          border: "2px dashed rgba(255,255,255,0.1)",
          borderRadius: 10,
          padding: 28,
          textAlign: "center",
          cursor: "pointer",
          background: "rgba(0,0,0,0.2)",
          minHeight: 180,
        }}
      >
        <div style={{ fontSize: 36, marginBottom: 10, opacity: 0.3 }}>📁</div>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
          {files.length > 0 ? `${files.length} image(s) selected` : "Drop images or click to browse"}
        </div>
        <div style={{ fontSize: 10, opacity: 0.4 }}>PNG, JPG, TIFF • Multiple upload</div>
        {files.length > 0 && (
          <div style={{ marginTop: 14, display: "flex", gap: 5, flexWrap: "wrap", justifyContent: "center" }}>
            {files.slice(0, 6).map((f) => (
              <div key={f.id} style={{ width: 50, height: 50, borderRadius: 5, overflow: "hidden", border: `1px solid ${color}40` }}>
                <img src={f.preview} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              </div>
            ))}
            {files.length > 6 && (
              <div
                style={{
                  width: 50,
                  height: 50,
                  borderRadius: 5,
                  background: "rgba(255,255,255,0.05)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 11,
                  fontWeight: 700,
                  color,
                }}
              >
                +{files.length - 6}
              </div>
            )}
          </div>
        )}
      </div>
      <input ref={fileRef} type="file" accept="image/*" multiple hidden onChange={(e) => handleFiles(e.target.files, type)} />
    </div>
  );

  return (
    <>
      <div className="section-header fade-up">
        <div className="section-crumb">Module · Dual Analysis</div>
        <h2 className="section-title">Combined Sonar + Anomaly Scan</h2>
        <div className="section-rule" />
      </div>
      <div className="card mb-20">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          <UploadZone
            title="Sonar Images"
            description="Side-scan sonar (SSS) or synthetic aperture sonar (SAS) for pipeline / seabed contacts."
            files={sonarFiles}
            type="sonar"
            fileRef={sonarRef}
            color="#22d3ee"
            icon="🔊"
          />
          <UploadZone
            title="Underwater Anomaly Images"
            description="ROV/AUV stills for defect detection — corrosion, biofouling, cracks, coating damage, etc."
            files={anomalyFiles}
            type="anomaly"
            fileRef={anomalyRef}
            color="#f59e0b"
            icon="🔍"
          />
        </div>
      </div>
      <div className="row mb-20" style={{ gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <button className="btn btn-primary" disabled={(sonarFiles.length === 0 && anomalyFiles.length === 0) || isAnalyzing} onClick={analyzeCombined}>
          {isAnalyzing && <span className="spinner" />}
          Analyze Combined
        </button>
        <button
          type="button"
          className={results ? "btn btn-primary" : "btn btn-ghost"}
          disabled={!results || pdfLoading}
          onClick={downloadPDF}
          title={results ? "Download combined sonar + visual summary PDF" : "Run Analyze Combined first, then download the PDF report"}
        >
          {pdfLoading && <span className="spinner" />}
          📄 PDF Report
        </button>
        <div style={{ fontSize: 12, opacity: 0.5 }}>
          {sonarFiles.length > 0 && `${sonarFiles.length} sonar`}
          {sonarFiles.length > 0 && anomalyFiles.length > 0 && " · "}
          {anomalyFiles.length > 0 && `${anomalyFiles.length} visual`}
        </div>
        {(sonarFiles.length > 0 || anomalyFiles.length > 0) && (
          <button className="btn btn-ghost" onClick={clearAll}>
            Clear All
          </button>
        )}
      </div>
      {error && (
        <div
          style={{
            padding: 14,
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: 8,
            color: "#ef4444",
            fontSize: 13,
            marginBottom: 20,
          }}
        >
          {error}
        </div>
      )}
      {results && (
        <>
          <div className="card mb-20" style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 14, padding: "14px 18px" }}>
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1, opacity: 0.5, textTransform: "uppercase", marginBottom: 4 }}>Export</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: "#e2e8f0" }}>Combined inspection PDF</div>
              <div style={{ fontSize: 11, opacity: 0.45, marginTop: 4 }}>Annotated frames · detection tables with scores</div>
            </div>
            <button type="button" className="btn btn-primary" disabled={pdfLoading} onClick={downloadPDF}>
              {pdfLoading && <span className="spinner" />}
              Download PDF
            </button>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 24 }}>
            <div className="card" style={{ textAlign: "center", padding: "16px 10px" }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: "#22d3ee" }}>{results.combined_summary?.total_detections || 0}</div>
              <div style={{ fontSize: 10, opacity: 0.45, marginTop: 4, textTransform: "uppercase", letterSpacing: 1 }}>Total</div>
            </div>
            <div className="card" style={{ textAlign: "center", padding: "16px 10px" }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: "#22d3ee" }}>{results.sonar?.total_detections || 0}</div>
              <div style={{ fontSize: 10, opacity: 0.45, marginTop: 4, textTransform: "uppercase", letterSpacing: 1 }}>Sonar</div>
            </div>
            <div className="card" style={{ textAlign: "center", padding: "16px 10px" }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: "#f59e0b" }}>{results.anomaly?.total_detections || 0}</div>
              <div style={{ fontSize: 10, opacity: 0.45, marginTop: 4, textTransform: "uppercase", letterSpacing: 1 }}>Anomaly</div>
            </div>
            <div className="card" style={{ textAlign: "center", padding: "16px 10px" }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: "#ef4444" }}>{results.combined_summary?.total_critical || 0}</div>
              <div style={{ fontSize: 10, opacity: 0.45, marginTop: 4, textTransform: "uppercase", letterSpacing: 1 }}>Critical</div>
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div className="card">
              <div className="card-title" style={{ color: "#22d3ee", marginBottom: 14 }}>
                🔊 Sonar results — click to expand
              </div>
              {(results.sonar?.results?.length > 0
                ? results.sonar.results.map((r, idx) => (
                <div key={`${r.filename}-${idx}`} style={{ marginBottom: 12 }}>
                  <div
                    onClick={() => setExpandedSonar(expandedSonar === idx ? null : idx)}
                    style={{
                      padding: 14,
                      background: "rgba(34,211,238,0.05)",
                      border: "1px solid rgba(34,211,238,0.15)",
                      borderRadius: 8,
                      cursor: "pointer",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 4 }}>{r.filename}</div>
                        <div style={{ fontSize: 11, opacity: 0.8 }}>
                          {r.total_detections} detection{r.total_detections !== 1 ? "s" : ""}
                          {r.critical_count > 0 && (
                            <span style={{ color: "#ef4444", fontWeight: 700 }}> • {r.critical_count} critical</span>
                          )}
                        </div>
                      </div>
                      <span style={{ fontSize: 16, opacity: 0.5 }}>{expandedSonar === idx ? "▼" : "▶"}</span>
                    </div>
                  </div>
                  {expandedSonar === idx && r.detections && r.detections.length > 0 && (
                    <div style={{ marginTop: 8, paddingLeft: 12 }}>
                      {r.detections.map((det, didx) => (
                        <div
                          key={didx}
                          style={{
                            padding: 10,
                            background: "rgba(0,0,0,0.3)",
                            borderLeft: `3px solid ${getSevColor(det.severity)}`,
                            borderRadius: 4,
                            marginBottom: 6,
                            fontSize: 11,
                          }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                            <span style={{ fontWeight: 700 }}>
                              #{didx + 1}: {det.class_name || "Unknown"}
                            </span>
                            <span style={{ color: getSevColor(det.severity), fontWeight: 700, fontSize: 10 }}>{(det.severity || "n/a").toUpperCase()}</span>
                          </div>
                          <div style={{ opacity: 0.7 }}>Confidence: {det.confidence != null ? `${(det.confidence * 100).toFixed(1)}%` : "N/A"}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
                : null)}
              {!(results.sonar?.results?.length > 0) && (
                <div style={{ textAlign: "center", padding: 24, opacity: 0.3 }}>No sonar images in this run</div>
              )}
            </div>
            <div className="card">
              <div className="card-title" style={{ color: "#f59e0b", marginBottom: 14 }}>
                🔍 Visual inspection — click to expand
              </div>
              {(results.anomaly?.results?.length > 0
                ? results.anomaly.results.map((r, idx) => (
                <div key={`${r.filename}-${idx}`} style={{ marginBottom: 12 }}>
                  <div
                    onClick={() => setExpandedAnomaly(expandedAnomaly === idx ? null : idx)}
                    style={{
                      padding: 14,
                      background: "rgba(245,158,11,0.05)",
                      border: "1px solid rgba(245,158,11,0.15)",
                      borderRadius: 8,
                      cursor: "pointer",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 4 }}>{r.filename}</div>
                        <div style={{ fontSize: 11, opacity: 0.85 }}>
                          {r.total_detections === 0 ? (
                            <>
                              <strong>No defects</strong> above your confidence / filter — visual branch only counts ROV defect boxes (not sonar).
                              <span style={{ display: "block", marginTop: 6, fontSize: 10, opacity: 0.7 }}>
                                Inspection score <strong>{r.risk_score}%</strong> · Grade <strong>{r.grade}</strong> — higher score means fewer penalties (this is not “% danger”).
                                Try lowering <strong>Confidence</strong> in the sidebar or open the same image on <strong>Anomaly Scan</strong>.
                              </span>
                            </>
                          ) : (
                            <>
                              {r.total_detections} defect{r.total_detections !== 1 ? "s" : ""} · Grade <strong>{r.grade}</strong> · Inspection score{" "}
                              <strong>{r.risk_score}%</strong>
                            </>
                          )}
                        </div>
                      </div>
                      <span style={{ fontSize: 16, opacity: 0.5 }}>{expandedAnomaly === idx ? "▼" : "▶"}</span>
                    </div>
                  </div>
                  {expandedAnomaly === idx && r.detections && r.detections.length > 0 && (
                    <div style={{ marginTop: 8, paddingLeft: 12 }}>
                      {r.detections.map((det, didx) => (
                        <div
                          key={didx}
                          style={{
                            padding: 10,
                            background: "rgba(0,0,0,0.3)",
                            borderLeft: `3px solid ${getSevColor(det.severity)}`,
                            borderRadius: 4,
                            marginBottom: 6,
                            fontSize: 11,
                          }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                            <span style={{ fontWeight: 700 }}>#{didx + 1}: {det.class_name || det.cls || "Unknown"}</span>
                            <span style={{ color: getSevColor(det.severity), fontWeight: 700, fontSize: 10 }}>{(det.severity || "n/a").toUpperCase()}</span>
                          </div>
                          <div style={{ opacity: 0.7 }}>
                            Confidence: {det.confidence != null || det.conf != null ? `${((det.confidence ?? det.conf) * 100).toFixed(1)}%` : "N/A"}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
                : null)}
              {!(results.anomaly?.results?.length > 0) && (
                <div style={{ textAlign: "center", padding: 24, opacity: 0.3 }}>No visual images in this run</div>
              )}
            </div>
          </div>
        </>
      )}
    </>
  );
}
