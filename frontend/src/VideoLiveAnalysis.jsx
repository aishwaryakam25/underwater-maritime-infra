import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Radar } from "lucide-react";

function fmtTime(sec) {
  if (!Number.isFinite(sec) || sec < 0) return "00:00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function classColor(cls) {
  const c = String(cls || "").toLowerCase();
  if (c.includes("corrosion")) return "#ef4444";
  if (c.includes("crack")) return "#fb923c";
  if (c.includes("bio") || c.includes("foul") || c.includes("marine") || c.includes("algae") || c.includes("barnacle")) return "#f97316";
  return "#22d3ee";
}

function videoDisplayMetrics(video) {
  const vw = video.videoWidth || 1;
  const vh = video.videoHeight || 1;
  const cw = video.clientWidth || 1;
  const ch = video.clientHeight || 1;
  const scale = Math.min(cw / vw, ch / vh);
  const dw = vw * scale;
  const dh = vh * scale;
  const ox = (cw - dw) / 2;
  const oy = (ch - dh) / 2;
  return { scale, ox, oy, dw, dh, vw, vh };
}

function maxDetectionFrameIndex(detections) {
  let m = -1;
  for (const d of detections || []) {
    const f = Number(d.frame);
    if (Number.isFinite(f) && f >= 0) m = Math.max(m, f);
  }
  return m;
}

function detectionsAtTime(tSec, fps, totalFrames, stride, detections) {
  if (!stride || !fps || !detections?.length) return [];
  const maxDet = maxDetectionFrameIndex(detections);
  const metaCap = totalFrames > 0 ? totalFrames - 1 : null;
  let hardCap;
  if (maxDet >= 0) {
    hardCap = metaCap != null ? Math.min(maxDet, metaCap) : maxDet;
  } else {
    hardCap = metaCap != null ? metaCap : null;
  }

  let approx = Math.floor(Math.max(0, tSec) * fps);
  if (hardCap != null && Number.isFinite(hardCap)) {
    approx = Math.min(hardCap, Math.max(0, approx));
  }

  const maxBucket =
    hardCap != null && Number.isFinite(hardCap) ? Math.floor(hardCap / stride) * stride : Math.floor(approx / stride) * stride;
  let bucket = Math.floor(approx / stride) * stride;
  bucket = Math.min(bucket, maxBucket);

  const frameNums = [...new Set(detections.map((d) => Number(d.frame)).filter((n) => Number.isFinite(n) && n >= 0))].sort(
    (a, b) => a - b,
  );

  let matches = detections.filter((d) => Number(d.frame) === bucket);
  if (!matches.length && frameNums.length) {
    let nearest = frameNums[0];
    let best = Infinity;
    for (const f of frameNums) {
      const dist = Math.abs(f - approx);
      if (dist < best) {
        best = dist;
        nearest = f;
      }
    }
    matches = detections.filter((d) => Number(d.frame) === nearest);
  }
  return matches;
}

function bboxPixels(d, vw, vh) {
  let x1;
  let y1;
  let x2;
  let y2;
  if (Array.isArray(d.bbox) && d.bbox.length >= 4) {
    [x1, y1, x2, y2] = d.bbox.map((v) => Number(v));
  } else {
    x1 = Number(d.x1 ?? d.bbox?.xmin ?? 0);
    y1 = Number(d.y1 ?? d.bbox?.ymin ?? 0);
    x2 = Number(d.x2 ?? d.bbox?.xmax ?? 0);
    y2 = Number(d.y2 ?? d.bbox?.ymax ?? 0);
  }
  const norm = Math.max(x1, x2, y1, y2) <= 1.001;
  if (norm && vw > 0 && vh > 0) {
    x1 *= vw;
    x2 *= vw;
    y1 *= vh;
    y2 *= vh;
  }
  return { x1, y1, x2, y2 };
}

