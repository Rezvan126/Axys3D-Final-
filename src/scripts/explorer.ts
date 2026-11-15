// The interactive building on the home page.
// One real project model (exported from Revit, see tools/build-model.py) shown through the
// stages the studio delivers: sketch, drawings, 3D model, BIM detail, materials, final render.
// Loaded only when the section comes near the screen. Draws only when something changes.
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/examples/jsm/loaders/DRACOLoader.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";

type Disc = "architecture" | "structure" | "electrical" | "mechanical" | "plumbing" | "interiors";
const DISCS: Disc[] = ["architecture", "structure", "electrical", "mechanical", "plumbing", "interiors"];
const DISC_COLOR: Record<Disc, number> = {
  architecture: 0x9a9aa0, structure: 0xefa11f, electrical: 0xff6b5e, mechanical: 0x5ac8fa, plumbing: 0x34c759, interiors: 0xb9a7ff,
};

// camera presets per stage: yaw and pitch in degrees, distance as a multiple of the fitted distance
const VIEWS = [
  { yaw: -38, pitch: 16, dist: 1.0 },   // sketch
  { yaw: 0, pitch: 89.5, dist: 1.5 },  // drawings (plan)
  { yaw: 32, pitch: 22, dist: 1.0 },    // 3D model
  { yaw: 205, pitch: 30, dist: 1.2 },  // BIM (pulled back: the layers panel and the words share the screen)
  { yaw: -52, pitch: 12, dist: 0.95 },  // materials
  { yaw: -52, pitch: 10, dist: 0.9 },   // render (the photo covers the canvas)
];

export interface PartInfo { d: string; c: string; t: string; p: string; size: [number, number, number]; same: number }
export interface ExplorerApi { setStage(i: number): void; setDiscipline(d: Disc, on: boolean): void; clearSelection(): void; resize(): void; dispose(): void; }

