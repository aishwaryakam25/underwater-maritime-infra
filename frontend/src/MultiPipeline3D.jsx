import React, { useRef, useEffect } from "react";
import * as THREE from "three";

var SEV_COLOR = { Critical:0xff2200, High:0xff5500, Moderate:0xffaa00, Medium:0xffaa00, Low:0xffdd00, Mild:0xffdd00 };
var PIPE_GAP = 3.5;

export default function MultiPipeline3D({ uploads }) {
  var mountRef = useRef(null);
  var frameRef = useRef(null);

  var scanned = uploads.filter(function(u) { return u.detResult; });
  var totalDets = 0;
  for (var k = 0; k < scanned.length; k++) {
    totalDets += (scanned[k].detResult.detections || []).length;
  }

  useEffect(function() {
    var container = mountRef.current;
    if (!container) return;
    var W = container.clientWidth, H = 580;

    // Renderer — same as original
    var renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setClearColor(0x060d1a);
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    container.appendChild(renderer.domElement);

    // Scene
    var scene = new THREE.Scene();

    // Camera
    var camera = new THREE.PerspectiveCamera(45, W / H, 0.1, 200);
    var pipeCount = Math.max(scanned.length, uploads.length, 1);
    camera.position.set(0, 2, 8 + (pipeCount - 1) * 2.5);
    camera.lookAt(0, 0, 0);

    // Lights — EXACT same as original pipeline-3d-twin.html
    scene.add(new THREE.AmbientLight(0x223344, 2));
    var dir = new THREE.DirectionalLight(0xffffff, 2);
    dir.position.set(5, 8, 5);
    scene.add(dir);
    var pt1 = new THREE.PointLight(0x0088ff, 1.5, 30);
    pt1.position.set(-5, 3, 3);
    scene.add(pt1);
    var pt2 = new THREE.PointLight(0x00ffcc, 0.8, 20);
    pt2.position.set(5, -2, -3);
    scene.add(pt2);

    // Grid — EXACT same
    var grid = new THREE.GridHelper(20, 20, 0x0d1a2a, 0x0d1a2a);
    grid.position.y = -2;
    scene.add(grid);

    // Particles — EXACT same
    var pGeo = new THREE.BufferGeometry();
    var pPos = [];
    for (var i = 0; i < 300; i++) {
      pPos.push((Math.random() - 0.5) * 20, (Math.random() - 0.5) * 10, (Math.random() - 0.5) * 10);
    }
    pGeo.setAttribute("position", new THREE.Float32BufferAttribute(pPos, 3));
    scene.add(new THREE.Points(pGeo, new THREE.PointsMaterial({ color: 0x1a3a5c, size: 0.04 })));

    // Master group for all pipelines
    var masterGroup = new THREE.Group();
    scene.add(masterGroup);

    // Pulse meshes for animation
    var pulseMeshes = [];

    // Build one pipeline — EXACT same geometry as original
    function buildOnePipeline(zOffset, detResult, index) {
      var dets = [];
      var grade = "-";
      var risk = 0;
      var total = 0;
      var hasDet = !!detResult;

      if (hasDet) {
        dets = detResult.detections || [];
        grade = detResult.grade || "-";
        risk = detResult.risk_score || 0;
        total = detResult.total || dets.length;
      }

      // MAIN PIPE — exact same as original: CylinderGeometry(0.55, 0.55, 8, 64, 1, true)
      var pipe = new THREE.Mesh(
        new THREE.CylinderGeometry(0.55, 0.55, 8, 64, 1, true),
        new THREE.MeshStandardMaterial({
          color: 0x1a3a5c, metalness: 0.85, roughness: 0.25,
          side: THREE.DoubleSide, transparent: true, opacity: 0.82
        })
      );
      pipe.rotation.z = Math.PI / 2;
      pipe.position.z = zOffset;
      masterGroup.add(pipe);

      // END CAPS — exact same
      [-4, 4].forEach(function(x) {
        var cap = new THREE.Mesh(
          new THREE.CircleGeometry(0.55, 32),
          new THREE.MeshStandardMaterial({ color: 0x1a3a5c, metalness: 0.85 })
        );
        cap.position.set(x, 0, zOffset);
        cap.rotation.y = x > 0 ? 0 : Math.PI;
        masterGroup.add(cap);
      });

      // JOINT RINGS — exact same positions [-3, -1.5, 0, 1.5, 3]
      [-3, -1.5, 0, 1.5, 3].forEach(function(x) {
        var ring = new THREE.Mesh(
          new THREE.TorusGeometry(0.58, 0.055, 8, 32),
          new THREE.MeshStandardMaterial({ color: 0x2255aa, metalness: 0.9, roughness: 0.2 })
        );
        ring.position.set(x, 0, zOffset);
        ring.rotation.y = Math.PI / 2;
        masterGroup.add(ring);
      });

      // WIREFRAME OVERLAYS — exact same
      for (var wi = 0; wi < 3; wi++) {
        var wf = new THREE.Mesh(
          new THREE.CylinderGeometry(0.553, 0.553, 8, 32, 1, true),
          new THREE.MeshBasicMaterial({ color: 0x1144aa, wireframe: true, transparent: true, opacity: 0.05 })
        );
        wf.rotation.z = Math.PI / 2;
        wf.position.z = zOffset;
        masterGroup.add(wf);
      }

      // LABEL
      var lc = document.createElement("canvas");
      lc.width = 512;
      lc.height = 64;
      var ctx = lc.getContext("2d");
      ctx.fillStyle = "rgba(6,13,26,0.85)";
      ctx.fillRect(0, 0, 512, 64);
      ctx.strokeStyle = "rgba(0,204,255,0.3)";
      ctx.lineWidth = 1;
      ctx.strokeRect(1, 1, 510, 62);
      ctx.fillStyle = "#00ccff";
      ctx.font = "bold 20px Segoe UI, monospace";
      ctx.fillText("Pipeline " + (index + 1), 12, 26);
      ctx.fillStyle = "#4488aa";
      ctx.font = "14px Segoe UI, monospace";
      if (hasDet) {
        ctx.fillText("Grade: " + grade + "   Risk: " + risk + "%   Defects: " + total, 12, 52);
      } else {
        ctx.fillText("Awaiting scan...", 12, 52);
      }
      var tex = new THREE.CanvasTexture(lc);
      tex.minFilter = THREE.LinearFilter;
      var sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true }));
      sp.scale.set(4, 0.5, 1);
      sp.position.set(0, 1.3, zOffset);
      masterGroup.add(sp);

      // DEFECT MARKERS — exact same style as original
      for (var di = 0; di < dets.length; di++) {
        var d = dets[di];
        var severity = d.severity || "Low";
        var color = SEV_COLOR[severity] || 0x00ccff;
        var size = (severity === "Critical" || severity === "High") ? 0.13 :
                   (severity === "Medium" || severity === "Moderate") ? 0.10 : 0.08;
        var r = 0.62;

        // Position along pipe
        var pipePos = dets.length === 1 ? 50 : Math.round(5 + (di / Math.max(dets.length - 1, 1)) * 90);
        var angle = (di / Math.max(dets.length, 1)) * Math.PI * 2;
        var mx = (pipePos / 100) * 8 - 4;
        var my = Math.sin(angle) * r;
        var mz = zOffset + Math.cos(angle) * r;

        // Sphere — exact same material
        var sphere = new THREE.Mesh(
          new THREE.SphereGeometry(size, 16, 16),
          new THREE.MeshStandardMaterial({ color: color, emissive: color, emissiveIntensity: 0.7 })
        );
        sphere.position.set(mx, my, mz);
        masterGroup.add(sphere);

        // Pulse ring — exact same as original
        var pulse = new THREE.Mesh(
          new THREE.RingGeometry(size + 0.02, size + 0.06, 16),
          new THREE.MeshBasicMaterial({ color: color, side: THREE.DoubleSide, transparent: true, opacity: 0.5 })
        );
        pulse.position.set(mx, my, mz);
        pulse.lookAt(mx * 3, my * 3, mz * 3);
        pulse.userData = { isPulse: true };
        masterGroup.add(pulse);
        pulseMeshes.push(pulse);
      }
    }

    // Build all pipelines
    var sourceList = scanned.length > 0 ? scanned : uploads;
    var totalW = (sourceList.length - 1) * PIPE_GAP;
    var startZ = -totalW / 2;
    for (var p = 0; p < sourceList.length; p++) {
      buildOnePipeline(startZ + p * PIPE_GAP, sourceList[p].detResult, p);
    }

    // Mouse controls — exact same as original
    var isDragging = false, px = 0, py = 0, autoRotate = true;
    var el = renderer.domElement;

    el.addEventListener("mousedown", function(e) { isDragging = true; px = e.clientX; py = e.clientY; });
    window.addEventListener("mouseup", function() { isDragging = false; });
    window.addEventListener("mousemove", function(e) {
      if (!isDragging) return;
      masterGroup.rotation.y += (e.clientX - px) * 0.006;
      masterGroup.rotation.x += (e.clientY - py) * 0.004;
      px = e.clientX; py = e.clientY;
    });
    el.addEventListener("wheel", function(e) {
      camera.position.z = Math.max(3, Math.min(30, camera.position.z + e.deltaY * 0.01));
    });
    el.addEventListener("touchstart", function(e) { isDragging = true; px = e.touches[0].clientX; py = e.touches[0].clientY; });
    el.addEventListener("touchend", function() { isDragging = false; });
    el.addEventListener("touchmove", function(e) {
      if (!isDragging) return;
      masterGroup.rotation.y += (e.touches[0].clientX - px) * 0.006;
      masterGroup.rotation.x += (e.touches[0].clientY - py) * 0.004;
      px = e.touches[0].clientX; py = e.touches[0].clientY;
    });

    // Animation — exact same pulse effect as original
    var t = 0;
    function animate() {
      frameRef.current = requestAnimationFrame(animate);
      t += 0.016;
      if (autoRotate && !isDragging) masterGroup.rotation.y += 0.004;
      for (var mi = 0; mi < pulseMeshes.length; mi++) {
        var m = pulseMeshes[mi];
        if (m.userData.isPulse) {
          var s = 1 + Math.sin(t * 3) * 0.3;
          m.scale.setScalar(s);
          m.material.opacity = 0.3 + Math.sin(t * 3) * 0.2;
        }
      }
      renderer.render(scene, camera);
    }
    animate();

    // Resize
    function onResize() {
      var nw = container.clientWidth;
      camera.aspect = nw / H;
      camera.updateProjectionMatrix();
      renderer.setSize(nw, H);
    }
    window.addEventListener("resize", onResize);

    return function() {
      cancelAnimationFrame(frameRef.current);
      window.removeEventListener("resize", onResize);
      renderer.dispose();
      if (container.contains(el)) container.removeChild(el);
    };
  }, [uploads.length, scanned.length]);

  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ padding: "6px 14px", borderRadius: 6, background: "rgba(0,204,68,0.12)", border: "1.5px solid rgba(0,204,68,0.5)", fontSize: 12, color: "#0c6", fontWeight: 700, letterSpacing: 1 }}>LIVE — NautiCAI Pipeline Scan</div>
          <div style={{ fontSize: 12, opacity: 0.5 }}>{scanned.length} pipeline{scanned.length !== 1 ? "s" : ""} · {totalDets} defect{totalDets !== 1 ? "s" : ""}</div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {[["Critical / Severe", "#ff2200"], ["Moderate", "#ffaa00"], ["Mild / Low", "#ffdd00"], ["Clean", "#00cc44"]].map(function(pair) {
            return <div key={pair[0]} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 10, opacity: 0.6 }}><span style={{ width: 8, height: 8, borderRadius: "50%", background: pair[1] }} />{pair[0]}</div>;
          })}
        </div>
      </div>
      <div ref={mountRef} style={{ width: "100%", height: 580, borderRadius: 8, overflow: "hidden", border: "1px solid #0d2a4a", position: "relative", cursor: "grab", background: "#060d1a" }}>
        <div style={{ position: "absolute", bottom: 12, left: "50%", transform: "translateX(-50%)", zIndex: 10, color: "#334455", fontSize: 11, pointerEvents: "none" }}>🖱️ Drag to rotate • Scroll to zoom</div>
      </div>
      {scanned.length > 0 && (
        <div style={{ display: "flex", gap: 10, marginTop: 12, flexWrap: "wrap" }}>
          {scanned.map(function(u, i) {
            var dc = (u.detResult.detections || []).length;
            var gv = u.detResult.grade || "-";
            var rv = u.detResult.risk_score || 0;
            return (
              <div key={u.id} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 14px", borderRadius: 8, background: "#0a1520", border: "1px solid #0d2a4a", fontSize: 11 }}>
                <span style={{ fontWeight: 700, color: "#00ccff" }}>P{i + 1}</span>
                <span style={{ opacity: 0.5, maxWidth: 100, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{u.file.name}</span>
                <span style={{ color: "#00cc44", fontWeight: 700 }}>{gv}</span>
                <span style={{ color: "#ffaa00" }}>{rv}%</span>
                <span style={{ color: "#00ccff" }}>{dc} def</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}