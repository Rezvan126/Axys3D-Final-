// The interactive building on the home page.
// One real project model (exported from Revit through Navisworks, see tools/build-model-navis.py)
// shown through the stages the studio delivers: sketch, drawings, 3D model, BIM detail, materials,
// final render. The model has its interiors, so the 3D stages can lift the roof, show one floor at a
// time and slice the house open. Loaded only when the section comes near the screen. Draws only when
// something changes.
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/examples/jsm/loaders/DRACOLoader.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";

type Disc = "architecture" | "structure" | "electrical" | "mechanical" | "plumbing" | "interiors";
const DISCS: Disc[] = ["architecture", "structure", "electrical", "mechanical", "plumbing", "interiors"];
const DISC_COLOR: Record<Disc, number> = {
  architecture: 0x9a9aa0, structure: 0xefa11f, electrical: 0xff6b5e, mechanical: 0x5ac8fa, plumbing: 0x34c759, interiors: 0xb9a7ff,
};

// camera presets per stage: yaw and pitch in degrees, distance as a multiple of the fitted distance.
// The house is an infill plot, long and narrow with blank side walls: the street end is at yaw 180.
// On wide screens the words sit bottom left, so the views keep the street front to the right of them.
type View = { yaw: number; pitch: number; dist: number };
const VIEWS: View[] = [
  { yaw: 158, pitch: 13, dist: 1.12 },   // sketch: the street front
  { yaw: 90, pitch: 89.5, dist: 1.24 },   // drawings (plan, long side across the screen)
  { yaw: 150, pitch: 24, dist: 1.2 },    // 3D model
  { yaw: 52, pitch: 30, dist: 1.36 },    // BIM
  { yaw: 156, pitch: 18, dist: 1.15 },   // materials
  { yaw: 158, pitch: 12, dist: 1.12 },   // render (the film covers the canvas)
];
// phones: the picture is a small landscape window, so come a little closer
const VIEWS_PHONE: View[] = [
  { yaw: 158, pitch: 13, dist: 0.74 },
  { yaw: 90, pitch: 89.5, dist: 0.9 },
  { yaw: 150, pitch: 24, dist: 0.88 },
  { yaw: 54, pitch: 32, dist: 0.92 },
  { yaw: 156, pitch: 20, dist: 0.84 },
  { yaw: 158, pitch: 12, dist: 0.74 },
];

export interface PartInfo { d: string; c: string; t: string; l: string; size: [number, number, number]; same: number }
/** roof: lift the roof off. floor: -1 shows every floor, 0 to 2 shows up to that floor. section: 0 (off) to 1. axis: 0 slices along the length, 1 across it. */
export interface CutState { roof: boolean; floor: number; section: number; axis: 0 | 1 }
export interface ExplorerApi {
  setStage(i: number): void; setDiscipline(d: Disc, on: boolean): void; setCut(c: Partial<CutState>): void;
  clearSelection(): void; resize(): void; dispose(): void;
}

interface Part { d: Disc; c: string; t: string; l: string; f: number; node: THREE.Object3D; meshes: THREE.Mesh[] }

