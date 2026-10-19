import React, { useMemo, useState, useCallback } from "react";
import HullViewer3D from "./HullViewer3D";

function donutSlicePath(cx, cy, rOut, rIn, start, sweep) {
  const x1o = cx + rOut * Math.cos(start);
  const y1o = cy + rOut * Math.sin(start);
  const x2o = cx + rOut * Math.cos(start + sweep);
  const y2o = cy + rOut * Math.sin(start + sweep);
  const x2i = cx + rIn * Math.cos(start + sweep);
  const y2i = cy + rIn * Math.sin(start + sweep);
  const x1i = cx + rIn * Math.cos(start);
  const y1i = cy + rIn * Math.sin(start);
  const large = sweep > Math.PI ? 1 : 0;
  return `M ${x1o} ${y1o} A ${rOut} ${rOut} 0 ${large} 1 ${x2o} ${y2o} L ${x2i} ${y2i} A ${rIn} ${rIn} 0 ${large} 0 ${x1i} ${y1i} Z`;
}

function HullDonutChart({ data, size = 152 }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  const cx = size / 2;
  const cy = size / 2;
  const rOut = size / 2 - 6;
  const rIn = rOut * 0.62;
  if (!total) return null;
  let ang = -Math.PI / 2;
  const slices = data.map((d, i) => {
    const sweep = (d.value / total) * 2 * Math.PI;
    const path = donutSlicePath(cx, cy, rOut, rIn, ang, sweep);
    const pct = Math.round((d.value / total) * 100);
    ang += sweep;
    return { ...d, path, pct, key: `${d.name}-${i}` };
  });
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ display: "block", margin: "0 auto" }}>
      {slices.map((s) => (
        <path key={s.key} d={s.path} fill={s.color} stroke="rgba(0,0,0,0.35)" strokeWidth={1} opacity={0.94}>
          <title>{`${s.name}: ${s.value} (${s.pct}%)`}</title>
        </path>
      ))}
    </svg>
  );
}

const CLASS_LEGEND_ORDER = ["corrosion", "crack", "biofouling", "debris"];

function sortBarRows(rows) {
  const idx = (name) => {
    const low = String(name || "").toLowerCase();
    const i = CLASS_LEGEND_ORDER.findIndex((k) => low.includes(k));
    return i === -1 ? 99 : i;
  };
  return [...rows].sort((a, b) => idx(a.name) - idx(b.name));
}

function HullHBarChart({ rows }) {
  const list = rows.length ? sortBarRows(rows) : [{ name: "—", avg: 0, fill: "#334155" }];
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 9, paddingTop: 6 }}>
      {list.map((row) => (
        <div key={row.name} style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div
            style={{
              width: 82,
              fontSize: 11,
              color: "#94a3b8",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
              flexShrink: 0,
              textTransform: "capitalize",
            }}
            title={row.name}
          >
            {row.name}
          </div>
          <div style={{ flex: 1, height: 12, background: "rgba(30,41,59,0.95)", borderRadius: 6, overflow: "hidden" }}>
            <div
              style={{
                width: `${Math.min(100, row.avg)}%`,
                height: "100%",
                background: row.fill || "#22d3ee",
                borderRadius: 6,
                transition: "width 0.35s ease",
              }}
              title={`${row.name}: ${row.avg}% avg confidence`}
            />
          </div>
          <div style={{ width: 36, fontSize: 11, fontFamily: "JetBrains Mono, monospace", color: "#94a3b8", textAlign: "right" }}>
            {row.avg}%
          </div>
        </div>
      ))}
    </div>
  );
}