export async function createExplorer(opts: {
  canvas: HTMLCanvasElement;
  url: string;
  onProgress?: (p: number) => void;
  onPick?: (info: { d: string; c: string; t: string; p: string } | null, x: number, y: number) => void;
  onCounts?: (counts: Record<string, number>, total: number) => void;
  /** a part was clicked (or the selection was cleared) */
  onSelect?: (info: PartInfo | null) => void;
}): Promise<ExplorerApi> {
  const { canvas } = opts;
  const coarse = window.matchMedia("(pointer: coarse)").matches;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: !coarse, alpha: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, coarse ? 1.5 : 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.localClippingEnabled = true;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.08;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(28, 1, 0.1, 500);
  // soft light from all round (a studio room, so glass and metal have something to reflect),
  // a low warm sun that casts real shadows, and a cool fill from the other side
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.55;
  pmrem.dispose();
  const hemi = new THREE.HemisphereLight(0xdfe9ff, 0x3a3630, 0.45); scene.add(hemi);
  const sun = new THREE.DirectionalLight(0xffe9cf, 2.6); sun.position.set(7, 9, 6); scene.add(sun); scene.add(sun.target);
  sun.castShadow = true;
  sun.shadow.mapSize.setScalar(coarse ? 1024 : 2048);
  sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.02; sun.shadow.radius = 3;
  const fill = new THREE.DirectionalLight(0xbcd0ff, 0.35); fill.position.set(-8, 4, -6); scene.add(fill);

  // ---------- load ----------
  const draco = new DRACOLoader().setDecoderPath("/draco/");
  const loader = new GLTFLoader().setDRACOLoader(draco);
  const gltf = await loader.loadAsync(opts.url, (e) => opts.onProgress?.(e.total ? e.loaded / e.total : 0.5));
  draco.dispose();

  const root = gltf.scene;
  const box = new THREE.Box3().setFromObject(root);
  const size = box.getSize(new THREE.Vector3());
  const centre = box.getCenter(new THREE.Vector3());
  const k = 10 / Math.max(size.x, size.z);
  root.scale.setScalar(k);
  root.position.set(-centre.x * k, -box.min.y * k, -centre.z * k);
  root.updateMatrixWorld(true);
  scene.add(root);
  const H = size.y * k;
  const radius = Math.hypot(size.x, size.y, size.z) * k * 0.5;
  const target = new THREE.Vector3(0, H * 0.4, 0);
  // the shadow covers the whole building and nothing more
  sun.target.position.copy(target);
  sun.position.copy(target).add(new THREE.Vector3(7, 9, 6).normalize().multiplyScalar(radius * 2.2));
  const sc = sun.shadow.camera; sc.left = -radius * 1.15; sc.right = radius * 1.15; sc.top = radius * 1.15; sc.bottom = -radius * 1.15; sc.near = 0.1; sc.far = radius * 4.6; sc.updateProjectionMatrix();

  const meshes: THREE.Mesh[] = [];
  root.traverse((o) => { if ((o as THREE.Mesh).isMesh) { const m = o as THREE.Mesh; m.castShadow = m.receiveShadow = true; meshes.push(m); } });
  const counts: Record<string, number> = {};
  meshes.forEach((m) => { const d = m.userData.d as string; counts[d] = (counts[d] || 0) + 1; });
  opts.onCounts?.(counts, meshes.length);

  // ---------- materials ----------
  const clip = new THREE.Plane(new THREE.Vector3(0, -1, 0), H * 0.6); // plan cut height
  const noClip: THREE.Plane[] = [];
  const hidden = new THREE.MeshBasicMaterial({ colorWrite: false, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 });
  const clay = new THREE.MeshStandardMaterial({ color: 0xd8d3c9, roughness: 1, metalness: 0, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 });
  const bim: Record<string, THREE.Material> = {};
  DISCS.forEach((d) => {
    bim[d] = d === "architecture"
      ? new THREE.MeshStandardMaterial({ color: DISC_COLOR[d], roughness: 1, transparent: true, opacity: 0.1, depthWrite: false })
      : new THREE.MeshStandardMaterial({ color: DISC_COLOR[d], roughness: 0.6, emissive: DISC_COLOR[d], emissiveIntensity: 0.25 });
  });
  // Finishes use the same texture maps as the studio's rendered scene (see tools/extract-textures.py).
  // The web model carries no UVs, so each map is laid on by box projection in world space:
  // the face's direction picks the plane, and real sizes set how often the map repeats.
  const texLoader = new THREE.TextureLoader();
  const loadTex = (name: string) => {
    const t = texLoader.load(`/media/tex/${name}.webp`, () => kick());
    t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
    return t;
  };
  const boxed = (map: THREE.Texture, tileMetres: number, gain: number, roughness: number, tint = 0xffffff) => {
    const mat = new THREE.MeshStandardMaterial({ color: tint, roughness, metalness: 0 });
    const scale = 1 / (tileMetres * k);
    mat.onBeforeCompile = (sh) => {
      sh.uniforms.boxMap = { value: map }; sh.uniforms.boxScale = { value: scale }; sh.uniforms.boxGain = { value: gain };
      sh.vertexShader = sh.vertexShader
        .replace("#include <common>", "#include <common>\nvarying vec3 vBoxP; varying vec3 vBoxN;")
        .replace("#include <project_vertex>", "#include <project_vertex>\nvBoxP = (modelMatrix * vec4(transformed, 1.0)).xyz; vBoxN = normalize(mat3(modelMatrix) * objectNormal);");
      sh.fragmentShader = sh.fragmentShader
        .replace("#include <common>", "#include <common>\nuniform sampler2D boxMap; uniform float boxScale; uniform float boxGain; varying vec3 vBoxP; varying vec3 vBoxN;")
        .replace("#include <map_fragment>", "#include <map_fragment>\nvec3 bn = abs(normalize(vBoxN)); vec2 buv = bn.y > 0.5 ? vBoxP.xz : (bn.x > bn.z ? vBoxP.zy : vBoxP.xy); diffuseColor.rgb *= texture2D(boxMap, buv * boxScale).rgb * boxGain;");
    };
    mat.customProgramCacheKey = () => "box";
    return mat;
  };
  const std = (color: number, roughness = 0.85, metalness = 0) => new THREE.MeshStandardMaterial({ color, roughness, metalness });
  const finish = {
    siding: boxed(loadTex("siding"), 1.6, 2.1, 0.78),            // lap siding, boards about 200 mm
    stucco: boxed(loadTex("stucco"), 3, 1.05, 0.95),
    plaster: boxed(loadTex("plaster"), 2.5, 1.0, 0.95),
    roof: boxed(loadTex("roof"), 2.4, 1.7, 0.94),            // charcoal shingles: even tone, rows visible, no patchwork
    deck: boxed(loadTex("deck"), 1.8, 1.0, 0.7),
    concrete: boxed(loadTex("concrete"), 3, 0.95, 0.92),
    grass: boxed(loadTex("grass"), 3.5, 0.9, 1),
    // windows and glazed doors: glass and frame colours are painted per face in the model itself
    glazed: new THREE.MeshStandardMaterial({ color: 0xffffff, vertexColors: true, roughness: 0.16, metalness: 0.15, envMapIntensity: 1.6 }),
    trim: std(0xf2f1ed, 0.6), black: std(0x1b1c1f, 0.45, 0.55), casework: std(0xe6e0d5, 0.6), white: std(0xf4f4f2, 0.35),
    light: std(0xdcdcdc, 0.5), tile: std(0xcfd2d4, 0.35), door: std(0xe9e7e2, 0.55),
  };
  const finishFor = (m: THREE.Mesh) => {
    const c = String(m.userData.c), t = String(m.userData.t).toLowerCase(), d = String(m.userData.d);
    const existing = m.userData.p === "Existing";
    if (c === "Roofs") return /fascia|gutter|downspout/.test(t) ? finish.black : finish.roof;
    if (c === "Windows" || c === "Doors") return m.geometry.getAttribute("color") ? finish.glazed : finish.door;
    if (c === "Stairs and railings") return /stair|run|tread|landing/.test(t) ? (/cast|monolithic/.test(t) ? finish.concrete : finish.deck) : finish.black;
    if (c === "Walls") {
      if (/stem wall|concrete/.test(t)) return finish.concrete;
      if (/trim|sweep/.test(t)) return finish.trim;
      if (/partition|interior/.test(t)) return finish.plaster;
      if (/stucco|cement/.test(t)) return finish.stucco;
      return finish.siding;
    }
    if (c === "Floors") return /surface/.test(t) ? finish.grass : finish.deck;
    if (c === "Ceilings") return finish.white;
    if (c === "Framing") return /deck/.test(t) ? finish.deck : existing ? finish.concrete : finish.deck;
    if (c === "Columns") return /rectangular/.test(t) ? finish.black : finish.concrete;
    if (d === "structure") return finish.concrete;
    if (c === "Casework") return finish.casework;
    if (c === "Finishes") return /tile/.test(t) ? finish.tile : finish.trim;
    if (d === "plumbing") return finish.white;
    return finish.light;
  };
  // drilled piers sit below ground: shown with the structure in the BIM stage, hidden in the finished views
  const buried = (m: THREE.Mesh) => m.userData.c === "Columns" && /round/i.test(String(m.userData.t));
  // Some pieces of the export are open sheets or have faces pointing inwards. Drawing every surface on
  // both sides means none of them shows as a hole or a black patch, whichever way it faces.
  [hidden, clay, ...Object.values(bim), ...Object.values(finish)].forEach((m) => { m.side = THREE.DoubleSide; m.shadowSide = THREE.DoubleSide; });
  const finishOf = new Map<THREE.Mesh, THREE.Material>();
  meshes.forEach((m) => finishOf.set(m, finishFor(m)));
  const highlight = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.55, roughness: 0.4 , side: THREE.DoubleSide });
  // while one part is being inspected the rest of the building turns to faint glass around it
  const ghost = new THREE.MeshStandardMaterial({ color: 0x9aa0ad, roughness: 1, transparent: true, opacity: 0.07, depthWrite: false , side: THREE.DoubleSide });
  const picked = new THREE.MeshStandardMaterial({ color: 0xefa11f, emissive: 0xefa11f, emissiveIntensity: 0.35, roughness: 0.55 , side: THREE.DoubleSide });
  const glowCache = new Map<string, THREE.Material>();
  const glow = (mat: THREE.Material) => {
    let out = glowCache.get(mat.uuid);
    if (!out) { const c = mat.clone() as THREE.MeshStandardMaterial; c.onBeforeCompile = mat.onBeforeCompile; c.customProgramCacheKey = mat.customProgramCacheKey; c.emissive = new THREE.Color(0xefa11f); c.emissiveIntensity = 0.3; out = c; glowCache.set(mat.uuid, out); }
    return out;
  };

  // Revit models often have two surfaces in exactly the same plane (a wall and its finish, an existing
  // slab and a new one). Drawn as is they flicker. Each category is pushed back by its own tiny amount.
  const ORDER = ["Finishes", "Windows", "Doors", "Casework", "Appliances", "Plumbing fixtures", "Lighting", "Power and switching", "Ventilation", "Heating and cooling",
    "Stairs and railings", "Columns", "Framing", "Walls", "Roofs", "Ceilings", "Floors", "Slabs", "Foundations", "Other elements"];
  const layerCache = new Map<string, THREE.Material>();
  const layered = (mat: THREE.Material, m: THREE.Mesh) => {
    if (mat === hidden) return mat;
    const i = Math.max(0, ORDER.indexOf(String(m.userData.c))) + (m.userData.p === "Existing" ? 0.5 : 0);
    const k = mat.uuid + ":" + i;
    let out = layerCache.get(k);
    // a constant nudge only: a slope based one lets interiors show through roofs seen at a low angle
    if (!out) { out = mat.clone(); out.onBeforeCompile = mat.onBeforeCompile; out.customProgramCacheKey = mat.customProgramCacheKey; out.polygonOffset = true; out.polygonOffsetFactor = 1; out.polygonOffsetUnits = 1 + i * 3; layerCache.set(k, out); }
    return out;
  };

  // ---------- edge drawings: one line object per discipline, built a little at a time ----------
  const lineMat: Record<string, THREE.LineBasicMaterial> = {};
  const lines: Record<string, THREE.LineSegments> = {};
  const edgeCache = new Map<string, THREE.BufferGeometry>();
  const inv = new THREE.Matrix4().copy(root.matrixWorld).invert();
  async function buildEdges() {
    const acc: Record<string, number[]> = {};
    DISCS.forEach((d) => (acc[d] = []));
    const v = new THREE.Vector3();
    const local = new THREE.Matrix4();
    let last = performance.now();
    for (const m of meshes) {
      if (buried(m)) continue; // piers below ground stay out of the line drawings
      const d = m.userData.d as string;
      let eg = edgeCache.get(m.geometry.uuid);
      if (!eg) { eg = new THREE.EdgesGeometry(m.geometry, 32); edgeCache.set(m.geometry.uuid, eg); }
      local.multiplyMatrices(inv, m.matrixWorld);
      const pos = eg.getAttribute("position");
      const out = acc[d];
      for (let i = 0; i < pos.count; i++) { v.fromBufferAttribute(pos, i).applyMatrix4(local); out.push(v.x, v.y, v.z); }
      if (performance.now() - last > 10) { await new Promise((r) => setTimeout(r, 0)); last = performance.now(); }
    }
    edgeCache.forEach((g) => g.dispose()); edgeCache.clear();
    DISCS.forEach((d) => {
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.Float32BufferAttribute(acc[d], 3));
      lineMat[d] = new THREE.LineBasicMaterial({ color: 0xf5f5f7, transparent: true, opacity: 0 });
      lines[d] = new THREE.LineSegments(g, lineMat[d]);
      lines[d].visible = false;
      root.add(lines[d]);
    });
  }

  // ---------- stage logic ----------
  let stage = -1;
  const discOn: Record<string, boolean> = {};
  DISCS.forEach((d) => (discOn[d] = true));
  const lineTarget: Record<string, number> = {};
  let hovered: THREE.Mesh | null = null;
  let selected: THREE.Mesh | null = null;

  function paint() {
    const s = stage;
    const cut = s === 1;
    for (const m of meshes) {
      const d = m.userData.d as Disc;
      const shell = d === "architecture" || d === "structure";
      let mat: THREE.Material = hidden, vis = true;
      if (s === 0) { vis = shell && !buried(m); mat = hidden; }
      else if (s === 1) { mat = hidden; }
      else if (s === 2) { vis = shell && !buried(m); mat = clay; }
      else if (s === 3) { vis = discOn[d]; mat = bim[d]; }
      else { vis = (d !== "electrical" && d !== "mechanical" || m.userData.c === "Lighting") && !buried(m); mat = finishOf.get(m)!; }
      m.visible = vis;
      if (selected && vis && m !== selected) m.material = ghost;
      else if (m === selected) { m.visible = true; m.material = s === 4 ? glow(mat) : picked; }
      else m.material = m === hovered && s === 3 ? highlight : s === 3 ? mat : layered(mat, m);
    }
    [hidden, clay, ...Object.values(finish), ...layerCache.values()].forEach((m) => { m.clippingPlanes = cut ? [clip] : noClip; });
    DISCS.forEach((d) => {
      const shell = d === "architecture" || d === "structure";
      const lm = lineMat[d]; if (!lm) return;
      lm.clippingPlanes = cut ? [clip] : noClip;
      let o = 0, col = 0xf5f5f7;
      if (s === 0) o = shell ? 0.9 : 0;
      else if (s === 1) { o = shell ? 0.95 : 0.8; col = shell ? 0xf5f5f7 : 0xefa11f; }
      else if (s === 2) { o = shell ? 0.28 : 0; col = 0x1a1a1a; }
      else if (s === 3) { o = d === "architecture" && discOn[d] ? 0.3 : 0; }
      if (selected && s >= 2) { o = shell ? 0.2 : 0; col = 0xf5f5f7; }
      lm.color.setHex(col);
      lineTarget[d] = o;
      if (o > 0) lines[d].visible = true;
    });
    sun.intensity = s === 3 ? 1.2 : 2.6;
    sun.castShadow = (s === 2 || s === 4) && !selected;
    // the clay model is lit harder from one side so its form reads; finishes get softer, fuller light
    scene.environmentIntensity = s === 2 ? 0.22 : 0.55;
    hemi.intensity = s === 2 ? 0.25 : 0.45;
    if (s === 2) sun.intensity = 3.1;
  }

  // ---------- camera ----------
  const cur = { yaw: VIEWS[0].yaw, pitch: VIEWS[0].pitch, dist: 1 };
  const goal = { ...cur };
  let userYaw = 0, userYawGoal = 0;
  let fitDist = 30;
  const tCur = target.clone(), tGoal = target.clone(); // what the camera looks at: the building, or one part of it
  function fit() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    const vFov = THREE.MathUtils.degToRad(camera.fov);
    const hFov = 2 * Math.atan(Math.tan(vFov / 2) * camera.aspect);
    const r = radius * (w < 760 ? 0.93 : 0.74);
    fitDist = r / Math.sin(Math.min(vFov, hFov) / 2);
    camera.near = fitDist * 0.03; camera.far = fitDist * 3.5;
    // on wide screens the words sit over the bottom of the picture, so lift the model clear of them
    if (w >= 760) camera.setViewOffset(w, h, 0, Math.round(h * 0.13), w, h);
    else if (selected) camera.setViewOffset(w, h, 0, Math.round(h * 0.2), w, h);
    else camera.clearViewOffset();
    camera.updateProjectionMatrix();
    dirty = true;
  }
  function placeCamera() {
    const yaw = THREE.MathUtils.degToRad(cur.yaw + userYaw), pitch = THREE.MathUtils.degToRad(cur.pitch);
    const d = fitDist * cur.dist;
    camera.position.set(tCur.x + d * Math.cos(pitch) * Math.sin(yaw), tCur.y + d * Math.sin(pitch), tCur.z + d * Math.cos(pitch) * Math.cos(yaw));
    camera.up.set(0, 1, 0);
    camera.lookAt(tCur);
  }

  // ---------- render loop (on demand) ----------
  let dirty = true, running = true, visible = true, raf = 0, sway = 0;
  function frame(t: number) {
    raf = 0;
    if (!running) return;
    let moving = false;
    const ease = 0.085;
    // shortest way round for yaw
    let dy = goal.yaw - cur.yaw; dy = ((dy + 540) % 360) - 180;
    if (Math.abs(dy) > 0.02) { cur.yaw += dy * ease; moving = true; } else cur.yaw = goal.yaw;
    for (const key of ["pitch", "dist"] as const) {
      const d = goal[key] - cur[key];
      if (Math.abs(d) > 0.002) { cur[key] += d * ease; moving = true; } else cur[key] = goal[key];
    }
    if (tCur.distanceToSquared(tGoal) > 1e-6) { tCur.lerp(tGoal, ease); moving = true; } else tCur.copy(tGoal);
    const du = userYawGoal - userYaw;
    if (Math.abs(du) > 0.02) { userYaw += du * 0.18; moving = true; } else userYaw = userYawGoal;
    DISCS.forEach((d) => {
      const lm = lineMat[d]; if (!lm) return;
      const diff = (lineTarget[d] ?? 0) - lm.opacity;
      if (Math.abs(diff) > 0.01) { lm.opacity += diff * 0.14; moving = true; }
      else { lm.opacity = lineTarget[d] ?? 0; if (lm.opacity === 0) lines[d].visible = false; }
    });
    // a slow breath of rotation while the section is on screen
    if (!reduce && visible && !dragging && !selected && stage !== 1 && stage !== 5) { sway = Math.sin(t / 5200) * 5; moving = true; } else sway *= 0.9;
    if (moving || dirty) {
      const keep = userYaw; userYaw += sway; placeCamera(); userYaw = keep;
      renderer.render(scene, camera);
      dirty = false;
    }
    if (visible) raf = requestAnimationFrame(frame);
  }
  const kick = () => { dirty = true; if (!raf && running && visible) raf = requestAnimationFrame(frame); };

  // ---------- drag to turn (horizontal only, so the page still scrolls on touch) ----------
  let dragging = false, lastX = 0, downX = 0, downY = 0;
  canvas.style.touchAction = "pan-y";
  canvas.addEventListener("pointerdown", (e) => { dragging = true; lastX = downX = e.clientX; downY = e.clientY; canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener("pointermove", (e) => {
    if (dragging) { userYawGoal -= (e.clientX - lastX) * 0.35; lastX = e.clientX; kick(); }
    else if (stage >= 2 && stage <= 4 && !coarse) queuePick(e.clientX, e.clientY);
  });
  const end = (e: PointerEvent) => {
    if (!dragging) return;
    dragging = false;
    if (stage >= 2 && stage <= 4 && Math.hypot(e.clientX - downX, e.clientY - downY) < 6) {
      const m = hitAt(e.clientX, e.clientY);
      select(m === selected ? null : m);
    }
  };
  canvas.addEventListener("pointerup", end);
  canvas.addEventListener("pointercancel", () => { dragging = false; });
  canvas.addEventListener("pointerleave", () => { if (!coarse) setHover(null, 0, 0); });

  // ---------- picking (BIM stage) ----------
  const ray = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  let pickQueued = false, px = 0, py = 0;
  function queuePick(x: number, y: number) { px = x; py = y; if (pickQueued) return; pickQueued = true; requestAnimationFrame(() => { pickQueued = false; pick(px, py); }); }
  function setHover(m: THREE.Mesh | null, x: number, y: number) {
    canvas.style.cursor = m ? "pointer" : "";
    if (stage !== 3 || selected) { if (hovered) { hovered = null; paint(); kick(); opts.onPick?.(null, 0, 0); } return; }
    if (hovered !== m) {
      if (hovered) hovered.material = bim[hovered.userData.d];
      hovered = m;
      if (m) m.material = highlight;
      kick();
    }
    opts.onPick?.(m ? { d: m.userData.d, c: m.userData.c, t: m.userData.t, p: m.userData.p } : null, x, y);
  }
  function hitAt(x: number, y: number): THREE.Mesh | null {
    const r = canvas.getBoundingClientRect();
    ndc.set(((x - r.left) / r.width) * 2 - 1, -((y - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    const hits = ray.intersectObjects(meshes.filter((m) => m.visible), false);
    // the see through shell should not block what is inside it
    const hit = (stage === 3 || selected ? hits.find((h) => { const o = h.object as THREE.Mesh; return o === selected || (stage === 3 && o.userData.d !== "architecture"); }) : null) ?? hits[0];
    return hit ? (hit.object as THREE.Mesh) : null;
  }
  function pick(x: number, y: number) {
    const r = canvas.getBoundingClientRect();
    setHover(hitAt(x, y), x - r.left, y - r.top);
  }

  // ---------- inspect one part: the camera flies to it and the rest fades to glass ----------
  const bb = new THREE.Box3(), sph = new THREE.Sphere(), v3 = new THREE.Vector3();
  function select(m: THREE.Mesh | null) {
    if (m === selected) return;
    if (hovered) { hovered = null; opts.onPick?.(null, 0, 0); }
    selected = m;
    if (m) {
      bb.setFromObject(m); bb.getBoundingSphere(sph);
      tGoal.copy(sph.center);
      const vF = THREE.MathUtils.degToRad(camera.fov), hF = 2 * Math.atan(Math.tan(vF / 2) * camera.aspect);
      const d = Math.max((sph.radius * 2.3) / Math.sin(Math.min(vF, hF) / 2), fitDist * 0.2);
      goal.dist = Math.min(1, d / fitDist);
      goal.pitch = 20;
      // look at it from the outside of the building, on the side the part is on
      cur.yaw += userYaw; userYaw = userYawGoal = 0;
      const hx = sph.center.x - target.x, hz = sph.center.z - target.z;
      goal.yaw = Math.hypot(hx, hz) > radius * 0.1 ? THREE.MathUtils.radToDeg(Math.atan2(hx, hz)) : cur.yaw;
      const sz = bb.getSize(v3);
      const dims = [sz.x / k, sz.z / k, sz.y / k].map((n) => Math.round(n * 100) / 100) as [number, number, number];
      opts.onSelect?.({ d: m.userData.d, c: m.userData.c, t: m.userData.t, p: m.userData.p, size: dims, same: meshes.filter((o) => o.userData.c === m.userData.c).length });
    } else {
      tGoal.copy(target);
      Object.assign(goal, VIEWS[Math.max(0, stage)]);
      userYawGoal = 0;
      opts.onSelect?.(null);
    }
    paint();
    fit();
    kick();
  }

  // ---------- life cycle ----------
  const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; if (visible) kick(); });
  io.observe(canvas);
  const onVis = () => { running = !document.hidden; if (running) kick(); };
  document.addEventListener("visibilitychange", onVis);
  const ro = new ResizeObserver(() => { fit(); kick(); });
  ro.observe(canvas);

  fit();
  await buildEdges();

  const api: ExplorerApi = {
    setStage(i) {
      if (i === stage) return;
      if (hovered) { hovered = null; opts.onPick?.(null, 0, 0); }
      if (selected) { selected = null; tGoal.copy(target); opts.onSelect?.(null); }
      canvas.style.cursor = "";
      stage = i;
      Object.assign(goal, VIEWS[i]);
      userYawGoal = 0;
      paint();
      kick();
    },
    setDiscipline(d, on) { discOn[d] = on; if (selected && selected.userData.d === d && !on) select(null); else if (stage === 3) { paint(); kick(); } },
    clearSelection() { select(null); },
    resize() { fit(); kick(); },
    dispose() {
      running = false; cancelAnimationFrame(raf); io.disconnect(); ro.disconnect();
      document.removeEventListener("visibilitychange", onVis);
      renderer.dispose();
    },
  };
  return api;
}