export async function createExplorer(opts: {
  canvas: HTMLCanvasElement;
  url: string;
  onProgress?: (p: number) => void;
  onPick?: (info: { d: string; c: string; t: string; l: string } | null, x: number, y: number) => void;
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
  renderer.shadowMap.type = THREE.PCFShadowMap;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(28, 1, 0.1, 500);
  // soft light from all round (a studio room, so glass and metal have something to reflect),
  // a low warm sun that casts real shadows, and a cool fill from the other side
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.55;
  pmrem.dispose();
  const hemi = new THREE.HemisphereLight(0xdfe9ff, 0x3a3630, 0.45); scene.add(hemi);
  const sun = new THREE.DirectionalLight(0xffe9cf, 2.6); scene.add(sun); scene.add(sun.target);
  sun.castShadow = true;
  sun.shadow.mapSize.setScalar(coarse ? 1024 : 2048);
  // the sun does not move, so the shadow map is drawn again only when the model changes, not on every frame
  sun.shadow.autoUpdate = false;
  sun.shadow.needsUpdate = true;
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
  const halfX = (size.x * k) / 2, halfZ = (size.z * k) / 2;
  const radius = Math.hypot(size.x, size.y, size.z) * k * 0.5;
  const target = new THREE.Vector3(0, H * 0.42, 0);
  // the shadow covers the whole building and nothing more. The sun comes in over a long side and from the street end
  sun.target.position.copy(target);
  sun.position.copy(target).add(new THREE.Vector3(6, 9, -7).normalize().multiplyScalar(radius * 2.2));
  const sc = sun.shadow.camera; sc.left = -radius * 1.15; sc.right = radius * 1.15; sc.top = radius * 1.15; sc.bottom = -radius * 1.15; sc.near = 0.1; sc.far = radius * 4.6; sc.updateProjectionMatrix();

  // one part is one Revit instance. A part with several finishes arrives as a group of meshes, one per finish
  const parts: Part[] = [];
  const meshes: THREE.Mesh[] = [];
  root.traverse((o) => {
    if (typeof o.userData.d !== "string") return;
    const part: Part = { d: o.userData.d as Disc, c: String(o.userData.c), t: String(o.userData.t), l: String(o.userData.l ?? ""), f: Number(o.userData.f ?? 0), node: o, meshes: [] };
    o.traverse((m) => {
      if (!(m as THREE.Mesh).isMesh) return;
      const mesh = m as THREE.Mesh;
      mesh.userData.part = part;
      mesh.userData.cls = (mesh.material as THREE.Material).name || "white";
      mesh.receiveShadow = true;
      mesh.castShadow = mesh.userData.cls !== "glass";
      part.meshes.push(mesh); meshes.push(mesh);
    });
    parts.push(part);
  });
  const partOf = (m: THREE.Object3D) => m.userData.part as Part;
  const counts: Record<string, number> = {};
  const perCategory: Record<string, number> = {};
  parts.forEach((p) => { counts[p.d] = (counts[p.d] || 0) + 1; perCategory[p.c] = (perCategory[p.c] || 0) + 1; });
  opts.onCounts?.(counts, parts.length);

  // level heights written by the builder: [name, floor group, metres above the base]
  let levels: [string, number, number][] = [];
  try { levels = JSON.parse(String(root.userData.levels ?? "[]")); } catch { levels = []; }
  const topFloor = Math.max(0, ...parts.filter((p) => p.f < 3).map((p) => p.f));
  const topLevel = levels.filter((l) => l[1] === topFloor).sort((a, b) => b[2] - a[2])[0];

  // ---------- materials ----------
  const allMats = new Set<THREE.Material>();
  const reg = <T extends THREE.Material>(m: T): T => { m.side = THREE.DoubleSide; m.shadowSide = THREE.DoubleSide; m.clipShadows = true; allMats.add(m); return m; };
  // plan cut: a little above the floor of the top storey, so its rooms, doors and fittings all read
  const clip = new THREE.Plane(new THREE.Vector3(0, -1, 0), topLevel ? (topLevel[2] + 1.25) * k : H * 0.8);
  // the section slider: one upright plane that travels through the house
  const sectionPlane = new THREE.Plane(new THREE.Vector3(-1, 0, 0), halfX);
  const hidden = reg(new THREE.MeshBasicMaterial({ colorWrite: false, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 }));
  const clay = reg(new THREE.MeshStandardMaterial({ color: 0xd8d3c9, roughness: 1, metalness: 0, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 }));
  const bim: Record<string, THREE.Material> = {};
  DISCS.forEach((d) => {
    bim[d] = reg(d === "architecture"
      ? new THREE.MeshStandardMaterial({ color: DISC_COLOR[d], roughness: 1, transparent: true, opacity: 0.1, depthWrite: false })
      : new THREE.MeshStandardMaterial({ color: DISC_COLOR[d], roughness: 0.6, emissive: DISC_COLOR[d], emissiveIntensity: 0.25 }));
  });
  // Finishes use the texture maps from the studio's rendered scenes (see tools/extract-textures.py).
  // The web model carries no UVs, so each map is laid on by box projection in world space:
  // the face's direction picks the plane, and real sizes set how often the map repeats.
  const texLoader = new THREE.TextureLoader();
  const texCache: Record<string, THREE.Texture> = {};
  const loadTex = (name: string) => {
    if (texCache[name]) return texCache[name];
    const t = texLoader.load(`/media/tex/${name}.webp`, () => kick());
    t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
    return (texCache[name] = t);
  };
  // desat pulls a map toward grey (the deck boards are orange, white oak is not); upright turns boards to run up the wall
  const boxed = (map: THREE.Texture, tileMetres: number, gain: number, roughness: number, tint = 0xffffff, desat = 0, upright = false) => {
    const mat = new THREE.MeshStandardMaterial({ color: tint, roughness, metalness: 0 });
    const scale = 1 / (tileMetres * k);
    mat.onBeforeCompile = (sh) => {
      sh.uniforms.boxMap = { value: map }; sh.uniforms.boxScale = { value: scale }; sh.uniforms.boxGain = { value: gain }; sh.uniforms.boxDesat = { value: desat };
      sh.vertexShader = sh.vertexShader
        .replace("#include <common>", "#include <common>\nvarying vec3 vBoxP; varying vec3 vBoxN;")
        .replace("#include <project_vertex>", "#include <project_vertex>\nvBoxP = (modelMatrix * vec4(transformed, 1.0)).xyz; vBoxN = normalize(mat3(modelMatrix) * objectNormal);");
      sh.fragmentShader = sh.fragmentShader
        .replace("#include <common>", "#include <common>\nuniform sampler2D boxMap; uniform float boxScale; uniform float boxGain; uniform float boxDesat; varying vec3 vBoxP; varying vec3 vBoxN;")
        .replace("#include <map_fragment>", `#include <map_fragment>\nvec3 bn = abs(normalize(vBoxN)); vec2 buv = bn.y > 0.5 ? vBoxP.xz : (bn.x > bn.z ? vBoxP.zy : vBoxP.xy);${upright ? " if (bn.y <= 0.5) buv = buv.yx;" : ""} vec3 btex = texture2D(boxMap, buv * boxScale).rgb; btex = mix(btex, vec3(dot(btex, vec3(0.3, 0.59, 0.11))), boxDesat); diffuseColor.rgb *= btex * boxGain;`);
    };
    mat.customProgramCacheKey = () => (upright ? "boxup" : "box");
    return mat;
  };
  const std = (color: number, roughness = 0.85, metalness = 0) => new THREE.MeshStandardMaterial({ color, roughness, metalness });
  // one finish per class the builder wrote into the model: white plaster and stucco, black trim,
  // white oak joinery and floors, clear glass, tile, stone, porcelain and stainless fittings
  const finish: Record<string, THREE.Material> = {
    glass: new THREE.MeshStandardMaterial({ color: 0xbcd3dc, roughness: 0.06, metalness: 0.25, transparent: true, opacity: 0.26, depthWrite: false, envMapIntensity: 1.8 }),
    black: std(0x1b1c1f, 0.45, 0.55),
    metal: std(0xcdd0d4, 0.28, 0.85),
    brass: std(0xc8a468, 0.32, 0.85),
    white: boxed(loadTex("stucco"), 3, 1.1, 0.92),               // smooth painted plaster indoors
    stucco: boxed(loadTex("plaster"), 2.5, 1.06, 0.95),          // rougher white render outside
    siding: boxed(loadTex("siding"), 1.6, 1.25, 0.78, 0xffffff, 0, true),
    oak: boxed(loadTex("deck"), 1.5, 2.1, 0.6, 0xf0e4d0, 0.78),
    woodfloor: boxed(loadTex("deck"), 2.4, 1.9, 0.55, 0xe6d6bc, 0.72),
    timber: boxed(loadTex("deck"), 1.2, 1.8, 0.85, 0xeedcb8, 0.55),
    tile: std(0xd6d3cc, 0.3),
    stone: std(0xf0efeb, 0.25),
    porcelain: std(0xf6f6f4, 0.18),
    concrete: boxed(loadTex("concrete"), 3, 0.95, 0.92),
    ground: boxed(loadTex("concrete"), 3, 0.72, 0.95),
    roof: std(0xe4e4e1, 0.85),
    fabric: std(0xe6e0d4, 0.95),
  };
  Object.values(finish).forEach(reg);
  const finishFor = (m: THREE.Mesh) => finish[m.userData.cls as string] ?? finish.white;
  const highlight = reg(new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.55, roughness: 0.4 }));
  // while one part is being inspected the rest of the building turns to faint glass around it
  const ghost = reg(new THREE.MeshStandardMaterial({ color: 0x9aa0ad, roughness: 1, transparent: true, opacity: 0.035, depthWrite: false }));
  const picked = reg(new THREE.MeshStandardMaterial({ color: 0xefa11f, emissive: 0xefa11f, emissiveIntensity: 0.35, roughness: 0.55 }));
  const copyOf = (mat: THREE.Material) => { const c = mat.clone(); c.onBeforeCompile = mat.onBeforeCompile; c.customProgramCacheKey = mat.customProgramCacheKey; return reg(c); };
  const glowCache = new Map<string, THREE.Material>();
  const glow = (mat: THREE.Material) => {
    let out = glowCache.get(mat.uuid);
    if (!out) { const c = copyOf(mat) as THREE.MeshStandardMaterial; c.emissive = new THREE.Color(0xefa11f); c.emissiveIntensity = 0.3; c.transparent = false; c.opacity = 1; c.depthWrite = true; out = c; glowCache.set(mat.uuid, out); }
    return out;
  };

  // Revit models often have two surfaces in exactly the same plane (a wall and its tile, a slab and its
  // finish). Drawn as is they flicker. Each category is pushed back by its own tiny amount.
  const ORDER = ["Plumbing fixtures", "Pipe accessories", "Specialty equipment", "Electrical fixtures", "Electrical equipment", "Mechanical equipment", "Duct accessories",
    "Furniture", "Casework", "Generic models", "Windows", "Curtain walls", "Doors", "Railings", "Stairs", "Structural columns", "Structural framing",
    "Fascias", "Walls", "Roofs", "Ceilings", "Floors", "Site"];
  const layerCache = new Map<string, THREE.Material>();
  const layered = (mat: THREE.Material, m: THREE.Mesh) => {
    if (mat === hidden) return mat;
    // tile and stone sit in front of the wall or floor they are laid on
    const cls = m.userData.cls as string;
    const i = Math.max(0, ORDER.indexOf(partOf(m).c)) - (cls === "tile" || cls === "stone" ? 0.5 : 0);
    const key = mat.uuid + ":" + i;
    let out = layerCache.get(key);
    // a constant nudge only: a slope based one lets interiors show through roofs seen at a low angle
    if (!out) { out = copyOf(mat); out.polygonOffset = true; out.polygonOffsetFactor = 1; out.polygonOffsetUnits = 1 + i * 3; layerCache.set(key, out); }
    return out;
  };

  // ---------- cut away: roof off, one floor at a time, and a travelling section ----------
  const cut: CutState = { roof: false, floor: -1, section: 0, axis: 0 };
  let stage = -1;
  const cutLive = () => stage >= 2 && stage <= 4;
  const cutShows = (f: number, ceiling: boolean) => {
    if (!cutLive()) return true;
    if (cut.floor >= 0 && f > cut.floor) return false;
    if (cut.roof && f === 3) return false;
    // a ceiling is the lid of its own floor: it goes when that floor is the one being looked into
    if (ceiling && (cut.roof || cut.floor >= 0) && f >= (cut.floor >= 0 ? cut.floor : topFloor)) return false;
    return true;
  };
  const sectionLive = () => cutLive() && cut.section > 0.005;
  function placeSection() {
    // along the length (axis 0) the plane starts at one long side wall and travels across the width;
    // across (axis 1) it starts at the street end and travels down the length
    const half = cut.axis === 0 ? halfX : halfZ;
    sectionPlane.normal.set(cut.axis === 0 ? -1 : 0, 0, cut.axis === 0 ? 0 : 1);
    sectionPlane.constant = half * 1.02 - cut.section * half * 2 * 0.96;
  }

  // ---------- edge drawings: one line object per discipline and floor, built a little at a time ----------
  const lineMat: Record<string, THREE.LineBasicMaterial> = {};
  const lineSets: { d: Disc; f: number; ceiling: boolean; obj: THREE.LineSegments }[] = [];
  const edgeCache = new Map<string, THREE.BufferGeometry>();
  const inv = new THREE.Matrix4().copy(root.matrixWorld).invert();
  async function buildEdges() {
    const acc = new Map<string, { d: Disc; f: number; ceiling: boolean; pts: number[] }>();
    const v = new THREE.Vector3();
    const local = new THREE.Matrix4();
    let last = performance.now();
    for (const m of meshes) {
      const p = partOf(m);
      const ceiling = p.c === "Ceilings";
      const key = `${p.d}:${p.f}:${ceiling ? 1 : 0}`;
      let set = acc.get(key);
      if (!set) { set = { d: p.d, f: p.f, ceiling, pts: [] }; acc.set(key, set); }
      let eg = edgeCache.get(m.geometry.uuid);
      if (!eg) { eg = new THREE.EdgesGeometry(m.geometry, 32); edgeCache.set(m.geometry.uuid, eg); }
      local.multiplyMatrices(inv, m.matrixWorld);
      const pos = eg.getAttribute("position");
      const out = set.pts;
      for (let i = 0; i < pos.count; i++) { v.fromBufferAttribute(pos, i).applyMatrix4(local); out.push(v.x, v.y, v.z); }
      if (performance.now() - last > 10) { await new Promise((r) => setTimeout(r, 0)); last = performance.now(); }
    }
    edgeCache.forEach((g) => g.dispose()); edgeCache.clear();
    DISCS.forEach((d) => { lineMat[d] = reg(new THREE.LineBasicMaterial({ color: 0xf5f5f7, transparent: true, opacity: 0 })); });
    acc.forEach((set) => {
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.Float32BufferAttribute(set.pts, 3));
      const obj = new THREE.LineSegments(g, lineMat[set.d]);
      obj.visible = false;
      root.add(obj);
      lineSets.push({ d: set.d, f: set.f, ceiling: set.ceiling, obj });
    });
  }

  // ---------- stage logic ----------
  const discOn: Record<string, boolean> = {};
  DISCS.forEach((d) => (discOn[d] = true));
  const lineTarget: Record<string, number> = {};
  let hovered: Part | null = null;
  let selected: Part | null = null;
  const planes: THREE.Plane[] = [];

  function paint() {
    const s = stage;
    for (const m of meshes) {
      const p = partOf(m);
      const shell = p.d === "architecture" || p.d === "structure";
      let mat: THREE.Material = hidden, vis = true;
      if (s === 0) { vis = shell; mat = hidden; }
      else if (s === 1) { mat = hidden; }
      else if (s === 2) { mat = clay; }
      else if (s === 3) { vis = discOn[p.d]; mat = bim[p.d]; }
      else { mat = finishFor(m); }
      vis = vis && cutShows(p.f, p.c === "Ceilings");
      m.visible = vis;
      if (selected && vis && p !== selected) m.material = ghost;
      else if (p === selected) { m.visible = true; m.material = s === 4 ? glow(mat) : picked; }
      else m.material = p === hovered && s === 3 ? highlight : s === 3 ? mat : layered(mat, m);
    }
    planes.length = 0;
    if (s === 1) planes.push(clip);
    if (sectionLive()) { placeSection(); planes.push(sectionPlane); }
    const shared = planes.slice();
    allMats.forEach((m) => { m.clippingPlanes = shared; });
    DISCS.forEach((d) => {
      const shell = d === "architecture" || d === "structure";
      const lm = lineMat[d]; if (!lm) return;
      let o = 0, col = 0xf5f5f7;
      if (s === 0) o = shell ? 0.9 : 0;
      else if (s === 1) { o = shell ? 0.95 : 0.8; col = shell ? 0xf5f5f7 : 0xefa11f; }
      else if (s === 2) { o = 0.26; col = 0x1a1a1a; }
      else if (s === 3) { o = d === "architecture" && discOn[d] ? 0.3 : 0; }
      if (selected && s >= 2) { o = shell ? 0.2 : 0; col = 0xf5f5f7; }
      lm.color.setHex(col);
      lineTarget[d] = o;
    });
    lineSets.forEach((set) => { set.obj.visible = (lineTarget[set.d] > 0 || lineMat[set.d].opacity > 0) && cutShows(set.f, set.ceiling); });
    sun.intensity = s === 3 ? 1.2 : 2.6;
    sun.castShadow = (s === 2 || s === 4) && !selected;
    sun.shadow.needsUpdate = true;
    // the clay model is lit harder from one side so its form reads; finishes get softer, fuller light
    scene.environmentIntensity = s === 2 ? 0.22 : 0.55;
    hemi.intensity = s === 2 ? 0.25 : 0.45;
    if (s === 2) sun.intensity = 3.1;
    // opened up, the rooms need more light from all round than a closed house does
    if (cutLive() && (cut.roof || cut.floor >= 0 || sectionLive())) { scene.environmentIntensity += 0.25; hemi.intensity += 0.2; }
  }

  // ---------- camera ----------
  const phone = () => canvas.clientWidth < 760;
  const viewFor = (i: number): View => (phone() ? VIEWS_PHONE : VIEWS)[Math.max(0, i)];
  const cur = { ...viewFor(0) };
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
    // and a little to the right, clear of the controls and the heading on the left (a selected part stays
    // in the middle: its call out is drawn from the centre)
    if (w >= 760) camera.setViewOffset(w, h, w >= 1000 && !selected ? -Math.round(w * 0.15) : 0, Math.round(h * 0.13), w, h);
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
  // where the camera should stand for the current stage and cut
  function restView() {
    const v = { ...viewFor(stage) };
    if (cutLive() && !selected) {
      if (sectionLive()) {
        // face the cut: from the side that has been taken away
        v.yaw = cut.axis === 0 ? 68 : 162; v.pitch = 13; v.dist = cut.axis === 0 ? (phone() ? 1.1 : 1.3) : (phone() ? 0.8 : 1.0);
      } else if (cut.roof || cut.floor >= 0) {
        // look down into the rooms
        v.pitch = phone() ? 50 : 46; v.dist *= phone() ? 1.1 : 1.32;
      }
    }
    Object.assign(goal, v);
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
      else if (lm.opacity !== (lineTarget[d] ?? 0)) {
        lm.opacity = lineTarget[d] ?? 0;
        if (lm.opacity === 0) lineSets.forEach((set) => { if (set.d === d) set.obj.visible = false; });
        moving = true;
      }
    });
    // a slow breath of rotation while the section is on screen
    if (!reduce && visible && !dragging && !selected && stage !== 1 && stage !== 5) { sway = Math.sin(t / 5200) * 5; moving = true; } else sway *= 0.9;
    // nothing is drawn until the first stage is set: the raw model must not flash while the line drawings build
    if ((moving || dirty) && stage >= 0) {
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
      const p = hitAt(e.clientX, e.clientY);
      select(p === selected ? null : p);
    }
  };
  canvas.addEventListener("pointerup", end);
  canvas.addEventListener("pointercancel", () => { dragging = false; });
  canvas.addEventListener("pointerleave", () => { if (!coarse) setHover(null, 0, 0); });

  // ---------- picking ----------
  const ray = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  let pickQueued = false, px = 0, py = 0;
  function queuePick(x: number, y: number) { px = x; py = y; if (pickQueued) return; pickQueued = true; requestAnimationFrame(() => { pickQueued = false; pick(px, py); }); }
  function setHover(p: Part | null, x: number, y: number) {
    canvas.style.cursor = p ? "pointer" : "";
    if (stage !== 3 || selected) { if (hovered) { hovered = null; paint(); kick(); opts.onPick?.(null, 0, 0); } return; }
    if (hovered !== p) {
      if (hovered) { const old = hovered; old.meshes.forEach((m) => (m.material = bim[old.d])); }
      hovered = p;
      if (p) p.meshes.forEach((m) => (m.material = highlight));
      kick();
    }
    opts.onPick?.(p ? { d: p.d, c: p.c, t: p.t, l: p.l } : null, x, y);
  }
  function hitAt(x: number, y: number): Part | null {
    const r = canvas.getBoundingClientRect();
    ndc.set(((x - r.left) / r.width) * 2 - 1, -((y - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    let hits = ray.intersectObjects(meshes.filter((m) => m.visible), false);
    // what the section has sliced away cannot be clicked
    if (sectionLive()) hits = hits.filter((h) => sectionPlane.distanceToPoint(h.point) >= 0);
    // glass and the see through shell should not block what is behind them
    const solid = (h: THREE.Intersection) => {
      const p = partOf(h.object);
      if (p === selected) return true;
      if (selected) return false;
      if (stage === 3) return p.d !== "architecture";
      return !(stage === 4 && h.object.userData.cls === "glass" && p.c !== "Windows" && p.c !== "Curtain walls" && p.c !== "Doors");
    };
    const hit = hits.find(solid) ?? hits[0];
    return hit ? partOf(hit.object) : null;
  }
  function pick(x: number, y: number) {
    const r = canvas.getBoundingClientRect();
    setHover(hitAt(x, y), x - r.left, y - r.top);
  }

  // ---------- inspect one part: the camera flies to it and the rest fades to glass ----------
  const bb = new THREE.Box3(), sph = new THREE.Sphere(), v3 = new THREE.Vector3();
  function select(p: Part | null) {
    if (p === selected) return;
    if (hovered) { hovered = null; opts.onPick?.(null, 0, 0); }
    selected = p;
    if (p) {
      bb.setFromObject(p.node); bb.getBoundingSphere(sph);
      tGoal.copy(sph.center);
      const vF = THREE.MathUtils.degToRad(camera.fov), hF = 2 * Math.atan(Math.tan(vF / 2) * camera.aspect);
      const d = Math.max((sph.radius * 2.3) / Math.sin(Math.min(vF, hF) / 2), fitDist * 0.16);
      goal.dist = Math.min(1, d / fitDist);
      goal.pitch = 24;
      // look at it from the outside of the building, on the side the part is on
      cur.yaw += userYaw; userYaw = userYawGoal = 0;
      const hx = sph.center.x - target.x, hz = sph.center.z - target.z;
      goal.yaw = Math.hypot(hx, hz) > radius * 0.1 ? THREE.MathUtils.radToDeg(Math.atan2(hx, hz)) : cur.yaw;
      const sz = bb.getSize(v3);
      // a wall, a door or a window is a thin slab: face its broad side, a little off square, never its edge
      if (Math.min(sz.x, sz.z) < Math.max(sz.x, sz.z) * 0.35) {
        goal.yaw = sz.x < sz.z ? (hx >= 0 ? 68 : -68) : (hz >= 0 ? 22 : 158);
      }
      const dims = [sz.x / k, sz.z / k, sz.y / k].map((n) => Math.round(n * 100) / 100) as [number, number, number];
      opts.onSelect?.({ d: p.d, c: p.c, t: p.t, l: p.l, size: dims, same: perCategory[p.c] ?? 1 });
    } else {
      tGoal.copy(target);
      restView();
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
  let wasPhone = phone();
  const ro = new ResizeObserver(() => { fit(); if (phone() !== wasPhone) { wasPhone = phone(); if (!selected && stage >= 0) restView(); } kick(); });
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
      restView();
      userYawGoal = 0;
      paint();
      fit();
      kick();
    },
    setDiscipline(d, on) { discOn[d] = on; if (selected && selected.d === d && !on) select(null); else if (stage === 3) { paint(); kick(); } },
    setCut(c) {
      const before = { ...cut };
      Object.assign(cut, c);
      cut.section = Math.max(0, Math.min(1, cut.section));
      // dragging the slider only moves the plane: nothing is rebuilt
      const sliding = before.section > 0.005 && cut.section > 0.005 && before.axis === cut.axis && before.roof === cut.roof && before.floor === cut.floor;
      if (sliding) { placeSection(); sun.shadow.needsUpdate = true; kick(); return; }
      // a part the cut has just hidden cannot stay selected
      if (selected && !cutShows(selected.f, selected.c === "Ceilings")) { select(null); return; }
      if (!selected) { restView(); userYawGoal = 0; }
      paint();
      kick();
    },
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