function HullTrendChart({ points }) {
  const w = 320;
  const h = 136;
  const padL = 30;
  const padR = 10;
  const padV = 14;
  const pts = points.length ? points : [{ n: "—", conf: 0 }];
  const maxI = Math.max(pts.length - 1, 1);
  const seg = (w - padL - padR) / maxI;
  const lineD = pts
    .map((p, i) => {
      const x = padL + i * seg;
      const y = padV + (1 - Math.min(100, Math.max(0, p.conf)) / 100) * (h - 2 * padV);
      return `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg width="100%" height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="xMidYMid meet" style={{ display: "block" }}>
      <line x1={padL} y1={h - padV} x2={w - padR} y2={h - padV} stroke="#2a3f54" strokeWidth={1} />
      <line x1={padL} y1={padV} x2={padL} y2={h - padV} stroke="#2a3f54" strokeWidth={1} />
      {[0, 50, 100].map((t) => (
        <text key={t} x={padL - 8} y={padV + (1 - t / 100) * (h - 2 * padV) + 4} fill="#64748b" fontSize={9} textAnchor="end">
          {t}
        </text>
      ))}
      <path d={lineD} fill="none" stroke="#22d3ee" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />
      {pts.map((p, i) => {
        const x = padL + i * seg;
        const y = padV + (1 - Math.min(100, Math.max(0, p.conf)) / 100) * (h - 2 * padV);
        return (
          <circle key={`${p.n}-${i}`} cx={x} cy={y} r={4} fill="#22d3ee" stroke="#0a1628" strokeWidth={1}>
            <title>{`${p.n}: ${p.conf}%`}</title>
          </circle>
        );
      })}
    </svg>
  );
}

const ZONE_LABELS = [
  ["Fore — Port", "Bow", "Fore — Starboard"],
  ["Midship — Port", "Keel / Bottom", "Midship — Starboard"],
  ["Aft — Port", "Aft — Center", "Aft — Starboard"],
];

const ZONE_SIDEBAR_ORDER = [
  "Midship — Port",
  "Bow",
  "Keel / Bottom",
  "Fore — Starboard",
  "Fore — Port",
  "Midship — Starboard",
  "Aft — Port",
  "Aft — Center",
  "Aft — Starboard",
];

/** Scene anchors — extruded hull (bow −Z). */
const ZONE_3D = {
  "Fore — Port": [-1.12, 0.26, -2.35],
  Bow: [0, 0.34, -3.38],
  "Fore — Starboard": [1.12, 0.26, -2.35],
  "Midship — Port": [-1.2, 0.16, 0.05],
  "Keel / Bottom": [0, -0.2, 0.05],
  "Midship — Starboard": [1.2, 0.16, 0.05],
  "Aft — Port": [-1.02, 0.26, 2.45],
  "Aft — Center": [0, 0.24, 3.08],
  "Aft — Starboard": [1.02, 0.26, 2.45],
};

/** 3D tag text (reference mock shows “Hull” on midship side). */
const ZONE_VIEWER_LABEL = {
  "Midship — Port": "Hull",
};

const TIER_RANK = { HIGH: 3, MEDIUM: 2, LOW: 1, SAFE: 0 };

const TIER_COLORS = {
  HIGH: "#ef4444",
  MEDIUM: "#eab308",
  LOW: "#22d3ee",
  SAFE: "#22c55e",
};

function tierFromSeverity(s) {
  const v = String(s || "").toLowerCase();
  if (v === "critical" || v === "high") return "HIGH";
  if (v === "medium" || v === "moderate") return "MEDIUM";
  return "LOW";
}

function bboxToZone(d, W, H) {
  const x1 = d.bbox?.xmin ?? d.bbox?.x1 ?? d.x1 ?? 0;
  const x2 = d.bbox?.xmax ?? d.bbox?.x2 ?? d.x2 ?? W;
  const y1 = d.bbox?.ymin ?? d.bbox?.y1 ?? d.y1 ?? 0;
  const y2 = d.bbox?.ymax ?? d.bbox?.y2 ?? d.y2 ?? H;
  const cx = ((x1 + x2) / 2) / Math.max(W, 1);
  const cy = ((y1 + y2) / 2) / Math.max(H, 1);

  let row = cy < 0.34 ? 0 : cy < 0.67 ? 1 : 2;
  let col = cx < 0.38 ? 0 : cx < 0.62 ? 1 : 2;

  if (cy > 0.68 && Math.abs(cx - 0.5) < 0.22) {
    row = 1;
    col = 1;
  }

  return ZONE_LABELS[row][col];
}

function classDisplayColor(cls) {
  const c = String(cls || "").toLowerCase();
  if (c.includes("corrosion")) return "#ef4444";
  if (c.includes("crack")) return "#f97316";
  if (c.includes("bio") || c.includes("foul") || c.includes("marine")) return "#eab308";
  if (c.includes("debris")) return "#22c55e";
  return "#22d3ee";
}

function aggregateHullUploads(uploads) {
  const flat = [];
  for (const u of uploads || []) {
    if (!u?.detResult) continue;
    const dets = u.detResult.detections || [];
    const W = u.detResult.img_width || 1280;
    const H = u.detResult.img_height || 720;
    for (const d of dets) flat.push({ ...d, _W: W, _H: H });
  }
  return flat;
}

function sortZoneList(zoneList) {
  const ord = (z) => {
    const i = ZONE_SIDEBAR_ORDER.indexOf(z.label);
    return i === -1 ? 999 : i;
  };
  return [...zoneList].sort((a, b) => {
    const ac = a.count > 0 ? 0 : 1;
    const bc = b.count > 0 ? 0 : 1;
    if (ac !== bc) return ac - bc;
    return ord(a) - ord(b);
  });
}

function viewerLabelForZone(zoneLabel) {
  return ZONE_VIEWER_LABEL[zoneLabel] || zoneLabel;
}

/** Reference dashboard snapshot when no hull scan data yet (matches marketing mock layout). */
function buildReferenceDemoStats() {
  const zones = {};
  for (const z of Object.keys(ZONE_3D)) {
    zones[z] = { label: z, tier: "SAFE", count: 0, classes: [] };
  }
  zones["Midship — Port"] = { label: "Midship — Port", tier: "HIGH", count: 1, classes: ["corrosion"] };
  zones["Bow"] = { label: "Bow", tier: "MEDIUM", count: 1, classes: ["crack"] };
  zones["Keel / Bottom"] = { label: "Keel / Bottom", tier: "LOW", count: 1, classes: ["biofouling"] };
  zones["Fore — Starboard"] = { label: "Fore — Starboard", tier: "SAFE", count: 1, classes: ["debris"] };

  const zoneList = sortZoneList(Object.values(zones));
  const covered = 4;
  const totalZones = zoneList.length;
  const total = 4;
  const avgConf = 0.78;

  const donutData = [
    { name: "corrosion", value: 1, color: "#ef4444" },
    { name: "crack", value: 1, color: "#f97316" },
    { name: "biofouling", value: 1, color: "#eab308" },
    { name: "debris", value: 1, color: "#22c55e" },
  ];
  const barData = sortBarRows([
    { name: "corrosion", avg: 80, fill: "#ef4444" },
    { name: "crack", avg: 70, fill: "#f97316" },
    { name: "biofouling", avg: 65, fill: "#eab308" },
    { name: "debris", avg: 55, fill: "#22c55e" },
  ]);
  const trendData = [
    { n: "#1", conf: 88 },
    { n: "#2", conf: 81 },
    { n: "#3", conf: 76 },
    { n: "#4", conf: 71 },
  ];

  const markers = [
    { label: viewerLabelForZone("Midship — Port"), x: ZONE_3D["Midship — Port"][0], y: ZONE_3D["Midship — Port"][1], z: ZONE_3D["Midship — Port"][2], color: TIER_COLORS.HIGH },
    { label: "Bow", x: ZONE_3D.Bow[0], y: ZONE_3D.Bow[1], z: ZONE_3D.Bow[2], color: TIER_COLORS.MEDIUM },
    { label: viewerLabelForZone("Fore — Starboard"), x: ZONE_3D["Fore — Starboard"][0], y: ZONE_3D["Fore — Starboard"][1], z: ZONE_3D["Fore — Starboard"][2], color: TIER_COLORS.SAFE },
  ];

  return {
    zoneList,
    covered,
    totalZones,
    total,
    avgConf,
    barData,
    donutData,
    trendData,
    markers,
    isDemo: true,
  };
}

function computeStatsFromDetections(flatDets) {
  const zones = {};
  for (const z of Object.keys(ZONE_3D)) {
    zones[z] = { label: z, tier: "SAFE", count: 0, classes: [] };
  }

  for (const d of flatDets) {
    const z = bboxToZone(d, d._W, d._H);
    if (!zones[z]) continue;
    zones[z].count += 1;
    zones[z].classes.push(d.cls ?? d.class ?? "Unknown");
    const tr = tierFromSeverity(d.severity);
    if (TIER_RANK[tr] > TIER_RANK[zones[z].tier]) zones[z].tier = tr;
  }

  const zoneList = sortZoneList(Object.values(zones));
  const covered = zoneList.filter((z) => z.count > 0).length;
  const totalZones = zoneList.length;

  const total = flatDets.length;
  const avgConf = total ? flatDets.reduce((s, d) => s + (Number(d.conf) || 0), 0) / total : 0;

  const byClass = {};
  for (const d of flatDets) {
    const c = d.cls ?? d.class ?? "Unknown";
    if (!byClass[c]) byClass[c] = { sum: 0, n: 0 };
    byClass[c].sum += Number(d.conf) || 0;
    byClass[c].n += 1;
  }
  const barData = sortBarRows(
    Object.entries(byClass).map(([name, v]) => ({
      name,
      avg: Math.round((v.sum / v.n) * 1000) / 10,
      fill: classDisplayColor(name),
    }))
  );

  const donutMap = {};
  for (const d of flatDets) {
    const c = d.cls ?? d.class ?? "Unknown";
    donutMap[c] = (donutMap[c] || 0) + 1;
  }
  const donutData = Object.entries(donutMap).map(([name, value]) => ({
    name,
    value,
    color: classDisplayColor(name),
  }));

  const trendData = flatDets.map((d, i) => ({
    n: `#${i + 1}`,
    conf: Math.round((Number(d.conf) || 0) * 1000) / 10,
  }));

  const markers = zoneList
    .filter((z) => z.count > 0)
    .map((z) => {
      const [x, y, zp] = ZONE_3D[z.label] || [0, 0, 0];
      return {
        label: viewerLabelForZone(z.label),
        x,
        y,
        z: zp,
        color: TIER_COLORS[z.tier] || TIER_COLORS.LOW,
      };
    });

  return {
    zoneList,
    covered,
    totalZones,
    total,
    avgConf,
    barData,
    donutData,
    trendData,
    markers,
    isDemo: false,
  };
}

