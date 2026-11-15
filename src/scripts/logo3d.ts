// The Axys3D logo as an interactive 3D object. Uses the studio's own logo model.
// Idle: a slow swing. Pointer near: it leans toward the pointer. Drag: it spins with momentum.
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

export async function createLogo(canvas: HTMLCanvasElement, url: string) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(26, 1, 0.1, 100);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x444440, 1.1));
  const key = new THREE.DirectionalLight(0xffffff, 2.4); key.position.set(3, 5, 6); scene.add(key);
  const rim = new THREE.DirectionalLight(0xefa11f, 1.6); rim.position.set(-5, 2, -4); scene.add(rim);

  const gltf = await new GLTFLoader().loadAsync(url);
  const pivot = new THREE.Group();
  const body = new THREE.MeshStandardMaterial({ color: 0xf3f0ea, roughness: 0.35, metalness: 0.15, vertexColors: true });

  // centre and size the model, find its widest face so the logo reads front on
  const box = new THREE.Box3().setFromObject(gltf.scene);
  const size = box.getSize(new THREE.Vector3());
  const centre = box.getCenter(new THREE.Vector3());
  gltf.scene.position.sub(centre);
  const holder = new THREE.Group();
  holder.add(gltf.scene);
  // the model was drawn lying flat: stand it up if its height is the thin axis
  if (size.y < size.z) holder.rotation.x = Math.PI / 2;
  pivot.add(holder);
  pivot.scale.setScalar(4 / Math.max(size.x, size.y, size.z));
  scene.add(pivot);

  // one mesh, no materials: paint the dot amber by position (it sits apart, upper right of the "s")
  gltf.scene.traverse((o) => {
    const m = o as THREE.Mesh;
    if (!m.isMesh) return;
    const g = m.geometry as THREE.BufferGeometry;
    const pos = g.getAttribute("position");
    const col = new Float32Array(pos.count * 3);
    g.computeBoundingBox();
    const b = g.boundingBox!;
    const w = b.max.x - b.min.x;
    const depthAxis = size.y < size.z ? "z" : "y"; // the axis that is "up" on the flat drawing
    const lo = (b.min as any)[depthAxis], hi = (b.max as any)[depthAxis];
    const amber = new THREE.Color(0xefa11f), white = new THREE.Color(0xf3f0ea);
    for (let i = 0; i < pos.count; i++) {
      const u = (pos.getX(i) - b.min.x) / w;
      const raw = depthAxis === "z" ? pos.getZ(i) : pos.getY(i);
      let v = (raw - lo) / (hi - lo);
      if (depthAxis === "z") v = 1 - v;
      const isDot = u > 0.615 && u < 0.695 && v > 0.66;
      const c = isDot ? amber : white;
      col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b;
    }
    g.setAttribute("color", new THREE.BufferAttribute(col, 3));
    g.computeVertexNormals();
    m.material = body;
  });

  const fit = () => {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    const hFov = 2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2) * camera.aspect);
    camera.position.set(0, 0, 2.5 / Math.tan(hFov / 2));
    camera.lookAt(0, 0, 0);
    camera.updateProjectionMatrix();
  };
  fit();
  new ResizeObserver(fit).observe(canvas);

  let yaw = -0.5, pitch = 0.12, vy = 0, leanX = 0, leanY = 0, dragging = false, lastX = 0, lastY = 0, visible = true, raf = 0;
  canvas.addEventListener("pointerdown", (e) => { dragging = true; lastX = e.clientX; lastY = e.clientY; canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener("pointermove", (e) => {
    const r = canvas.getBoundingClientRect();
    leanX = ((e.clientX - r.left) / r.width - 0.5) * 0.5;
    leanY = ((e.clientY - r.top) / r.height - 0.5) * 0.3;
    if (!dragging) return;
    vy = (e.clientX - lastX) * 0.008; yaw += vy;
    pitch = Math.max(-0.5, Math.min(0.5, pitch + (e.clientY - lastY) * 0.004));
    lastX = e.clientX; lastY = e.clientY;
  });
  const end = () => { dragging = false; };
  canvas.addEventListener("pointerup", end);
  canvas.addEventListener("pointercancel", end);
  canvas.addEventListener("pointerleave", () => { leanX = 0; leanY = 0; });

  let rest = -0.5;
  const frame = (t: number) => {
    raf = 0;
    if (!dragging) {
      yaw += vy; vy *= 0.94;
      // after a spin, settle back to the nearest front facing angle and keep a slow swing
      if (Math.abs(vy) < 0.002) {
        const turns = Math.round(yaw / (Math.PI * 2));
        rest = turns * Math.PI * 2 + Math.sin(t / 2600) * 0.38 + leanX;
        yaw += (rest - yaw) * 0.04;
        pitch += (0.1 + leanY - pitch) * 0.05;
      }
    }
    pivot.rotation.set(pitch, yaw, 0);
    renderer.render(scene, camera);
    if (visible && !document.hidden) raf = requestAnimationFrame(frame);
  };
  const kick = () => { if (!raf) raf = requestAnimationFrame(frame); };
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; if (visible) kick(); }).observe(canvas);
  document.addEventListener("visibilitychange", kick);
  kick();
}
