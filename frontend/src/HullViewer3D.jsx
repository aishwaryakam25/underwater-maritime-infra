import React, { useRef, useEffect } from "react";
import * as THREE from "three";

/**
 * Cruise ship schematic: long hull, white stacked superstructure, twin funnels.
 * Bow faces −Z (matches Hull3DPanel zone markers).
 */
export default function HullViewer3D({ markers, height = 520, zoom = 11, onZoomChange }) {
  const mountRef = useRef(null);
  const frameRef = useRef(null);
  const zoomRef = useRef(zoom);
  const zoomCbRef = useRef(onZoomChange);
  useEffect(() => {
    zoomCbRef.current = onZoomChange;
  }, [onZoomChange]);

  useEffect(() => {
    zoomRef.current = zoom;
  }, [zoom]);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    let W = container.clientWidth || 640;
    let H = height;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setClearColor(0x0c1520);
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog(0x0c1520, 22, 48);

    const camera = new THREE.PerspectiveCamera(38, W / H, 0.1, 120);
    camera.position.set(0.45, 2.4, zoomRef.current);
    camera.lookAt(0, 0.85, 0);

    const hemi = new THREE.HemisphereLight(0xa8c4e8, 0x1a2535, 0.9);
    scene.add(hemi);
    const dir = new THREE.DirectionalLight(0xffffff, 1.05);
    dir.position.set(10, 18, 12);
    dir.castShadow = true;
    dir.shadow.mapSize.width = 2048;
    dir.shadow.mapSize.height = 2048;
    dir.shadow.camera.near = 0.5;
    dir.shadow.camera.far = 55;
    dir.shadow.camera.left = -14;
    dir.shadow.camera.right = 14;
    dir.shadow.camera.top = 14;
    dir.shadow.camera.bottom = -14;
    scene.add(dir);
    const fill = new THREE.DirectionalLight(0xb8d4f0, 0.35);
    fill.position.set(-8, 6, -4);
    scene.add(fill);

    const grid = new THREE.GridHelper(26, 26, 0x2a4058, 0x1a2635);
    grid.position.y = -0.95;
    scene.add(grid);

    const hullGroup = new THREE.Group();
    scene.add(hullGroup);

    const matHullUpper = new THREE.MeshStandardMaterial({
      color: 0x1a2d42,
      metalness: 0.12,
      roughness: 0.78,
    });
    const matHullLower = new THREE.MeshStandardMaterial({
      color: 0xb03030,
      metalness: 0.06,
      roughness: 0.85,
    });
    const matWhite = new THREE.MeshStandardMaterial({
      color: 0xf2f4f8,
      metalness: 0.04,
      roughness: 0.82,
    });
    const matWhiteDeck = new THREE.MeshStandardMaterial({
      color: 0xe8ecf2,
      metalness: 0.05,
      roughness: 0.8,
    });
    const matWindows = new THREE.MeshStandardMaterial({
      color: 0x1e3a52,
      metalness: 0.2,
      roughness: 0.35,
    });
    const matFunnel = new THREE.MeshStandardMaterial({
      color: 0x2a3544,
      metalness: 0.15,
      roughness: 0.55,
    });
    const matFunnelTop = new THREE.MeshStandardMaterial({
      color: 0xf4c430,
      metalness: 0.25,
      roughness: 0.45,
    });

    function cruiseHullGeometry() {
      const B = 1.38;
      const bowZ = -4.35;
      const sternZ = 4.15;
      const shape = new THREE.Shape();
      shape.moveTo(0, bowZ);
      shape.quadraticCurveTo(B * 0.5, bowZ + 0.5, B * 0.95, bowZ + 1.45);
      shape.quadraticCurveTo(B * 1.18, bowZ + 2.6, B * 1.12, bowZ + 3.35);
      shape.lineTo(B * 1.08, 2.6);
      shape.lineTo(B * 1.05, 3.2);
      shape.quadraticCurveTo(B * 0.85, sternZ - 0.4, B * 0.55, sternZ);
      shape.lineTo(-B * 0.55, sternZ);
      shape.quadraticCurveTo(-B * 0.85, sternZ - 0.4, -B * 1.05, 3.2);
      shape.lineTo(-B * 1.08, 2.6);
      shape.lineTo(-B * 1.12, bowZ + 3.35);
      shape.quadraticCurveTo(-B * 1.18, bowZ + 2.6, -B * 0.95, bowZ + 1.45);
      shape.quadraticCurveTo(-B * 0.5, bowZ + 0.5, 0, bowZ);

      const geo = new THREE.ExtrudeGeometry(shape, {
        depth: 0.72,
        bevelEnabled: true,
        bevelThickness: 0.032,
        bevelSize: 0.032,
        bevelSegments: 2,
        curveSegments: 32,
      });
      geo.rotateX(Math.PI / 2);
      geo.translate(0, -0.36, 0);
      return geo;
    }

    const hullGeo = cruiseHullGeometry();

    const hullUpper = new THREE.Mesh(hullGeo, matHullUpper);
    hullUpper.position.set(0, 0.08, 0);
    hullUpper.castShadow = true;
    hullUpper.receiveShadow = true;
    hullGroup.add(hullUpper);

    const hullLower = new THREE.Mesh(hullGeo.clone(), matHullLower);
    hullLower.scale.set(1.02, 0.5, 1.02);
    hullLower.position.set(0, -0.28, 0);
    hullLower.castShadow = true;
    hullLower.receiveShadow = true;
    hullGroup.add(hullLower);

    // Open decks (long promenade deck on hull top).
    const promenade = new THREE.Mesh(
      new THREE.BoxGeometry(2.68, 0.06, 8.4),
      matWhiteDeck
    );
    promenade.position.set(0, 0.48, -0.05);
    promenade.castShadow = true;
    promenade.receiveShadow = true;
    hullGroup.add(promenade);

    // Thin navy accent stripe (hull band).
    const stripe = new THREE.Mesh(
      new THREE.BoxGeometry(2.62, 0.04, 8.25),
      matWindows
    );
    stripe.position.set(0, 0.22, -0.05);
    hullGroup.add(stripe);

    const cruise = new THREE.Group();
    hullGroup.add(cruise);

    function addPart(mesh, x, y, z) {
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      mesh.position.set(x, y, z);
      cruise.add(mesh);
    }

    // ── Stepped superstructure (aft → forward, classic “wedding cake”) ──
    const zAft = 2.85;
    addPart(new THREE.Mesh(new THREE.BoxGeometry(2.35, 0.38, 2.5), matWhite), 0.08, 0.72, zAft - 0.2);
    addPart(new THREE.Mesh(new THREE.BoxGeometry(2.15, 0.34, 2.15), matWhite), 0.08, 1.06, zAft - 0.15);
    addPart(new THREE.Mesh(new THREE.BoxGeometry(1.92, 0.32, 1.85), matWhite), 0.08, 1.38, zAft - 0.1);
    addPart(new THREE.Mesh(new THREE.BoxGeometry(1.68, 0.28, 1.55), matWhite), 0.08, 1.68, zAft - 0.05);
    addPart(new THREE.Mesh(new THREE.BoxGeometry(1.42, 0.26, 1.25), matWhite), 0.08, 1.94, zAft);

    // Window bands (dark glass rows on each tier).
    const band = (w, h, d, y, z) => {
      addPart(new THREE.Mesh(new THREE.BoxGeometry(w, h, d), matWindows), 0.08, y, z);
    };
    band(2.38, 0.12, 2.48, 0.72, zAft - 0.2);
    band(2.18, 0.1, 2.12, 1.06, zAft - 0.15);
    band(1.95, 0.1, 1.82, 1.38, zAft - 0.1);
    band(1.7, 0.09, 1.52, 1.68, zAft - 0.05);

    // Forward navigation / observation block (above bow).
    addPart(new THREE.Mesh(new THREE.BoxGeometry(0.95, 0.42, 0.72), matWhite), -0.05, 1.05, -2.35);
    addPart(new THREE.Mesh(new THREE.BoxGeometry(0.92, 0.14, 0.68), matWindows), -0.05, 1.12, -2.35);

    // Lido / pool deck slab (wide top aft).
    addPart(new THREE.Mesh(new THREE.BoxGeometry(1.55, 0.08, 1.05), matWhiteDeck), 0.1, 2.18, zAft + 0.05);

    // Twin funnels with yellow caps.
    function funnel(x, z) {
      addPart(new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.2, 0.75, 20, 1), matFunnel), x, 2.45, z);
      addPart(new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.16, 0.12, 16, 1), matFunnelTop), x, 2.86, z);
    }
    funnel(-0.35, zAft + 0.35);
    funnel(0.52, zAft + 0.3);

    // Bow mast.
    addPart(new THREE.Mesh(new THREE.CylinderGeometry(0.028, 0.035, 1.35, 8, 1), matWhite), -0.72, 1.15, -3.55);
    addPart(new THREE.Mesh(new THREE.BoxGeometry(0.85, 0.025, 0.025), matWhite), -0.72, 1.75, -3.55);

    const water = new THREE.Mesh(
      new THREE.PlaneGeometry(40, 40),
      new THREE.MeshStandardMaterial({
        color: 0x0e2438,
        roughness: 0.88,
        metalness: 0.04,
        transparent: true,
        opacity: 0.6,
      })
    );
    water.rotation.x = -Math.PI / 2;
    water.position.y = -0.42;
    water.receiveShadow = true;
    scene.add(water);

    const overlayGroup = new THREE.Group();
    hullGroup.add(overlayGroup);

    function addLabel(text, x, y, z, colorHex) {
      const c = document.createElement("canvas");
      c.width = 512;
      c.height = 72;
      const ctx = c.getContext("2d");
      ctx.fillStyle = "rgba(10,16,24,0.92)";
      ctx.fillRect(0, 0, 512, 72);
      ctx.strokeStyle = colorHex;
      ctx.globalAlpha = 0.4;
      ctx.strokeRect(1, 1, 510, 70);
      ctx.globalAlpha = 1;
      ctx.fillStyle = colorHex;
      ctx.font = "600 20px Segoe UI, system-ui, sans-serif";
      ctx.fillText(text, 14, 44);
      const tex = new THREE.CanvasTexture(c);
      tex.minFilter = THREE.LinearFilter;
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true }));
      sp.scale.set(2.2, 0.32, 1);
      sp.position.set(x, y + 0.48, z);
      overlayGroup.add(sp);
    }

    const list = markers && markers.length ? markers : [];
    for (let i = 0; i < list.length; i++) {
      const m = list[i];
      const col = new THREE.Color(m.color || "#22d3ee");
      const box = new THREE.Mesh(
        new THREE.BoxGeometry(0.38, 0.24, 0.32),
        new THREE.MeshStandardMaterial({
          color: col,
          emissive: col,
          emissiveIntensity: 0.25,
          transparent: true,
          opacity: 0.55,
          metalness: 0.15,
          roughness: 0.55,
        })
      );
      box.position.set(m.x, m.y, m.z);
      overlayGroup.add(box);
      const edges = new THREE.LineSegments(
        new THREE.EdgesGeometry(new THREE.BoxGeometry(0.4, 0.26, 0.34)),
        new THREE.LineBasicMaterial({ color: col.getHex(), transparent: true, opacity: 0.9 })
      );
      edges.position.copy(box.position);
      overlayGroup.add(edges);
      if (m.label) addLabel(m.label, m.x, m.y, m.z, m.color || "#22d3ee");
    }

    let isDragging = false;
    let px = 0;
    let py = 0;
    let autoRotate = true;
    const el = renderer.domElement;

    el.addEventListener("mousedown", (e) => {
      isDragging = true;
      px = e.clientX;
      py = e.clientY;
    });
    window.addEventListener("mouseup", () => {
      isDragging = false;
    });
    window.addEventListener("mousemove", (e) => {
      if (!isDragging) return;
      hullGroup.rotation.y += (e.clientX - px) * 0.0055;
      hullGroup.rotation.x += (e.clientY - py) * 0.003;
      hullGroup.rotation.x = Math.max(-0.4, Math.min(0.5, hullGroup.rotation.x));
      px = e.clientX;
      py = e.clientY;
    });
    el.addEventListener("wheel", (e) => {
      e.preventDefault();
      const z = Math.max(7, Math.min(22, zoomRef.current + e.deltaY * 0.01));
      zoomRef.current = z;
      camera.position.z = z;
      if (typeof zoomCbRef.current === "function") zoomCbRef.current(z);
    });

    let t = 0;
    function animate() {
      frameRef.current = requestAnimationFrame(animate);
      t += 0.016;
      if (autoRotate && !isDragging) hullGroup.rotation.y += 0.002;
      camera.position.z += (zoomRef.current - camera.position.z) * 0.12;
      overlayGroup.children.forEach((ch) => {
        if (ch.isMesh && ch.material && ch.material.opacity != null && ch.material.opacity < 0.9) {
          ch.material.opacity = 0.48 + Math.sin(t * 2 + ch.id * 0.15) * 0.06;
        }
      });
      renderer.render(scene, camera);
    }
    animate();

    function onResize() {
      if (!mountRef.current) return;
      W = mountRef.current.clientWidth || 640;
      camera.aspect = W / H;
      camera.updateProjectionMatrix();
      renderer.setSize(W, H);
    }
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(frameRef.current);
      window.removeEventListener("resize", onResize);
      renderer.dispose();
      if (container.contains(el)) container.removeChild(el);
    };
  }, [markers, height]);

  return (
    <div
      ref={mountRef}
      style={{
        width: "100%",
        height,
        borderRadius: 10,
        overflow: "hidden",
        border: "1px solid rgba(34,211,238,0.18)",
        position: "relative",
        background: "#0c1520",
        cursor: "grab",
      }}
    />
  );
}
