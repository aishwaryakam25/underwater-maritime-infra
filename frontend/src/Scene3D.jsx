/**
 * Minimal 3D WebGL background for NautiCAI — rotating sonar-style ring.
 * Renders behind main content; pointer-events: none.
 */
import React, { useRef, useEffect } from "react";
import * as THREE from "three";

export default function Scene3D() {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let frameId;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(28, 1, 0.1, 1000);
    camera.position.set(0, 0, 8);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x040b14, 0.4);
    container.appendChild(renderer.domElement);

    // Main sonar ring — clearly visible cyan wireframe
    const geometry = new THREE.TorusGeometry(2.2, 0.08, 20, 56);
    const material = new THREE.MeshBasicMaterial({
      color: 0x00e5ff,
      transparent: true,
      opacity: 0.35,
      side: THREE.DoubleSide,
      wireframe: true,
    });
    const torus = new THREE.Mesh(geometry, material);
    torus.rotation.x = Math.PI * 0.2;
    scene.add(torus);

    // Second ring — teal, visible
    const ring2 = new THREE.Mesh(
      new THREE.TorusGeometry(1.6, 0.05, 16, 40),
      new THREE.MeshBasicMaterial({ color: 0x00e5ff, transparent: true, opacity: 0.22, wireframe: true, side: THREE.DoubleSide })
    );
    ring2.rotation.x = Math.PI * 0.35;
    ring2.rotation.z = Math.PI * 0.25;
    scene.add(ring2);

    // Third ring — inner, accent
    const ring3 = new THREE.Mesh(
      new THREE.TorusGeometry(0.9, 0.03, 12, 32),
      new THREE.MeshBasicMaterial({ color: 0x67e8f9, transparent: true, opacity: 0.28, wireframe: true, side: THREE.DoubleSide })
    );
    ring3.rotation.x = Math.PI * 0.5;
    ring3.rotation.y = Math.PI * 0.15;
    scene.add(ring3);

    function resize() {
      const w = container.offsetWidth;
      const h = container.offsetHeight;
      if (!w || !h) return;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    }

    function animate() {
      frameId = requestAnimationFrame(animate);
      const t = performance.now() * 0.0003;
      torus.rotation.y = t;
      torus.rotation.x = Math.PI * 0.2 + Math.sin(t * 0.7) * 0.1;
      ring2.rotation.y = t * 0.8;
      ring2.rotation.x = Math.PI * 0.35 + Math.cos(t * 0.5) * 0.08;
      ring3.rotation.y = t * 1.1;
      ring3.rotation.x = Math.PI * 0.5 + Math.sin(t * 0.4) * 0.06;
      renderer.render(scene, camera);
    }

    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(container);
    animate();

    return () => {
      ro.disconnect();
      cancelAnimationFrame(frameId);
      renderer.dispose();
      if (container && renderer.domElement.parentNode === container) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  return <div className="scene-3d-wrap" ref={containerRef} aria-hidden="true" />;
}