export default function Hull3DPanel({ uploads, onGoDashboard, onBackToInspection, embedFullPage }) {
  const [hullZoom, setHullZoom] = useState(11);
  const flatDets = useMemo(() => aggregateHullUploads(uploads), [uploads]);

  const stats = useMemo(() => {
    if (!flatDets.length) return buildReferenceDemoStats();
    return computeStatsFromDetections(flatDets);
  }, [flatDets]);

  const donutPlaceholder = [{ name: "—", value: 1, color: "#334155" }];

  const zoomIn = useCallback(() => setHullZoom((z) => Math.max(5.5, z - 1.4)), []);
  const zoomOut = useCallback(() => setHullZoom((z) => Math.min(21, z + 1.4)), []);
  const zoomReset = useCallback(() => setHullZoom(11), []);

  const shellStyle = embedFullPage
    ? {
        marginTop: 0,
        marginBottom: 0,
        borderRadius: 0,
        minHeight: "calc(100vh - 24px)",
        borderLeft: "none",
        borderRight: "none",
      }
    : {
        marginTop: 20,
        marginBottom: 24,
        borderRadius: 12,
      };

  return (
    <div
      style={{
        ...shellStyle,
        border: "1px solid rgba(34,211,238,0.14)",
        background: "linear-gradient(168deg, rgba(10,18,32,0.99) 0%, rgba(5,9,16,1) 55%, rgba(8,14,24,0.98) 100%)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 12,
          padding: "16px 22px",
          borderBottom: "1px solid rgba(255,255,255,0.07)",
          background: "rgba(0,0,0,0.25)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
          <span style={{ fontWeight: 800, letterSpacing: 2, fontSize: 14, color: "#f1f5f9", fontVariant: "small-caps" }}>
            NautiCAI
          </span>
          <span style={{ opacity: 0.35, fontSize: 13 }}>|</span>
          <span style={{ fontSize: 14, fontWeight: 600, color: "#22d3ee", letterSpacing: 0.3 }}>3D Hull Viewer</span>
          {stats.isDemo && (
            <span
              style={{
                fontSize: 10,
                opacity: 0.55,
                padding: "3px 10px",
                borderRadius: 20,
                border: "1px solid rgba(148,163,184,0.25)",
                color: "#94a3b8",
              }}
            >
              Sample layout · run hull scan for live mission data
            </span>
          )}
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "7px 16px",
              borderRadius: 8,
              border: "1.5px solid rgba(52,211,153,0.5)",
              background: "rgba(34,197,94,0.07)",
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: 1,
              color: "#4ade80",
            }}
          >
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: "#22c55e",
                boxShadow: "0 0 10px rgba(34,197,94,0.85)",
              }}
            />
            LIVE ANALYSIS
          </span>
          {onGoDashboard && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={onGoDashboard}>
              + Dashboard
            </button>
          )}
        </div>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", minHeight: 460 }}>
        <aside
          style={{
            width: 268,
            flexShrink: 0,
            borderRight: "1px solid rgba(255,255,255,0.06)",
            padding: "18px 16px",
            display: "flex",
            flexDirection: "column",
            gap: 18,
            background: "rgba(0,0,0,0.15)",
          }}
        >
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div
              className="card"
              style={{
                padding: "16px 12px",
                textAlign: "center",
                background: "rgba(34,211,238,0.06)",
                border: "1px solid rgba(34,211,238,0.12)",
              }}
            >
              <div style={{ fontSize: 26, fontWeight: 800, color: "#22d3ee", lineHeight: 1 }}>{stats.total}</div>
              <div style={{ fontSize: 9, opacity: 0.5, letterSpacing: 1.1, marginTop: 6, fontWeight: 600 }}>
                TOTAL DETECTIONS
              </div>
            </div>
            <div
              className="card"
              style={{
                padding: "16px 12px",
                textAlign: "center",
                background: "rgba(251,146,60,0.06)",
                border: "1px solid rgba(251,146,60,0.15)",
              }}
            >
              <div style={{ fontSize: 26, fontWeight: 800, color: "#fb923c", lineHeight: 1 }}>
                {stats.total ? `${(stats.avgConf * 100).toFixed(0)}%` : "—"}
              </div>
              <div style={{ fontSize: 9, opacity: 0.5, letterSpacing: 1.1, marginTop: 6, fontWeight: 600 }}>
                AVG CONFIDENCE
              </div>
            </div>
          </div>

          <div>
            <div style={{ fontSize: 10, opacity: 0.42, letterSpacing: 1.2, marginBottom: 10, fontWeight: 600 }}>HULL COVERAGE</div>
            <div style={{ height: 9, borderRadius: 5, background: "rgba(255,255,255,0.06)", overflow: "hidden" }}>
              <div
                style={{
                  height: "100%",
                  width: `${stats.totalZones ? (stats.covered / stats.totalZones) * 100 : 0}%`,
                  background: "linear-gradient(90deg, #22d3ee, #34d399)",
                  borderRadius: 5,
                  transition: "width 0.45s ease",
                }}
              />
            </div>
            <div style={{ fontSize: 12, marginTop: 8, opacity: 0.68, fontWeight: 500 }}>
              {stats.covered}/{stats.totalZones} zones
            </div>
          </div>

          <div style={{ flex: 1, minHeight: 0 }}>
            <div style={{ fontSize: 10, opacity: 0.42, letterSpacing: 1.2, marginBottom: 10, fontWeight: 600 }}>DETECTIONS</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 7, maxHeight: 300, overflowY: "auto" }}>
              {stats.zoneList.map((z) => {
                const active = z.count > 0;
                const col = TIER_COLORS[z.tier];
                return (
                  <div
                    key={z.label}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      padding: "9px 11px",
                      borderRadius: 9,
                      border: `1px solid ${active ? "rgba(34,211,238,0.22)" : "rgba(255,255,255,0.05)"}`,
                      background: active ? "rgba(34,211,238,0.07)" : "rgba(255,255,255,0.02)",
                      opacity: active ? 1 : 0.4,
                    }}
                  >
                    <span
                      style={{
                        width: 11,
                        height: 11,
                        borderRadius: "50%",
                        background: col,
                        flexShrink: 0,
                        boxShadow: active ? `0 0 12px ${col}77` : "none",
                      }}
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div
                        style={{
                          fontSize: 12,
                          fontWeight: 600,
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          color: active ? "#e2e8f0" : "#64748b",
                        }}
                      >
                        {z.label}
                      </div>
                      <div style={{ fontSize: 11, opacity: 0.52, marginTop: 2 }}>
                        {active ? (
                          <>
                            <span style={{ color: col, fontWeight: 700 }}>{z.tier}</span>
                            <span style={{ opacity: 0.45 }}> · </span>
                            <span>{z.count}</span>
                          </>
                        ) : (
                          "—"
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {onBackToInspection && (
              <button type="button" className="btn btn-ghost" style={{ width: "100%", fontSize: 12 }} onClick={onBackToInspection}>
                ← Hull inspection
              </button>
            )}
            {onGoDashboard && (
              <button type="button" className="btn btn-ghost" style={{ width: "100%", fontSize: 12 }} onClick={onGoDashboard}>
                ← Back to Dashboard
              </button>
            )}
          </div>
        </aside>

        <div style={{ flex: 1, minWidth: 300, padding: "18px 22px", display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ fontSize: 11, letterSpacing: 1.6, opacity: 0.48, fontWeight: 600 }}>3D HULL MODEL — DETECTION OVERLAY</div>
          <div style={{ position: "relative", flex: 1, minHeight: 420 }}>
            <HullViewer3D markers={stats.markers} height={432} zoom={hullZoom} onZoomChange={setHullZoom} />
            <div style={{ position: "absolute", bottom: 14, left: 14, display: "flex", gap: 8, zIndex: 2 }}>
              <button
                type="button"
                onClick={zoomIn}
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 8,
                  border: "1px solid rgba(255,255,255,0.14)",
                  background: "rgba(0,0,0,0.62)",
                  color: "#cbd5e1",
                  fontSize: 17,
                  cursor: "pointer",
                  lineHeight: 1,
                }}
                title="Zoom in"
              >
                +
              </button>
              <button
                type="button"
                onClick={zoomOut}
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 8,
                  border: "1px solid rgba(255,255,255,0.14)",
                  background: "rgba(0,0,0,0.62)",
                  color: "#cbd5e1",
                  fontSize: 17,
                  cursor: "pointer",
                  lineHeight: 1,
                }}
                title="Zoom out"
              >
                −
              </button>
              <button
                type="button"
                onClick={zoomReset}
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 8,
                  border: "1px solid rgba(255,255,255,0.14)",
                  background: "rgba(0,0,0,0.62)",
                  color: "#cbd5e1",
                  fontSize: 17,
                  cursor: "pointer",
                  lineHeight: 1,
                }}
                title="Reset zoom"
              >
                ↻
              </button>
            </div>
          </div>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, minmax(220px, 1fr))",
          gap: 16,
          padding: "18px 22px 22px",
          borderTop: "1px solid rgba(255,255,255,0.06)",
          background: "linear-gradient(180deg, rgba(0,0,0,0.35) 0%, rgba(5,10,18,0.9) 100%)",
        }}
      >
        <div className="card" style={{ padding: 14, minHeight: 228, background: "rgba(15,23,42,0.45)", border: "1px solid rgba(51,65,85,0.35)" }}>
          <div style={{ fontSize: 10, opacity: 0.42, letterSpacing: 1.2, marginBottom: 10, fontWeight: 600 }}>DETECTION DISTRIBUTION</div>
          <div style={{ minHeight: 162, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <HullDonutChart data={stats.donutData.length ? stats.donutData : donutPlaceholder} size={156} />
          </div>
          <div
            style={{
              fontSize: 10,
              opacity: 0.62,
              display: "flex",
              flexWrap: "wrap",
              gap: "8px 14px",
              justifyContent: "center",
              textTransform: "lowercase",
            }}
          >
            {["Corrosion", "Crack", "Biofouling", "Debris"].map((lab) => (
              <span key={lab} style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
                <span
                  style={{
                    width: 9,
                    height: 9,
                    borderRadius: 2,
                    background:
                      lab === "Corrosion"
                        ? "#ef4444"
                        : lab === "Crack"
                          ? "#f97316"
                          : lab === "Biofouling"
                            ? "#eab308"
                            : "#22c55e",
                  }}
                />
                {lab.toLowerCase()}
              </span>
            ))}
          </div>
        </div>

        <div className="card" style={{ padding: 14, minHeight: 228, background: "rgba(15,23,42,0.45)", border: "1px solid rgba(51,65,85,0.35)" }}>
          <div style={{ fontSize: 10, opacity: 0.42, letterSpacing: 1.2, marginBottom: 10, fontWeight: 600 }}>CONFIDENCE PER CLASS</div>
          <HullHBarChart rows={stats.barData.length ? stats.barData : [{ name: "—", avg: 0, fill: "#334155" }]} />
        </div>

        <div className="card" style={{ padding: 14, minHeight: 228, background: "rgba(15,23,42,0.45)", border: "1px solid rgba(51,65,85,0.35)" }}>
          <div style={{ fontSize: 10, opacity: 0.42, letterSpacing: 1.2, marginBottom: 10, fontWeight: 600 }}>CONFIDENCE TREND</div>
          <HullTrendChart points={stats.trendData.length ? stats.trendData : [{ n: "—", conf: 0 }]} />
        </div>
      </div>
    </div>
  );
}
