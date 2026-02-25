/**
 * OceanCanvas — Full-screen WebGL-quality underwater live wallpaper
 * 60fps canvas rendering: caustic light, depth particles, bubbles,
 * sonar rings, plankton, volumetric light rays, jellyfish
 */
import React, { useRef, useEffect } from "react";

/* ───────── tunables ───────── */
const PARTICLE_COUNT   = 120;   // floating dust / micro-organisms
const BUBBLE_COUNT     = 18;    // rising bubbles
const RAY_COUNT        = 7;     // volumetric light beams
const PLANKTON_COUNT   = 25;    // glowing plankton
const JELLYFISH_COUNT  = 3;     // jellyfish silhouettes
const CAUSTIC_CELLS    = 6;     // caustic light patches
const SONAR_INTERVAL   = 4000;  // ms between sonar pings

/* Colour palette — NautiCAI brand */
const DEEP_TOP    = [2, 8, 18];
const DEEP_BOT    = [4, 16, 36];
const CYAN        = [0, 229, 255];
const TEAL        = [0, 200, 180];
const VIOLET      = [124, 106, 255];
const WARM        = [0, 180, 220];

function lerp(a, b, t) { return a + (b - a) * t; }
function rand(lo, hi) { return Math.random() * (hi - lo) + lo; }

/* ───────── entity factories ───────── */
function mkParticle(w, h) {
  const depth = Math.random();                     // 0 = far, 1 = near
  return {
    x: Math.random() * w,
    y: Math.random() * h,
    r: lerp(0.4, 2.2, depth),
    depth,
    speed: lerp(0.08, 0.35, depth),
    drift: rand(-0.15, 0.15),
    alpha: lerp(0.12, 0.45, depth),
    phase: Math.random() * Math.PI * 2,
  };
}

function mkBubble(w, h, fromBottom = true) {
  const sz = rand(2, 7);
  return {
    x: rand(0, w),
    y: fromBottom ? h + rand(10, 200) : rand(0, h),
    r: sz,
    speed: rand(0.4, 1.1),
    wobbleAmp: rand(10, 35),
    wobbleFreq: rand(0.005, 0.015),
    phase: Math.random() * Math.PI * 2,
    alpha: rand(0.15, 0.45),
    shine: rand(0.3, 0.7),
  };
}

function mkRay(w) {
  return {
    x: rand(0, w),
    width: rand(30, 120),
    alpha: rand(0.015, 0.06),
    speed: rand(0.1, 0.3),
    phase: Math.random() * Math.PI * 2,
    length: rand(0.35, 0.75),            // fraction of canvas height
    hue: rand(180, 210),                  // cyan-ish
  };
}

function mkPlankton(w, h) {
  return {
    x: rand(0, w),
    y: rand(0, h),
    r: rand(1.2, 3),
    vx: rand(-0.2, 0.2),
    vy: rand(-0.15, 0.15),
    glow: rand(0.3, 0.9),
    pulse: rand(0.002, 0.008),
    phase: Math.random() * Math.PI * 2,
    color: Math.random() > 0.5 ? TEAL : CYAN,
  };
}

function mkJellyfish(w, h) {
  return {
    x: rand(w * 0.15, w * 0.85),
    y: rand(h * 0.25, h * 0.75),
    size: rand(18, 42),
    drift: rand(-0.08, 0.08),
    bob: rand(0.15, 0.35),
    phase: Math.random() * Math.PI * 2,
    alpha: rand(0.04, 0.12),
    color: Math.random() > 0.5 ? VIOLET : CYAN,
    tentacles: Math.floor(rand(4, 8)),
  };
}

function mkCaustic(w) {
  return {
    x: rand(0, w),
    size: rand(60, 200),
    alpha: rand(0.015, 0.045),
    speed: rand(0.2, 0.5),
    phase: Math.random() * Math.PI * 2,
  };
}

/* ───────── sonar ring ───────── */
function mkSonar(w, h) {
  return { x: w * 0.5, y: h * 0.8, age: 0, maxAge: 180, maxR: Math.min(w, h) * 0.6 };
}

/* ═══════════════════════════════════════════════
   React component
   ═══════════════════════════════════════════════ */
