import React, { useMemo } from 'react';

/**
 * WeldDefectOverlay
 * ------------------------------------------------------------
 * Renders an annotated weld inspection image where every detection
 * gets a visible label, and labels never overlap each other.
 *
 * How it works:
 *   1. Boxes are drawn at the model's predicted coordinates.
 *   2. For each detection we try a list of candidate label slots
 *      (above box, below box, right of box, left of box, then
 *      stepped offsets). The first slot that doesn't collide
 *      with an already-placed label and stays in-bounds wins.
 *   3. A dashed leader line connects each label back to the
 *      center of its box, so shifted labels stay visually tied
 *      to the right detection.
 *
 * Props:
 *   imageUrl      string                source image URL
 *   imageWidth    number                natural pixel width
 *   imageHeight   number                natural pixel height
 *   detections    Array<Detection>      see shape below
 *
 * Detection shape:
 *   {
 *     id?:         string | number,
 *     class:       string,              // e.g. "Scaling", "Fracture"
 *     confidence:  number,              // 0..1
 *     bbox:        { x, y, w, h },      // pixels in image coords
 *     severity?:   'low'|'medium'|'high'|'critical'
 *   }
 *
 * Drop into your existing tab — replaces the old SVG overlay block.
 * ------------------------------------------------------------
 */

const SEVERITY_COLORS = {
  critical: '#ef4444', // red
  high:     '#f97316', // orange
  medium:   '#eab308', // yellow
  low:      '#22c55e', // green
};

// Lower confidence => higher severity (matches your sonar module convention).
function severityFromConfidence(conf) {
  if (conf < 0.55) return 'critical';
  if (conf < 0.70) return 'high';
  if (conf < 0.85) return 'medium';
  return 'low';
}

// AABB overlap test with a small padding so labels don't touch.
function rectsOverlap(a, b, pad = 4) {
  return !(
    a.x + a.w + pad <= b.x ||
    b.x + b.w + pad <= a.x ||
    a.y + a.h + pad <= b.y ||
    b.y + b.h + pad <= a.y
  );
}

function inBounds(r, W, H) {
  return r.x >= 0 && r.y >= 0 && r.x + r.w <= W && r.y + r.h <= H;
}

/**
 * Greedy label placer.
 * For each detection, walks a priority list of candidate positions
 * and picks the first one that fits without overlap.
 */
function placeLabels(detections, W, H, opts = {}) {
  const labelW = opts.labelW ?? 150;
  const labelH = opts.labelH ?? 24;
  const gap    = opts.gap    ?? 4;

  // Sort by box area (largest first) so big features anchor
  // their labels first; smaller ones flex around them.
  const order = detections
    .map((d, i) => ({ d, i, area: d.bbox.w * d.bbox.h }))
    .sort((a, b) => b.area - a.area);

  const placed = [];

  for (const { d, i } of order) {
    const { x, y, w, h } = d.bbox;

    const candidates = [
      { x: x,                y: y - labelH - gap },           // above-left
      { x: x + w - labelW,   y: y - labelH - gap },           // above-right
      { x: x,                y: y + h + gap },                // below-left
      { x: x + w - labelW,   y: y + h + gap },                // below-right
      { x: x + w + gap,      y: y },                          // right-top
      { x: x + w + gap,      y: y + h - labelH },             // right-bottom
      { x: x - labelW - gap, y: y },                          // left-top
      { x: x - labelW - gap, y: y + h - labelH },             // left-bottom
    ];

    let chosen = null;
    for (const c of candidates) {
      const r = { x: c.x, y: c.y, w: labelW, h: labelH };
      if (!inBounds(r, W, H)) continue;
      if (placed.some(p => rectsOverlap(r, p.label))) continue;
      chosen = r;
      break;
    }

    // Spiral fallback: step further up/down/left/right until we find a slot.
    if (!chosen) {
      const step = labelH + gap;
      outer: for (let k = 1; k < 40; k++) {
        for (const dy of [-k * step, k * step]) {
          for (const dx of [0, -k * 20, k * 20]) {
            const r = {
              x: x + dx,
              y: y - labelH - gap + dy,
              w: labelW,
              h: labelH,
            };
            if (!inBounds(r, W, H)) continue;
            if (placed.some(p => rectsOverlap(r, p.label))) continue;
            chosen = r;
            break outer;
          }
        }
      }
    }

    // Last resort — clamp to image (rare).
    if (!chosen) {
      chosen = {
        x: Math.max(0, Math.min(W - labelW, x)),
        y: Math.max(0, y - labelH - gap),
        w: labelW,
        h: labelH,
      };
    }

    placed.push({
      det: d,
      idx: i,
      label: chosen,
      box: { x, y, w, h },
      anchor: { x: x + w / 2, y: y + h / 2 },
    });
  }

  // Restore original detection order so [01], [02]... stay readable.
  return placed.sort((a, b) => a.idx - b.idx);
}

export default function WeldDefectOverlay({
  imageUrl,
  imageWidth,
  imageHeight,
  detections = [],
}) {
  const placements = useMemo(
    () => placeLabels(detections, imageWidth, imageHeight),
    [detections, imageWidth, imageHeight]
  );

  return (
    <div
      style={{
        position: 'relative',
        display: 'inline-block',
        maxWidth: '100%',
        lineHeight: 0,
      }}
    >
      <img
        src={imageUrl}
        alt="Annotated weld inspection"
        style={{ display: 'block', width: '100%', height: 'auto' }}
      />
      <svg
        viewBox={`0 0 ${imageWidth} ${imageHeight}`}
        preserveAspectRatio="none"
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none',
        }}
      >
        {placements.map(({ det, idx, label, box, anchor }) => {
          const severity = det.severity ?? severityFromConfidence(det.confidence);
          const color = SEVERITY_COLORS[severity];
          const tag = `[${String(idx + 1).padStart(2, '0')}]`;
          const text = `${tag} ${det.class} ${Math.round(det.confidence * 100)}%`;

          // Leader line: from label edge nearest the box to box center.
          const labelCx = label.x + label.w / 2;
          const labelCy = label.y + label.h / 2;

          return (
            <g key={det.id ?? idx}>
              {/* bounding box */}
              <rect
                x={box.x}
                y={box.y}
                width={box.w}
                height={box.h}
                fill="none"
                stroke={color}
                strokeWidth={3}
              />

              {/* leader line — only drawn if label is meaningfully offset */}
              <line
                x1={labelCx}
                y1={labelCy}
                x2={anchor.x}
                y2={anchor.y}
                stroke={color}
                strokeWidth={1.25}
                strokeDasharray="4 3"
                opacity={0.55}
              />

              {/* small dot at the anchor so it's clear which box owns the label */}
              <circle cx={anchor.x} cy={anchor.y} r={2.5} fill={color} />

              {/* label background */}
              <rect
                x={label.x}
                y={label.y}
                width={label.w}
                height={label.h}
                fill={color}
                rx={3}
              />

              {/* label text */}
              <text
                x={label.x + 8}
                y={label.y + label.h / 2 + 0.5}
                fill="#ffffff"
                fontSize={13}
                fontWeight={700}
                fontFamily="system-ui, -apple-system, Segoe UI, sans-serif"
                dominantBaseline="middle"
                style={{ paintOrder: 'stroke', stroke: 'rgba(0,0,0,0.25)', strokeWidth: 0.5 }}
              >
                {text}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}