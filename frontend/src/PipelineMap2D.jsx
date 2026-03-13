/**
 * PipelineMap2D.jsx
 * 2D unrolled pipeline defect map.
 * Defects plotted from REAL bbox coordinates — no guessing.
 * Pipe is "unwrapped" into a flat rectangle:
 *   X-axis = pipe length (0% → 100%)
 *   Y-axis = circumference angle (0° top → 360° bottom)
 */

import React, { useRef, useEffect, useState, useCallback } from "react";

// ── Severity colors ──────────────────────────────────────────────────────────
const SEV_COLOR = {
  Critical: "#ef4444",
  High:     "#f97316",
  Medium:   "#f59e0b",
  Low:      "#22c55e",
  Unknown:  "#6b7280",
};

const CLASSES_ICON = {
  corrosion:      "🔴",
  crack:          "⚡",
  biofouling:     "🟤",
  coating_damage: "🟠",
  anode_depletion:"🟡",
  marine_growth:  "🟢",
  dent:           "🔵",
  weld_defect:    "⚪",
  leak:           "💧",
  free_span:      "〰️",
};

// ── Map a detection bbox to pipe coordinates ─────────────────────────────────
function bboxToPipeCoords(bbox, imgW = 1280, imgH = 720) {
  // center of bbox in image coords
  const cx = ((bbox.xmin ?? bbox.x1 ?? 0) + (bbox.xmax ?? bbox.x2 ?? imgW)) / 2;
  const cy = ((bbox.ymin ?? bbox.y1 ?? 0) + (bbox.ymax ?? bbox.y2 ?? imgH)) / 2;
  // map to 0-1 range
  const pipePos = cx / imgW;       // 0 = left end, 1 = right end
  const angle   = (cy / imgH);     // 0 = top, 1 = bottom of pipe
  return { pipePos, angle };
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function PipelineMap2D({ detResult, imgW = 1280, imgH = 720 }) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);

  const [zoom,    setZoom]    = useState(1);
  const [pan,     setPan]     = useState({ x: 0, y: 0 });
  const [dragging,setDragging]= useState(false);
  const [dragStart,setDragStart]=useState({ x:0, y:0 });
  const [hovered, setHovered] = useState(null);
  const [selected,setSelected]= useState(null);

  // build defect map from real bbox coords
  const defects = React.useMemo(() => {
    if (!detResult?.detections?.length) return [];
    return detResult.detections.map((d, i) => {
      const { pipePos, angle } = bboxToPipeCoords(d.bbox || {}, imgW, imgH);
      return {
        id:       i,
        cls:      d.cls ?? d.class ?? "unknown",
        severity: d.severity ?? "Unknown",
        conf:     d.conf ?? 0,
        pipePos,        // 0–1 along pipe length
        angle,          // 0–1 around circumference
        color:    SEV_COLOR[d.severity] ?? SEV_COLOR.Unknown,
        bbox:     d.bbox,
      };
    });
  }, [detResult, imgW, imgH]);

  // ── Draw ───────────────────────────────────────────────────────────────────
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx   = canvas.getContext("2d");
    const W     = canvas.width;
    const H     = canvas.height;

    ctx.clearRect(0, 0, W, H);

    // transform
    ctx.save();
    ctx.translate(pan.x, pan.y);
    ctx.scale(zoom, zoom);

    const mapX = 60, mapY = 80;
    const mapW = W - 120, mapH = H - 160;

    // ── Background ──
    const bg = ctx.createLinearGradient(mapX, mapY, mapX, mapY + mapH);
    bg.addColorStop(0,   "rgba(10,20,40,0.95)");
    bg.addColorStop(0.5, "rgba(15,30,60,0.95)");
    bg.addColorStop(1,   "rgba(10,20,40,0.95)");
    ctx.fillStyle = bg;
    ctx.beginPath();
    ctx.roundRect(mapX, mapY, mapW, mapH, 8);
    ctx.fill();

    // ── Pipe surface texture — horizontal stripes ──
    ctx.strokeStyle = "rgba(34,211,238,0.04)";
    ctx.lineWidth = 1;
    for (let y = mapY; y < mapY + mapH; y += 20) {
      ctx.beginPath(); ctx.moveTo(mapX, y); ctx.lineTo(mapX + mapW, y); ctx.stroke();
    }
    // vertical guides every 10%
    for (let i = 0; i <= 10; i++) {
      const x = mapX + (mapW * i) / 10;
      ctx.strokeStyle = i % 5 === 0 ? "rgba(34,211,238,0.15)" : "rgba(34,211,238,0.06)";
      ctx.lineWidth = i % 5 === 0 ? 1.5 : 0.5;
      ctx.beginPath(); ctx.moveTo(x, mapY); ctx.lineTo(x, mapY + mapH); ctx.stroke();
    }

    // ── Border ──
    ctx.strokeStyle = "rgba(34,211,238,0.4)";
    ctx.lineWidth   = 2;
    ctx.beginPath();
    ctx.roundRect(mapX, mapY, mapW, mapH, 8);
    ctx.stroke();

    // ── Top/bottom edge highlight (pipe ends) ──
    ctx.strokeStyle = "rgba(34,211,238,0.6)";
    ctx.lineWidth   = 3;
    ctx.beginPath(); ctx.moveTo(mapX, mapY); ctx.lineTo(mapX + mapW, mapY); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(mapX, mapY + mapH); ctx.lineTo(mapX + mapW, mapY + mapH); ctx.stroke();

    // ── X-axis labels (pipe length 0–100m) ──
    ctx.fillStyle   = "rgba(34,211,238,0.6)";
    ctx.font        = "11px monospace";
    ctx.textAlign   = "center";
    for (let i = 0; i <= 10; i++) {
      const x = mapX + (mapW * i) / 10;
      ctx.fillText(`${i * 10}m`, x, mapY + mapH + 18);
    }
    ctx.fillStyle = "rgba(255,255,255,0.3)";
    ctx.fillText("PIPE LENGTH →", mapX + mapW / 2, mapY + mapH + 36);

    // ── Y-axis labels (angle around circumference) ──
    ctx.textAlign  = "right";
    ctx.font       = "10px monospace";
    ctx.fillStyle  = "rgba(34,211,238,0.5)";
    const angleLabels = [["TOP", 0], ["90°", 0.25], ["BOTTOM", 0.5], ["270°", 0.75], ["TOP", 1]];
    for (const [label, frac] of angleLabels) {
      const y = mapY + mapH * frac;
      ctx.fillText(label, mapX - 8, y + 4);
    }

    // ── Weld seam line at top/bottom ──
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = "rgba(255,255,255,0.08)";
    ctx.lineWidth   = 1;
    ctx.beginPath(); ctx.moveTo(mapX, mapY + mapH * 0.5); ctx.lineTo(mapX + mapW, mapY + mapH * 0.5); ctx.stroke();
    ctx.setLineDash([]);

    // ── Weld rings (support rings every 20m) ──
    for (let i = 1; i < 5; i++) {
      const x = mapX + (mapW * i) / 5;
      ctx.strokeStyle = "rgba(34,85,170,0.4)";
      ctx.lineWidth   = 4;
      ctx.beginPath(); ctx.moveTo(x, mapY); ctx.lineTo(x, mapY + mapH); ctx.stroke();
      ctx.fillStyle = "rgba(34,85,170,0.7)";
      ctx.font = "9px monospace";
      ctx.textAlign = "center";
      ctx.fillText(`RING ${i}`, x, mapY + 12);
    }

    // ── Defect markers ──
    for (const d of defects) {
      const dx = mapX + d.pipePos * mapW;
      const dy = mapY + d.angle   * mapH;
      const r  = d.severity === "Critical" ? 12 : d.severity === "High" ? 10 : 8;
      const isHov = hovered?.id  === d.id;
      const isSel = selected?.id === d.id;

      // glow
      const glow = ctx.createRadialGradient(dx, dy, 0, dx, dy, r * 3);
      glow.addColorStop(0,   d.color + "55");
      glow.addColorStop(1,   d.color + "00");
      ctx.fillStyle = glow;
      ctx.beginPath(); ctx.arc(dx, dy, r * 3, 0, Math.PI * 2); ctx.fill();

      // pulse ring
      ctx.strokeStyle = d.color + "88";
      ctx.lineWidth   = 1.5;
      ctx.beginPath(); ctx.arc(dx, dy, r + 5, 0, Math.PI * 2); ctx.stroke();

      // main circle
      ctx.fillStyle   = d.color;
      ctx.strokeStyle = isHov || isSel ? "#ffffff" : d.color + "cc";
      ctx.lineWidth   = isHov || isSel ? 2.5 : 1.5;
      ctx.beginPath(); ctx.arc(dx, dy, r, 0, Math.PI * 2);
      ctx.fill(); ctx.stroke();

      // inner dot
      ctx.fillStyle = "rgba(0,0,0,0.5)";
      ctx.beginPath(); ctx.arc(dx, dy, r * 0.35, 0, Math.PI * 2); ctx.fill();

      // label — only on hover or selected, never always-on to avoid overlap
      if (isHov || isSel) {
        ctx.font         = "bold 11px monospace";
        ctx.textAlign    = "left";
        ctx.textBaseline = "middle";
        const label = `${d.cls} (${(d.conf * 100).toFixed(0)}%)`;
        const tw    = ctx.measureText(label).width;
        // smart placement: flip left if near right edge
        const lx = (dx + r + 8 + tw + 8 > mapX + mapW) ? dx - r - tw - 12 : dx + r + 6;
        const ly = dy;
        // background pill
        ctx.fillStyle = "rgba(0,0,0,0.85)";
        ctx.beginPath();
        ctx.roundRect(lx - 4, ly - 9, tw + 10, 18, 4);
        ctx.fill();
        // border
        ctx.strokeStyle = d.color + "99";
        ctx.lineWidth   = 1;
        ctx.stroke();
        // text
        ctx.fillStyle = d.color;
        ctx.fillText(label, lx, ly);
      }
    }

    // ── Tooltip for selected ──
    if (selected) {
      const dx = mapX + selected.pipePos * mapW;
      const dy = mapY + selected.angle   * mapH;
      const tx = dx + 16, ty = Math.max(mapY + 10, dy - 50);
      const lines = [
        `Class:    ${selected.cls}`,
        `Severity: ${selected.severity}`,
        `Conf:     ${(selected.conf * 100).toFixed(1)}%`,
        `Pos:      ${(selected.pipePos * 100).toFixed(1)}m`,
        `Angle:    ${(selected.angle * 360).toFixed(0)}°`,
      ];
      const tw = 210, th = lines.length * 18 + 16;
      ctx.fillStyle   = "rgba(8,15,30,0.95)";
      ctx.strokeStyle = selected.color;
      ctx.lineWidth   = 1.5;
      ctx.beginPath(); ctx.roundRect(tx, ty, tw, th, 6); ctx.fill(); ctx.stroke();
      ctx.font        = "11px monospace";
      ctx.textAlign   = "left";
      lines.forEach((line, i) => {
        ctx.fillStyle = i === 0 ? selected.color : "rgba(255,255,255,0.8)";
        ctx.fillText(line, tx + 10, ty + 14 + i * 18);
      });
    }

    // ── Title ──
    ctx.restore();
    ctx.fillStyle   = "rgba(34,211,238,0.9)";
    ctx.font        = "bold 14px monospace";
    ctx.textAlign   = "left";
    ctx.textBaseline= "top";
    ctx.fillText("PIPELINE DEFECT MAP — UNROLLED VIEW", 16, 12);
    ctx.fillStyle = "rgba(255,255,255,0.3)";
    ctx.font      = "11px monospace";
    ctx.fillText(`${defects.length} defects mapped from real bbox coordinates`, 16, 30);
    if (detResult?.mission_id) {
      ctx.fillStyle = "rgba(34,211,238,0.5)";
      ctx.textAlign = "right";
      ctx.fillText(`Mission: ${detResult.mission_id}`, canvasRef.current?.width - 16, 12);
    }

  }, [defects, zoom, pan, hovered, selected, detResult]);

  // redraw on state change
  useEffect(() => { draw(); }, [draw]);

  // resize observer
  useEffect(() => {
    const canvas    = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    const ro = new ResizeObserver(() => {
      canvas.width  = container.clientWidth;
      canvas.height = container.clientHeight;
      draw();
    });
    ro.observe(container);
    canvas.width  = container.clientWidth;
    canvas.height = container.clientHeight;
    draw();
    return () => ro.disconnect();
  }, [draw]);

  // ── Hit test ──────────────────────────────────────────────────────────────
  const hitTest = useCallback((e) => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const rect  = canvas.getBoundingClientRect();
    const mx    = (e.clientX - rect.left - pan.x) / zoom;
    const my    = (e.clientY - rect.top  - pan.y) / zoom;
    const mapX  = 60, mapY = 80;
    const mapW  = canvas.width - 120, mapH = canvas.height - 160;
    for (const d of defects) {
      const dx = mapX + d.pipePos * mapW;
      const dy = mapY + d.angle   * mapH;
      const r  = d.severity === "Critical" ? 12 : d.severity === "High" ? 10 : 8;
      if (Math.hypot(mx - dx, my - dy) <= r + 4) return d;
    }
    return null;
  }, [defects, zoom, pan]);

  const onMouseMove = useCallback((e) => {
    if (dragging) {
      setPan(p => ({ x: p.x + e.movementX, y: p.y + e.movementY }));
    } else {
      setHovered(hitTest(e));
    }
  }, [dragging, hitTest]);

  const onMouseDown = useCallback((e) => {
    const hit = hitTest(e);
    if (hit) { setSelected(s => s?.id === hit.id ? null : hit); }
    else      { setDragging(true); }
  }, [hitTest]);

  const onMouseUp   = () => setDragging(false);
  const onMouseLeave= () => { setHovered(null); setDragging(false); };
  const onWheel     = (e) => {
    e.preventDefault();
    setZoom(z => Math.min(4, Math.max(0.5, z - e.deltaY * 0.001)));
  };

  // ── Legend ────────────────────────────────────────────────────────────────
  const sevCounts = defects.reduce((acc, d) => {
    acc[d.severity] = (acc[d.severity] || 0) + 1; return acc;
  }, {});

  return (
    <div style={{ marginTop: 20 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <div>
          <div style={{ fontSize: 11, opacity: 0.5, letterSpacing: 1, textTransform: "uppercase" }}>2D Pipeline Map</div>
          <div style={{ fontSize: 16, fontWeight: 700 }}>Unrolled Defect View — Real Coordinates</div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={() => { setZoom(1); setPan({ x:0, y:0 }); }}
            style={{ padding: "4px 12px", background: "rgba(34,211,238,0.1)", border: "1px solid rgba(34,211,238,0.3)", borderRadius: 4, color: "#22d3ee", cursor: "pointer", fontSize: 11 }}>
            Reset View
          </button>
          <button onClick={() => setZoom(z => Math.min(4, z + 0.25))}
            style={{ padding: "4px 10px", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 4, color: "white", cursor: "pointer", fontSize: 13 }}>
            +
          </button>
          <button onClick={() => setZoom(z => Math.max(0.5, z - 0.25))}
            style={{ padding: "4px 10px", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 4, color: "white", cursor: "pointer", fontSize: 13 }}>
            −
          </button>
        </div>
      </div>

      {/* Legend */}
      <div style={{ display: "flex", gap: 16, marginBottom: 10, flexWrap: "wrap" }}>
        {Object.entries(SEV_COLOR).filter(([k]) => k !== "Unknown").map(([sev, col]) => (
          <div key={sev} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11 }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: col, display: "inline-block" }} />
            <span style={{ color: col }}>{sev}</span>
            {sevCounts[sev] && <span style={{ opacity: 0.5 }}>({sevCounts[sev]})</span>}
          </div>
        ))}
        <div style={{ fontSize: 11, opacity: 0.4, marginLeft: "auto" }}>
          Scroll to zoom · Drag to pan · Click defect for details
        </div>
      </div>

      {/* Canvas */}
      <div ref={containerRef} style={{ width: "100%", height: 420, borderRadius: 8, overflow: "hidden", background: "#060d1a", border: "1px solid rgba(34,211,238,0.2)", cursor: dragging ? "grabbing" : hovered ? "pointer" : "grab" }}>
        <canvas ref={canvasRef}
          onMouseMove={onMouseMove} onMouseDown={onMouseDown}
          onMouseUp={onMouseUp} onMouseLeave={onMouseLeave}
          onWheel={onWheel}
          style={{ display: "block" }}
        />
      </div>

      {/* Selected defect detail */}
      {selected && (
        <div style={{ marginTop: 10, padding: "12px 16px", background: `${selected.color}11`, border: `1px solid ${selected.color}44`, borderRadius: 8, display: "flex", gap: 24, flexWrap: "wrap" }}>
          <div>
            <div style={{ fontSize: 10, opacity: 0.5, letterSpacing: 1, marginBottom: 2 }}>CLASS</div>
            <div style={{ fontWeight: 700, color: selected.color }}>{selected.cls}</div>
          </div>
          <div>
            <div style={{ fontSize: 10, opacity: 0.5, letterSpacing: 1, marginBottom: 2 }}>SEVERITY</div>
            <div style={{ fontWeight: 700, color: selected.color }}>{selected.severity}</div>
          </div>
          <div>
            <div style={{ fontSize: 10, opacity: 0.5, letterSpacing: 1, marginBottom: 2 }}>CONFIDENCE</div>
            <div style={{ fontWeight: 700 }}>{(selected.conf * 100).toFixed(1)}%</div>
          </div>
          <div>
            <div style={{ fontSize: 10, opacity: 0.5, letterSpacing: 1, marginBottom: 2 }}>PIPE POSITION</div>
            <div style={{ fontWeight: 700 }}>{(selected.pipePos * 100).toFixed(1)}m</div>
          </div>
          <div>
            <div style={{ fontSize: 10, opacity: 0.5, letterSpacing: 1, marginBottom: 2 }}>ANGLE</div>
            <div style={{ fontWeight: 700 }}>{(selected.angle * 360).toFixed(0)}°</div>
          </div>
          {selected.bbox && (
            <div>
              <div style={{ fontSize: 10, opacity: 0.5, letterSpacing: 1, marginBottom: 2 }}>BBOX</div>
              <div style={{ fontWeight: 700, fontFamily: "monospace", fontSize: 11 }}>
                ({selected.bbox.xmin ?? selected.bbox.x1 ?? "?"},  {selected.bbox.ymin ?? selected.bbox.y1 ?? "?"}) → ({selected.bbox.xmax ?? selected.bbox.x2 ?? "?"}, {selected.bbox.ymax ?? selected.bbox.y2 ?? "?"})
              </div>
            </div>
          )}
          <button onClick={() => setSelected(null)} style={{ marginLeft: "auto", background: "none", border: "none", color: "rgba(255,255,255,0.4)", cursor: "pointer", fontSize: 16 }}>✕</button>
        </div>
      )}

      {defects.length === 0 && (
        <div style={{ textAlign: "center", padding: 24, opacity: 0.3, fontSize: 13 }}>
          Run a pipeline scan to populate the defect map with real coordinates
        </div>
      )}
    </div>
  );
}