export default function VideoLiveAnalysis({
  videoFile,
  videoRef,
  setVideoFile,
  onDragOver,
  onDragLeave,
  analyzeVideo,
  genVideoPDF,
  exportAnnotatedVideo,
  videoLoading,
  videoPdfLoading,
  videoExportLoading,
  videoResult,
  error,
}) {
  const [viewMode, setViewMode] = useState("annotated");
  const [displayMode, setDisplayMode] = useState("video");
  const [currentT, setCurrentT] = useState(0);
  const videoElRef = useRef(null);
  const canvasRef = useRef(null);
  const wrapRef = useRef(null);
  const [videoUrl, setVideoUrl] = useState(null);
  const [mediaDuration, setMediaDuration] = useState(0);

  useEffect(() => {
    if (!videoFile) {
      setVideoUrl(null);
      return;
    }
    const url = URL.createObjectURL(videoFile);
    setVideoUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [videoFile]);

  useEffect(() => {
    setMediaDuration(0);
  }, [videoFile]);

  const vi = videoResult?.video_info || {};
  const fps = Number(vi.fps) || 25;
  const duration = Number(vi.duration) || 0;
  const totalFrames = Number(vi.total_frames) || 0;
  const durationFromFrames = totalFrames > 0 && fps > 0 ? totalFrames / fps : 0;
  const timelineDuration = Math.max(duration || 0, durationFromFrames || 0, mediaDuration || 0);
  const stride = Number(videoResult?.sample_stride) || 10;
  const detections = videoResult?.detections || [];
  const timelineHits = videoResult?.timeline_hits;

  const classCounts = useMemo(() => {
    const m = {};
    for (const d of detections) {
      const k = d.cls || d.class || "Unknown";
      m[k] = (m[k] || 0) + 1;
    }
    return Object.entries(m).sort((a, b) => b[1] - a[1]);
  }, [detections]);

  const timelineMarks = useMemo(() => {
    if (Array.isArray(timelineHits) && timelineHits.length > 0) {
      return timelineHits
        .map((h) => {
          const frameNum = Number(h.frame);
          return {
            frameNum,
            t: frameNum / fps,
            color: classColor(h.cls),
          };
        })
        .filter((m) => Number.isFinite(m.frameNum) && m.frameNum >= 0);
    }
    const byFrame = new Map();
    for (const d of detections) {
      const f = Number(d.frame);
      if (!Number.isFinite(f) || f < 0) continue;
      if (!byFrame.has(f)) byFrame.set(f, []);
      byFrame.get(f).push(d);
    }
    return [...byFrame.entries()]
      .sort((a, b) => a[0] - b[0])
      .map(([frameNum, dets]) => ({
        frameNum,
        t: frameNum / fps,
        color: classColor(dets[0]?.cls || dets[0]?.class),
      }));
  }, [timelineHits, detections, fps]);

  const gradeUp = String(videoResult?.grade || "").toUpperCase();
  const highRisk =
    ["F", "D", "C"].includes(gradeUp) ||
    (videoResult?.risk_score != null && Number(videoResult.risk_score) < 52);

  const drawOverlay = useCallback(() => {
    const video = videoElRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || viewMode !== "annotated" || displayMode !== "video") return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const cw = video.clientWidth;
    const ch = video.clientHeight;
    canvas.width = cw;
    canvas.height = ch;
    ctx.clearRect(0, 0, cw, ch);
    const { scale, ox, oy, vw, vh } = videoDisplayMetrics(video);
    const active = detectionsAtTime(video.currentTime || 0, fps, totalFrames, stride, detections);
    for (const d of active) {
      const { x1, y1, x2, y2 } = bboxPixels(d, vw, vh);
      const col = classColor(d.cls || d.class);
      const sx1 = x1 * scale + ox;
      const sy1 = y1 * scale + oy;
      const sw = (x2 - x1) * scale;
      const sh = (y2 - y1) * scale;
      ctx.strokeStyle = col;
      ctx.lineWidth = Math.max(2, Math.round(2 * (scale || 1)));
      ctx.strokeRect(sx1, sy1, sw, sh);
      const label = `${d.cls || d.class || "?"} ${((Number(d.conf) || 0) * 100).toFixed(0)}%`;
      ctx.font = "600 13px Segoe UI, system-ui, sans-serif";
      const tw = ctx.measureText(label).width;
      ctx.fillStyle = "rgba(0,0,0,0.72)";
      ctx.fillRect(sx1, sy1 - 22, tw + 12, 20);
      ctx.fillStyle = col;
      ctx.fillText(label, sx1 + 6, sy1 - 6);
    }
  }, [viewMode, displayMode, fps, totalFrames, stride, detections]);

  useEffect(() => {
    drawOverlay();
  }, [drawOverlay, currentT]);

  useEffect(() => {
    const ro = new ResizeObserver(() => drawOverlay());
    if (wrapRef.current) ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, [drawOverlay]);

  const onTime = () => {
    const v = videoElRef.current;
    if (v) setCurrentT(v.currentTime || 0);
    drawOverlay();
  };

  const seekTo = (t) => {
    const v = videoElRef.current;
    if (!v) return;
    const cap =
      Number.isFinite(v.duration) && v.duration > 0
        ? v.duration
        : timelineDuration > 0
          ? timelineDuration
          : 0;
    if (!cap) return;
    v.currentTime = Math.max(0, Math.min(cap, t));
    setCurrentT(v.currentTime);
    drawOverlay();
  };

  const sampleFrames = videoResult?.sample_frames ?? videoResult?.frames ?? [];

  const playheadPct =
    timelineDuration > 0 ? Math.min(100, (currentT / timelineDuration) * 100) : 0;
  const activeNow = detectionsAtTime(currentT, fps, totalFrames, stride, detections);

  return (
    <div style={{ marginTop: 8 }}>
      {!videoResult && (
        <div className="card mb-20">
          <div className="card-title">Video Upload</div>
          <div
            className="dropzone"
            onClick={() => videoRef.current?.click()}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={(e) => {
              e.preventDefault();
              e.currentTarget.classList.remove("drag-over");
              setVideoFile(e.dataTransfer.files[0]);
            }}
          >
            <div className="dz-icon">🎬</div>
            <div className="dz-label">{videoFile ? "Click or drop to replace" : "Drop video file here"}</div>
            <div className="dz-hint">Supported: MP4, AVI, MOV</div>
            {videoFile && (
              <div className="dz-file">
                ✓ {videoFile.name}
                {videoFile.size != null && (
                  <span style={{ opacity: 0.55, marginLeft: 8 }}>({(videoFile.size / (1024 * 1024)).toFixed(1)} MB)</span>
                )}
              </div>
            )}
          </div>
          <input ref={videoRef} type="file" accept="video/*" hidden onChange={(e) => setVideoFile(e.target.files[0])} />
        </div>
      )}

      {!videoResult && (
        <div className="row mb-20" style={{ gap: 10, flexWrap: "wrap" }}>
          <button className="btn btn-primary" disabled={!videoFile || videoLoading} onClick={analyzeVideo}>
            {videoLoading && <span className="spinner" />} Analyze Video
          </button>
          <button className="btn btn-ghost" disabled={!videoFile || videoPdfLoading || videoLoading} onClick={genVideoPDF}>
            {videoPdfLoading && <span className="spinner" />} 📄 PDF
          </button>
        </div>
      )}

      {!videoResult && (
        <div
          className="card mb-20"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 14,
            padding: "14px 18px",
            border: "1px solid rgba(251, 191, 36, 0.4)",
            background: "linear-gradient(135deg, rgba(251,191,36,0.08) 0%, rgba(34,211,238,0.05) 100%)",
          }}
          aria-label="Live tracking available after analysis"
        >
          <div
            style={{
              flexShrink: 0,
              width: 48,
              height: 48,
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: "rgba(251, 191, 36, 0.18)",
              color: "#fbbf24",
              border: "1px solid rgba(251, 191, 36, 0.45)",
              boxShadow: "0 0 20px rgba(251, 191, 36, 0.15)",
            }}
          >
            <Radar size={26} strokeWidth={2.25} aria-hidden />
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <span style={{ fontWeight: 800, letterSpacing: 1.4, fontSize: 12, color: "#fbbf24" }}>LIVE TRACKING</span>
              <span
                style={{
                  fontSize: 9,
                  fontWeight: 700,
                  letterSpacing: 0.8,
                  padding: "2px 8px",
                  borderRadius: 4,
                  background: "rgba(34,211,238,0.12)",
                  color: "#22d3ee",
                  border: "1px solid rgba(34,211,238,0.25)",
                }}
              >
                AFTER ANALYZE
              </span>
            </div>
            <p style={{ margin: "8px 0 0", fontSize: 12, opacity: 0.78, lineHeight: 1.45 }}>
              Bounding boxes and class labels follow playback on the timeline. Run <strong style={{ color: "#22d3ee" }}>Analyze Video</strong> to open the
              tracker view (scrub or play — overlays snap to sampled frames).
            </p>
          </div>
        </div>
      )}

      <StatusBarInline error={error} />
      {videoPdfLoading && !videoResult && (
        <p style={{ marginTop: 12, fontSize: 13, opacity: 0.75 }}>
          Generating PDF — this runs the full video again and may take several minutes. Keep this tab open.
        </p>
      )}

      {videoResult && (
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 18,
            alignItems: "flex-start",
            marginTop: 8,
          }}
        >
          <aside
            style={{
              width: 300,
              flexShrink: 0,
              display: "flex",
              flexDirection: "column",
              gap: 14,
            }}
          >
            <div
              className="card"
              style={{
                padding: 14,
                border: "1px solid rgba(34,211,238,0.15)",
                background: "rgba(8,14,24,0.85)",
              }}
            >
              <div style={{ fontSize: 11, opacity: 0.45, letterSpacing: 1, marginBottom: 8 }}>UPLOAD</div>
              <div style={{ fontSize: 12, fontWeight: 600, wordBreak: "break-all", marginBottom: 10 }}>
                {videoFile?.name || "Video"}
              </div>
              <button type="button" className="btn btn-ghost btn-sm" style={{ width: "100%" }} onClick={() => videoRef.current?.click()}>
                Replace video
              </button>
              <input ref={videoRef} type="file" accept="video/*" hidden onChange={(e) => setVideoFile(e.target.files[0])} />
            </div>

            <div style={{ display: "flex", gap: 6 }}>
              <button
                type="button"
                className={displayMode === "video" ? "btn btn-primary" : "btn btn-ghost"}
                style={{ flex: 1, fontSize: 11 }}
                onClick={() => setDisplayMode("video")}
              >
                Annotated Video
              </button>
              <button
                type="button"
                className={displayMode === "frames" ? "btn btn-primary" : "btn btn-ghost"}
                style={{ flex: 1, fontSize: 11 }}
                onClick={() => setDisplayMode("frames")}
              >
                Frame Mode
              </button>
            </div>

            <div
              className="card"
              style={{
                padding: 14,
                border: highRisk ? "1px solid rgba(239,68,68,0.35)" : "1px solid rgba(51,65,85,0.4)",
                background: "rgba(15,23,42,0.6)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 800,
                    letterSpacing: 1,
                    padding: "5px 12px",
                    borderRadius: 6,
                    background: highRisk ? "rgba(239,68,68,0.2)" : "rgba(52,211,153,0.15)",
                    color: highRisk ? "#f87171" : "#4ade80",
                    border: `1px solid ${highRisk ? "rgba(239,68,68,0.45)" : "rgba(52,211,153,0.35)"}`,
                  }}
                >
                  {highRisk ? "HIGH RISK" : "WITHIN TOLERANCE"}
                </span>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                {[
                  ["Frames analyzed", String(videoResult.frames_processed ?? "—")],
                  ["Detections", String(videoResult.total_detections ?? 0)],
                  ["Duration", `${vi.duration ?? "—"}s`],
                  ["Video FPS", String(vi.fps ?? "—")],
                ].map(([k, v]) => (
                  <div key={k} style={{ padding: "10px 8px", borderRadius: 8, background: "rgba(0,0,0,0.25)" }}>
                    <div style={{ fontSize: 9, opacity: 0.45, letterSpacing: 0.8, marginBottom: 4 }}>{k}</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: "#22d3ee", fontFamily: "JetBrains Mono, monospace" }}>{v}</div>
                  </div>
                ))}
              </div>
              {classCounts.length > 0 && (
                <div style={{ marginTop: 14, paddingTop: 12, borderTop: "1px solid rgba(255,255,255,0.06)" }}>
                  <div style={{ fontSize: 10, opacity: 0.4, letterSpacing: 1, marginBottom: 8 }}>CLASSES</div>
                  {classCounts.slice(0, 8).map(([cls, n]) => (
                    <div key={cls} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6, fontSize: 12 }}>
                      <span style={{ width: 10, height: 10, borderRadius: "50%", background: classColor(cls), flexShrink: 0 }} />
                      <span style={{ flex: 1 }}>{cls}</span>
                      <span style={{ fontWeight: 700, color: "#94a3b8" }}>{n}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <button
              type="button"
              className="btn btn-primary"
              style={{ width: "100%" }}
              disabled={videoExportLoading || videoLoading || !videoFile}
              onClick={exportAnnotatedVideo}
            >
              {videoExportLoading && <span className="spinner" />} Download Video
            </button>
            <button type="button" className="btn btn-ghost" style={{ width: "100%" }} disabled={videoPdfLoading || videoLoading} onClick={genVideoPDF}>
              {videoPdfLoading && <span className="spinner" />} View Report (PDF)
            </button>
            <button type="button" className="btn btn-ghost btn-sm" disabled={videoLoading} onClick={analyzeVideo}>
              {videoLoading && <span className="spinner" />} Re-analyze
            </button>
            {videoPdfLoading && (
              <p style={{ fontSize: 12, opacity: 0.65, margin: 0 }}>
                Generating PDF — runs the full video again; keep this tab open.
              </p>
            )}
          </aside>

          <div style={{ flex: 1, minWidth: 280 }}>
            {displayMode === "video" && videoUrl && (
              <>
                <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
                  {[
                    ["annotated", "ANNOTATED OUTPUT"],
                    ["original", "ORIGINAL VIDEO"],
                  ].map(([id, lab]) => (
                    <button
                      key={id}
                      type="button"
                      onClick={() => setViewMode(id)}
                      style={{
                        padding: "8px 16px",
                        borderRadius: 8,
                        border: viewMode === id ? "1px solid rgba(34,211,238,0.45)" : "1px solid rgba(255,255,255,0.08)",
                        background: viewMode === id ? "rgba(34,211,238,0.12)" : "transparent",
                        color: viewMode === id ? "#22d3ee" : "rgba(255,255,255,0.45)",
                        fontSize: 11,
                        fontWeight: viewMode === id ? 700 : 500,
                        letterSpacing: 1,
                        cursor: "pointer",
                      }}
                    >
                      {lab}
                    </button>
                  ))}
                </div>

                <div
                  ref={wrapRef}
                  style={{
                    position: "relative",
                    background: "#000",
                    borderRadius: 10,
                    overflow: "hidden",
                    border: "1px solid rgba(34,211,238,0.12)",
                    aspectRatio: (() => {
                      const r = vi.resolution;
                      if (r && String(r).includes("x")) {
                        const [w0, h0] = String(r).split("x");
                        const wa = parseInt(w0, 10);
                        const ha = parseInt(h0, 10);
                        if (wa > 0 && ha > 0) return `${wa} / ${ha}`;
                      }
                      return "16 / 9";
                    })(),
                    maxHeight: "min(72vh, 640px)",
                  }}
                >
                  <video
                    ref={videoElRef}
                    src={videoUrl || undefined}
                    controls
                    playsInline
                    style={{
                      width: "100%",
                      height: "100%",
                      display: "block",
                      objectFit: "contain",
                      opacity: viewMode === "original" ? 1 : 1,
                    }}
                    onTimeUpdate={onTime}
                    onLoadedMetadata={(e) => {
                      const d = e.currentTarget.duration;
                      if (Number.isFinite(d) && d > 0) setMediaDuration(d);
                      drawOverlay();
                    }}
                    onLoadedData={drawOverlay}
                    onPlay={drawOverlay}
                  />
                  <canvas
                    ref={canvasRef}
                    style={{
                      position: "absolute",
                      left: 0,
                      top: 0,
                      width: "100%",
                      height: "100%",
                      pointerEvents: "none",
                      display: viewMode === "annotated" ? "block" : "none",
                    }}
                  />

                  <div
                    style={{
                      position: "absolute",
                      bottom: 12,
                      left: 12,
                      padding: "6px 12px",
                      borderRadius: 6,
                      background: "rgba(0,0,0,0.75)",
                      fontSize: 13,
                      fontWeight: 700,
                      color: "#fbbf24",
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {fmtTime(currentT)}
                  </div>

                  <div
                    style={{
                      position: "absolute",
                      bottom: 12,
                      right: 12,
                      padding: "8px 12px",
                      borderRadius: 8,
                      background: "rgba(0,0,0,0.78)",
                      border: "1px solid rgba(251,191,36,0.35)",
                      fontSize: 11,
                      textAlign: "right",
                      maxWidth: 200,
                    }}
                  >
                    <div style={{ color: "#e2e8f0" }}>
                      {activeNow.length} detection{activeNow.length === 1 ? "" : "s"} @ sampled frame
                    </div>
                    <div style={{ color: "#fbbf24", fontWeight: 800, letterSpacing: 1, marginTop: 4 }}>TRACKING</div>
                  </div>

                  <div
                    style={{
                      position: "absolute",
                      top: 14,
                      left: 14,
                      maxWidth: "42%",
                      padding: "10px 12px",
                      borderRadius: 8,
                      background: "rgba(30,58,138,0.55)",
                      border: "1px solid rgba(96,165,250,0.35)",
                      fontSize: 11,
                      color: "#bfdbfe",
                      lineHeight: 1.45,
                    }}
                  >
                    <div style={{ fontWeight: 700, marginBottom: 4 }}>Distance Lock System</div>
                    <div style={{ opacity: 0.85 }}>
                      Maintain steady stand-off during inspection; overlays follow sampled frames (
                      {stride}
                      -frame stride).
                    </div>
                  </div>
                </div>

                <div style={{ marginTop: 16 }}>
                  <div style={{ fontSize: 10, opacity: 0.42, letterSpacing: 1.2, marginBottom: 8, fontWeight: 600 }}>
                    DETECTION TIMELINE — CLICK TO SEEK
                  </div>
                  <div
                    role="slider"
                    tabIndex={0}
                    aria-valuenow={Math.round(currentT)}
                    aria-valuemin={0}
                    aria-valuemax={Math.ceil(timelineDuration || duration)}
                    style={{
                      position: "relative",
                      height: 44,
                      borderRadius: 8,
                      background: "rgba(15,23,42,0.9)",
                      border: "1px solid rgba(51,65,85,0.5)",
                      cursor: "pointer",
                    }}
                    onClick={(e) => {
                      const r = e.currentTarget.getBoundingClientRect();
                      const x = e.clientX - r.left;
                      const pct = x / r.width;
                      seekTo(pct * (timelineDuration || duration));
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "ArrowRight") seekTo(currentT + 2);
                      if (e.key === "ArrowLeft") seekTo(currentT - 2);
                    }}
                  >
                    <div
                      style={{
                        position: "absolute",
                        left: 0,
                        right: 0,
                        top: "50%",
                        height: 3,
                        transform: "translateY(-50%)",
                        background: "rgba(51,65,85,0.9)",
                        borderRadius: 2,
                      }}
                    />
                    {timelineMarks.map((mk) => (
                      <div
                        key={mk.frameNum}
                        title={`${fmtTime(mk.t)} · frame ${mk.frameNum}`}
                        style={{
                          position: "absolute",
                          left: `${timelineDuration > 0 ? (mk.t / timelineDuration) * 100 : 0}%`,
                          top: 8,
                          width: 3,
                          height: 28,
                          marginLeft: -1,
                          background: mk.color,
                          borderRadius: 1,
                          opacity: 0.92,
                          pointerEvents: "none",
                        }}
                      />
                    ))}
                    <div
                      style={{
                        position: "absolute",
                        left: `${playheadPct}%`,
                        top: 4,
                        width: 2,
                        height: 36,
                        marginLeft: -1,
                        background: "#22d3ee",
                        boxShadow: "0 0 12px rgba(34,211,238,0.8)",
                        borderRadius: 1,
                        pointerEvents: "none",
                        zIndex: 2,
                      }}
                    />
                  </div>
                  <div style={{ fontSize: 10, opacity: 0.38, marginTop: 6 }}>
                    Sample stride {stride} · {timelineMarks.length} sampled frames with hits
                  </div>
                </div>
              </>
            )}

            {displayMode === "frames" && sampleFrames.length > 0 && (
              <div className="card" style={{ padding: 14 }}>
                <div className="card-title" style={{ marginBottom: 12 }}>
                  Sampled keyframes (annotated)
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                  {sampleFrames.map((f, i) => {
                    const b64 = typeof f === "string" ? f : f?.annotated_b64;
                    return b64 ? (
                      <div key={i} style={{ textAlign: "center" }}>
                        <img
                          src={`data:image/jpeg;base64,${b64}`}
                          alt={`Frame ${i}`}
                          style={{ width: 220, borderRadius: 8, border: "1px solid rgba(34,211,238,0.2)" }}
                        />
                        <div style={{ fontSize: 10, opacity: 0.45, marginTop: 4 }}>f {f.frame_num ?? i}</div>
                      </div>
                    ) : null;
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function StatusBarInline({ error }) {
  if (!error) return null;
  return (
    <div className="card" style={{ marginTop: 12, padding: 12, borderColor: "rgba(239,68,68,0.35)", background: "rgba(239,68,68,0.08)" }}>
      <span style={{ color: "#f87171", fontSize: 13 }}>{error}</span>
    </div>
  );
}
