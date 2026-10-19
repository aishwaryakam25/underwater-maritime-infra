import { useState, useRef } from "react";
import { apiUrl } from "./apiConfig";

const SEV_COLOR = {
  PASS: "#00c853",
  MODERATE: "#ffab00",
  HIGH: "#ff6d00",
  CRITICAL: "#d50000",
};

const SEV_BG = {
  PASS: "rgba(0,200,83,0.12)",
  MODERATE: "rgba(255,171,0,0.12)",
  HIGH: "rgba(255,109,0,0.12)",
  CRITICAL: "rgba(213,0,0,0.12)",
};

export default function WeldInspector() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [vesselName, setVesselName] = useState("MV Pacific Explorer");
  const [nZones, setNZones] = useState(6);
  const fileRef = useRef();

  const handleFile = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setResult(null);
    setError(null);
  };

  const handleInspect = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("vessel_name", vesselName);
      fd.append("n_zones", nZones);
      const res = await fetch(apiUrl("/api/innovation/weld-inspect"), {
        method: "POST", body: fd,
      });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setError(e.message);
    }
    setLoading(false);
  };

  return (
    <div style={{ padding: "24px", color: "#e0e6f0", fontFamily: "Inter, sans-serif" }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 6 }}>
          <span style={{ fontSize: 28 }}>🔬</span>
          <h2 style={{ margin: 0, fontSize: 22, color: "#00d4ff", fontWeight: 700 }}>
            Underwater Weld Anomaly Inspector
          </h2>
          <span style={{
            background: "linear-gradient(135deg, #00d4ff22, #7b2fff22)",
            border: "1px solid #00d4ff44",
            borderRadius: 20, padding: "2px 12px",
            fontSize: 11, color: "#00d4ff", fontWeight: 600
          }}>INDUSTRY FIRST</span>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 20 }}>
        {/* Left Panel */}
        <div>
          {/* Upload */}
          <div style={{
            background: "#0d1b2a", border: "1px solid #1e3a5f",
            borderRadius: 12, padding: 20, marginBottom: 16
          }}>
            <h3 style={{ margin: "0 0 14px", fontSize: 13, color: "#8899aa", textTransform: "uppercase", letterSpacing: 1 }}>
              ROV Footage Upload
            </h3>
            <div
              onClick={() => fileRef.current.click()}
              style={{
                border: `2px dashed ${file ? "#00d4ff" : "#1e3a5f"}`,
                borderRadius: 10, padding: "24px 16px", textAlign: "center",
                cursor: "pointer", marginBottom: 14,
                background: file ? "rgba(0,212,255,0.04)" : "transparent",
                transition: "all 0.2s"
              }}
            >
              {preview ? (
                <img src={preview} alt="preview" style={{
                  width: "100%", borderRadius: 8, maxHeight: 160, objectFit: "cover"
                }} />
              ) : (
                <>
                  <div style={{ fontSize: 32, marginBottom: 8 }}>📷</div>
                  <div style={{ fontSize: 13, color: "#8899aa" }}>Click to upload ROV image</div>
                  <div style={{ fontSize: 11, color: "#556677", marginTop: 4 }}>JPG, PNG, WEBP</div>
                </>
              )}
            </div>
            <input ref={fileRef} type="file" accept="image/*" onChange={handleFile} style={{ display: "none" }} />

            <label style={{ fontSize: 12, color: "#8899aa", display: "block", marginBottom: 4 }}>Vessel Name</label>
            <input
              value={vesselName}
              onChange={e => setVesselName(e.target.value)}
              style={{
                width: "100%", background: "#0a1628", border: "1px solid #1e3a5f",
                borderRadius: 8, padding: "8px 12px", color: "#e0e6f0",
                fontSize: 13, marginBottom: 12, boxSizing: "border-box"
              }}
            />

            <label style={{ fontSize: 12, color: "#8899aa", display: "block", marginBottom: 4 }}>
              Weld Zones to Inspect: {nZones}
            </label>
            <input type="range" min={3} max={12} value={nZones}
              onChange={e => setNZones(parseInt(e.target.value))}
              style={{ width: "100%", marginBottom: 16 }}
            />

            <button
              onClick={handleInspect}
              disabled={!file || loading}
              style={{
                width: "100%", padding: "12px",
                background: file && !loading
                  ? "linear-gradient(135deg, #00d4ff, #0088cc)"
                  : "#1e3a5f",
                border: "none", borderRadius: 10, color: "white",
                fontWeight: 700, fontSize: 14, cursor: file && !loading ? "pointer" : "not-allowed",
                transition: "all 0.2s"
              }}
            >
              {loading ? "🔬 Inspecting Welds..." : "🚀 Run Weld Inspection"}
            </button>

            {error && (
              <div style={{ marginTop: 12, padding: 10, background: "#2d0a0a",
                border: "1px solid #d50000", borderRadius: 8, fontSize: 12, color: "#ff6b6b" }}>
                ⚠️ {error}
              </div>
            )}
          </div>

          {/* Standards badge */}
          <div style={{
            background: "#0d1b2a", border: "1px solid #1e3a5f",
            borderRadius: 12, padding: 16
          }}>
            <h3 style={{ margin: "0 0 10px", fontSize: 12, color: "#8899aa", textTransform: "uppercase" }}>
              Standards Compliance
            </h3>
            {["AWS D1.1 Structural Welding", "ISO 5817 Quality Levels", "ABS Underwater Inspection", "Causal AI Explainability"].map(s => (
              <div key={s} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                <span style={{ color: "#00c853", fontSize: 14 }}>✓</span>
                <span style={{ fontSize: 12, color: "#aabbcc" }}>{s}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right Panel */}
        <div>
          {!result && !loading && (
            <div style={{
              background: "#0d1b2a", border: "1px solid #1e3a5f",
              borderRadius: 12, padding: 60, textAlign: "center"
            }}>
              <div style={{ fontSize: 48, marginBottom: 16 }}>🔬</div>
              <div style={{ color: "#556677", fontSize: 14 }}>
                Upload ROV footage to begin weld anomaly detection
              </div>
              <div style={{ color: "#334455", fontSize: 12, marginTop: 8 }}>
                Detects: Cracks • Porosity • Undercut • Incomplete Fusion • Corrosion Pits
              </div>
            </div>
          )}

          {loading && (
            <div style={{
              background: "#0d1b2a", border: "1px solid #00d4ff33",
              borderRadius: 12, padding: 60, textAlign: "center"
            }}>
              <div style={{ fontSize: 48, marginBottom: 16, animation: "spin 1s linear infinite" }}>⚙️</div>
              <div style={{ color: "#00d4ff", fontSize: 15, fontWeight: 600 }}>Analyzing weld zones...</div>
              <div style={{ color: "#556677", fontSize: 12, marginTop: 8 }}>Running AI defect classification with causal reasoning</div>
            </div>
          )}

          {result && (
            <div>
              {/* Summary cards */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 16 }}>
                {[
                  { label: "Overall Result", value: result.overall_result,
                    color: result.overall_result === "PASS" ? "#00c853" : result.overall_result === "FAIL" ? "#d50000" : "#ffab00" },
                  { label: "Critical Defects", value: result.critical_count, color: "#d50000" },
                  { label: "Risk Grade", value: result.grade, color: "#00d4ff" },
                  { label: "Repair Cost", value: `$${(result.total_repair_cost_usd/1000).toFixed(0)}K`, color: "#ffab00" },
                ].map(c => (
                  <div key={c.label} style={{
                    background: "#0d1b2a", border: `1px solid ${c.color}44`,
                    borderRadius: 12, padding: 16, textAlign: "center"
                  }}>
                    <div style={{ fontSize: 22, fontWeight: 800, color: c.color }}>{c.value}</div>
                    <div style={{ fontSize: 11, color: "#8899aa", marginTop: 4 }}>{c.label}</div>
                  </div>
                ))}
              </div>

              {/* Annotated image */}
              {result.annotated_b64 && (
                <div style={{
                  background: "#0d1b2a", border: "1px solid #1e3a5f",
                  borderRadius: 12, padding: 16, marginBottom: 16
                }}>
                  <h3 style={{ margin: "0 0 12px", fontSize: 13, color: "#8899aa", textTransform: "uppercase" }}>
                    AI Detection Overlay
                  </h3>
                  <img
                    src={`data:image/png;base64,${result.annotated_b64}`}
                    alt="annotated"
                    style={{ width: "100%", borderRadius: 8, maxHeight: 280, objectFit: "contain" }}
                  />
                </div>
              )}

              {/* Weld zones */}
              <div style={{
                background: "#0d1b2a", border: "1px solid #1e3a5f",
                borderRadius: 12, padding: 16
              }}>
                <h3 style={{ margin: "0 0 14px", fontSize: 13, color: "#8899aa", textTransform: "uppercase" }}>
                  Weld Zone Analysis — Causal AI Results
                </h3>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 10 }}>
                  {result.weld_zones.map(z => (
                    <div key={z.zone_id} style={{
                      background: SEV_BG[z.severity],
                      border: `1px solid ${SEV_COLOR[z.severity]}44`,
                      borderRadius: 10, padding: 14
                    }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                        <span style={{ fontWeight: 700, fontSize: 13, color: "#e0e6f0" }}>{z.zone_id}</span>
                        <span style={{
                          background: SEV_COLOR[z.severity],
                          borderRadius: 20, padding: "2px 10px",
                          fontSize: 11, color: "white", fontWeight: 700
                        }}>{z.severity}</span>
                      </div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: SEV_COLOR[z.severity], marginBottom: 6 }}>
                        {z.defect_class}
                      </div>
                      <div style={{ fontSize: 11, color: "#8899aa", marginBottom: 6 }}>
                        🧠 <em>{z.causal_explanation}</em>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11 }}>
                        <span style={{ color: "#aabbcc" }}>Confidence: <strong style={{ color: "#00d4ff" }}>{(z.confidence * 100).toFixed(1)}%</strong></span>
                        <span style={{ color: "#aabbcc" }}>Depth: <strong>{z.depth_m}m</strong></span>
                      </div>
                      {z.repair_cost_usd > 0 && (
                        <div style={{ marginTop: 6, fontSize: 11, color: "#ffab00" }}>
                          💰 Est. Repair: USD {z.repair_cost_usd.toLocaleString()}
                        </div>
                      )}
                      <div style={{ marginTop: 6, fontSize: 11, color: "#aabbcc" }}>
                        📋 {z.action}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