export default function OceanCanvas() {
  const cvs = useRef(null);
  const raf = useRef(null);

  useEffect(() => {
    const canvas = cvs.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    let W, H;
    const resize = () => {
      W = canvas.width  = window.innerWidth;
      H = canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    /* ── initialise entities ── */
    let particles  = Array.from({ length: PARTICLE_COUNT }, () => mkParticle(W, H));
    let bubbles    = Array.from({ length: BUBBLE_COUNT }, () => mkBubble(W, H, false));
    let rays       = Array.from({ length: RAY_COUNT }, () => mkRay(W));
    let planktons  = Array.from({ length: PLANKTON_COUNT }, () => mkPlankton(W, H));
    let jellies    = Array.from({ length: JELLYFISH_COUNT }, () => mkJellyfish(W, H));
    let caustics   = Array.from({ length: CAUSTIC_CELLS }, () => mkCaustic(W));
    let sonars     = [];
    let frame      = 0;

    /* Sonar timer */
    const sonarTimer = setInterval(() => {
      sonars.push(mkSonar(W, H));
      if (sonars.length > 4) sonars.shift();
    }, SONAR_INTERVAL);

    /* ── gradient cache ── */
    let bgGrad = null;
    function buildBG() {
      bgGrad = ctx.createLinearGradient(0, 0, 0, H);
      bgGrad.addColorStop(0,    `rgb(${DEEP_TOP.join(",")})`);
      bgGrad.addColorStop(0.35, `rgb(3,12,26)`);
      bgGrad.addColorStop(0.7,  `rgb(${DEEP_BOT.join(",")})`);
      bgGrad.addColorStop(1,    `rgb(6,20,42)`);
    }
    buildBG();

    /* ── draw helpers ── */
    function rgba(c, a) { return `rgba(${c[0]},${c[1]},${c[2]},${a})`; }

    function drawBG() {
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, W, H);

      /* subtle vignette */
      const vig = ctx.createRadialGradient(W / 2, H / 2, W * 0.25, W / 2, H / 2, W * 0.85);
      vig.addColorStop(0, "transparent");
      vig.addColorStop(1, "rgba(0,0,0,0.35)");
      ctx.fillStyle = vig;
      ctx.fillRect(0, 0, W, H);
    }

    function drawCaustics(t) {
      caustics.forEach(c => {
        c.phase += c.speed * 0.005;
        const cx = c.x + Math.sin(c.phase) * 40;
        const cy = Math.sin(c.phase * 0.7) * 30 + 80;
        const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, c.size);
        g.addColorStop(0, rgba(CYAN, c.alpha * (0.7 + 0.3 * Math.sin(t * 0.001 + c.phase))));
        g.addColorStop(0.5, rgba(TEAL, c.alpha * 0.3));
        g.addColorStop(1, "transparent");
        ctx.fillStyle = g;
        ctx.fillRect(cx - c.size, cy - c.size, c.size * 2, c.size * 2);
      });
    }

    function drawRays(t) {
      rays.forEach(r => {
        r.phase += r.speed * 0.003;
        const sway = Math.sin(r.phase) * 30;
        const alpha = r.alpha * (0.6 + 0.4 * Math.sin(t * 0.0008 + r.phase));
        const x = r.x + sway;
        const len = H * r.length;

        ctx.save();
        ctx.globalAlpha = alpha;
        ctx.globalCompositeOperation = "screen";

        const g = ctx.createLinearGradient(x, 0, x + r.width * 0.4, len);
        g.addColorStop(0, rgba(CYAN, 0.5));
        g.addColorStop(0.3, rgba(WARM, 0.2));
        g.addColorStop(1, "transparent");

        ctx.beginPath();
        ctx.moveTo(x - r.width * 0.5, 0);
        ctx.lineTo(x + r.width * 0.5, 0);
        ctx.lineTo(x + r.width * 0.15 + sway * 0.3, len);
        ctx.lineTo(x - r.width * 0.15 + sway * 0.3, len);
        ctx.closePath();
        ctx.fillStyle = g;
        ctx.fill();
        ctx.restore();
      });
    }

    function drawParticles(t) {
      particles.forEach(p => {
        p.phase += 0.01;
        p.x += p.drift + Math.sin(p.phase) * 0.1;
        p.y -= p.speed;

        /* wrap */
        if (p.y < -10) { p.y = H + 10; p.x = rand(0, W); }
        if (p.x < -10) p.x = W + 10;
        if (p.x > W + 10) p.x = -10;

        const flicker = 0.7 + 0.3 * Math.sin(t * 0.002 + p.phase);
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = rgba(CYAN, p.alpha * flicker);
        ctx.fill();
      });
    }

    function drawBubbles(t) {
      bubbles.forEach(b => {
        b.phase += b.wobbleFreq;
        b.y -= b.speed;
        const wobX = Math.sin(b.phase) * b.wobbleAmp;

        /* respawn from bottom */
        if (b.y < -20) {
          Object.assign(b, mkBubble(W, H, true));
        }

        const bx = b.x + wobX;

        /* outer ring */
        ctx.beginPath();
        ctx.arc(bx, b.y, b.r, 0, Math.PI * 2);
        ctx.strokeStyle = rgba(CYAN, b.alpha * 0.6);
        ctx.lineWidth = 0.8;
        ctx.stroke();

        /* inner glow */
        const ig = ctx.createRadialGradient(bx - b.r * 0.3, b.y - b.r * 0.3, 0, bx, b.y, b.r);
        ig.addColorStop(0, rgba([255, 255, 255], b.shine * 0.5));
        ig.addColorStop(0.4, rgba(CYAN, b.alpha * 0.3));
        ig.addColorStop(1, "transparent");
        ctx.fillStyle = ig;
        ctx.fill();
      });
    }

    function drawPlankton(t) {
      planktons.forEach(p => {
        p.phase += p.pulse;
        p.x += p.vx + Math.sin(p.phase) * 0.1;
        p.y += p.vy + Math.cos(p.phase * 0.7) * 0.08;

        /* wrap */
        if (p.x < -10) p.x = W + 10;
        if (p.x > W + 10) p.x = -10;
        if (p.y < -10) p.y = H + 10;
        if (p.y > H + 10) p.y = -10;

        const pulse = 0.5 + 0.5 * Math.sin(t * 0.003 + p.phase);
        const glow = p.glow * pulse;

        ctx.save();
        ctx.globalCompositeOperation = "screen";

        /* outer glow */
        const g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 5);
        g.addColorStop(0, rgba(p.color, glow * 0.5));
        g.addColorStop(1, "transparent");
        ctx.fillStyle = g;
        ctx.fillRect(p.x - p.r * 5, p.y - p.r * 5, p.r * 10, p.r * 10);

        /* core */
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r * (0.8 + pulse * 0.3), 0, Math.PI * 2);
        ctx.fillStyle = rgba(p.color, glow * 0.9);
        ctx.fill();

        ctx.restore();
      });
    }

    function drawJellyfish(t) {
      jellies.forEach(j => {
        j.phase += 0.008;
        j.x += j.drift;
        j.y += Math.sin(j.phase) * j.bob;

        if (j.x < -60) j.x = W + 60;
        if (j.x > W + 60) j.x = -60;
        if (j.y < 50) j.y = 50;
        if (j.y > H - 50) j.y = H - 50;

        const pulse = 0.9 + 0.1 * Math.sin(t * 0.003 + j.phase);
        const s = j.size * pulse;

        ctx.save();
        ctx.globalAlpha = j.alpha;
        ctx.globalCompositeOperation = "screen";

        /* bell — dome shape */
        const g = ctx.createRadialGradient(j.x, j.y - s * 0.1, 0, j.x, j.y, s);
        g.addColorStop(0, rgba(j.color, 0.6));
        g.addColorStop(0.5, rgba(j.color, 0.2));
        g.addColorStop(1, "transparent");
        ctx.fillStyle = g;

        ctx.beginPath();
        ctx.ellipse(j.x, j.y, s * 0.8, s * 0.5, 0, Math.PI, 0);
        ctx.fill();

        /* tentacles */
        ctx.strokeStyle = rgba(j.color, 0.25);
        ctx.lineWidth = 0.8;
        for (let i = 0; i < j.tentacles; i++) {
          const tx = j.x - s * 0.6 + (s * 1.2 / (j.tentacles - 1)) * i;
          ctx.beginPath();
          ctx.moveTo(tx, j.y);
          const wave = Math.sin(t * 0.002 + i + j.phase) * 8;
          ctx.quadraticCurveTo(tx + wave, j.y + s * 0.6, tx + wave * 0.5, j.y + s * 1.2);
          ctx.stroke();
        }

        ctx.restore();
      });
    }

    function drawSonars(t) {
      sonars.forEach(s => {
        s.age++;
        const progress = s.age / s.maxAge;
        const r = progress * s.maxR;
        const alpha = (1 - progress) * 0.2;

        if (alpha <= 0.001) return;

        ctx.save();
        ctx.globalCompositeOperation = "screen";

        /* ring */
        ctx.beginPath();
        ctx.arc(s.x, s.y, r, 0, Math.PI * 2);
        ctx.strokeStyle = rgba(CYAN, alpha);
        ctx.lineWidth = 1.5 * (1 - progress);
        ctx.stroke();

        /* inner fill */
        const sg = ctx.createRadialGradient(s.x, s.y, r * 0.85, s.x, s.y, r);
        sg.addColorStop(0, "transparent");
        sg.addColorStop(1, rgba(CYAN, alpha * 0.3));
        ctx.fillStyle = sg;
        ctx.fill();

        ctx.restore();
      });
      /* cleanup dead */
      sonars = sonars.filter(s => s.age < s.maxAge);
    }

    /* ── Water surface caustic mesh at top ── */
    function drawSurfaceCaustics(t) {
      ctx.save();
      ctx.globalCompositeOperation = "screen";
      const y0 = 0;
      const yMax = H * 0.12;
      const g = ctx.createLinearGradient(0, y0, 0, yMax);
      g.addColorStop(0, rgba(CYAN, 0.04 + 0.02 * Math.sin(t * 0.0005)));
      g.addColorStop(0.5, rgba(TEAL, 0.02));
      g.addColorStop(1, "transparent");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, W, yMax);

      /* moving caustic pattern — simple sine mesh */
      ctx.strokeStyle = rgba(CYAN, 0.025);
      ctx.lineWidth = 1;
      for (let i = 0; i < 8; i++) {
        ctx.beginPath();
        for (let x = 0; x < W; x += 4) {
          const y = 20 + i * 12 + Math.sin(x * 0.008 + t * 0.001 + i * 1.2) * 8;
          x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.stroke();
      }
      ctx.restore();
    }

    /* ── depth fog layer at bottom ── */
    function drawDepthFog() {
      const fogH = H * 0.25;
      const g = ctx.createLinearGradient(0, H - fogH, 0, H);
      g.addColorStop(0, "transparent");
      g.addColorStop(0.5, "rgba(4,16,36,0.3)");
      g.addColorStop(1, "rgba(2,8,18,0.7)");
      ctx.fillStyle = g;
      ctx.fillRect(0, H - fogH, W, fogH);
    }

    /* ── main loop ── */
    function tick() {
      frame++;
      const t = performance.now();

      drawBG();
      drawSurfaceCaustics(t);
      drawCaustics(t);
      drawRays(t);
      drawParticles(t);
      drawJellyfish(t);
      drawPlankton(t);
      drawBubbles(t);
      drawSonars(t);
      drawDepthFog();

      raf.current = requestAnimationFrame(tick);
    }

    raf.current = requestAnimationFrame(tick);

    /* ── handle resize: rebuild entities ── */
    const onResize = () => {
      resize();
      buildBG();
      particles = Array.from({ length: PARTICLE_COUNT }, () => mkParticle(W, H));
      rays = Array.from({ length: RAY_COUNT }, () => mkRay(W));
    };
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(raf.current);
      clearInterval(sonarTimer);
      window.removeEventListener("resize", resize);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  return (
    <canvas
      ref={cvs}
      className="ocean-canvas"
      aria-hidden="true"
    />
  );
}
