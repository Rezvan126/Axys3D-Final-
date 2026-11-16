#!/usr/bin/env node
// PROCESS MEDIA: turns raw uploads into the web files the site uses. Runs on every publish (GitHub Actions,
// .github/workflows/deploy.yml) and by hand: `node tools/process-media.mjs` (add --dry to only list the work).
//
// What it does, for files the owner uploads in Pages CMS (public/media/uploads/, any size):
//   Pictures (jpg, jpeg, png, tif, tiff, webp, avif)
//     -> <name>.webp at most 1920 wide and <name>-sm.webp 800 wide, next to the upload.
//        A jpg or png is replaced by the .webp: every data file that named it is rewritten to the .webp,
//        and the original is moved to assets-src/media-originals/ (git ignored; it stays in git history).
//   Films (mp4, mov, m4v, webm)
//     -> <name>.mp4 in web settings matching the existing clips (H.264 High, yuv420p, at most 1280 wide or
//        1280 tall, at most 30 fps, about 1 Mbit/s, fast start, no metadata, sound kept only if present)
//        plus a cover picture <name>.webp and <name>-sm.webp from a frame half a second in.
//   Virtual tour rooms (a room's "image" in src/data/tours/<slug>.json, set in the editor)
//     -> public/media/tours/<slug>/<room>.webp (4096 by 2048) and <room>-sm.webp (2048 by 1024), the same
//        files and quality as tools/make-tour.sh, and the room's "image" is pointed at the new file.
//        The picture must be a 360 degree (equirectangular) image, twice as wide as it is high.
//
// Already processed files are skipped: tools/media-cache.json (committed) keeps a fingerprint of every file
// this script wrote. Replace a file under the same name and it is processed again.
// Needs: node 22+, sharp (devDependency), ffmpeg and ffprobe on the PATH (only when there are films to do).
import { createHash } from "node:crypto";
import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const PUBLIC = path.join(ROOT, "public");
const UPLOADS = path.join(PUBLIC, "media", "uploads");
const ORIGINALS = path.join(ROOT, "assets-src", "media-originals");
const CACHE_FILE = path.join(ROOT, "tools", "media-cache.json");
const DATA_DIRS = [path.join(ROOT, "src", "content"), path.join(ROOT, "src", "data", "tours")];
const TOURS = path.join(ROOT, "src", "data", "tours");
const DRY = process.argv.includes("--dry");

const IMAGE = new Set([".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".avif"]);
const VIDEO = new Set([".mp4", ".mov", ".m4v", ".webm"]);
const PIC = { full: 1920, sm: 800, q: 82, qSm: 78 };
const PANO = { full: 4096, sm: 2048, q: 90, qSm: 88 };
const FILM = { box: 1280, fps: 30, crf: 25, maxrate: "1600k", bufsize: "3200k", posterAt: 0.5, okRate: 1_700_000 };

// ---------- small helpers ----------
const log = (...a) => console.log("[media]", ...a);
const posix = (p) => p.split(path.sep).join("/");
const url = (abs) => "/" + posix(path.relative(PUBLIC, abs));                 // public file -> site address
const fromUrl = (u) => path.join(PUBLIC, ...u.replace(/^\//, "").split("/"));  // site address -> public file
const sha1 = (abs) => createHash("sha1").update(fs.readFileSync(abs)).digest("hex");
const isSmall = (f) => /-sm\.webp$/i.test(f);
const walk = (dir) => (fs.existsSync(dir) ? fs.readdirSync(dir, { withFileTypes: true }) : []).flatMap((e) => {
  const p = path.join(dir, e.name);
  return e.isDirectory() ? walk(p) : [p];
});

const cache = fs.existsSync(CACHE_FILE) ? JSON.parse(fs.readFileSync(CACHE_FILE, "utf8")) : { files: {} };
cache.files ??= {};
const done = (abs) => cache.files[url(abs)]?.hash === sha1(abs);
const remember = (abs, from, kind) => { if (!DRY) cache.files[url(abs)] = { hash: sha1(abs), from, kind }; };
let changed = 0;
const claimed = new Set(); // uploads already used as a tour room picture
const problems = [];

// every data file that may name a picture or film
const dataFiles = () => DATA_DIRS.flatMap(walk).filter((f) => /\.(json|md|ya?ml)$/i.test(f));
// point every mention of one file at another (plain text, so formatting and other keys stay as they are)
function rewriteRefs(fromU, toU) {
  if (fromU === toU) return;
  for (const f of dataFiles()) {
    const t = fs.readFileSync(f, "utf8");
    if (!t.includes(fromU)) continue;
    log(`  ${posix(path.relative(ROOT, f))}: ${fromU} -> ${toU}`);
    if (!DRY) fs.writeFileSync(f, t.split(fromU).join(toU));
  }
}
// keep the owner's original out of the published folder (it is still in git history)
function retire(abs) {
  const dest = path.join(ORIGINALS, path.relative(UPLOADS, abs));
  log(`  original moved to ${posix(path.relative(ROOT, dest))}`);
  if (DRY) return;
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.rmSync(dest, { force: true });
  fs.renameSync(abs, dest);
}
// keep a copy of a file that is about to be replaced in place
function keep(abs) {
  const dest = path.join(ORIGINALS, path.relative(UPLOADS, abs));
  if (DRY) return;
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(abs, dest);
}
const tmpOf = (abs) => abs.replace(/(\.[^.]+)$/, ".tmp$1");

// ---------- pictures ----------
// `box`: the longest side at most this many pixels, never enlarged (an upright picture gets the same limit on its
// height, so its small copy really is smaller). `height`: an exact size instead (360 degree pictures).
async function webp(input, out, box, quality, height) {
  const img = sharp(input, { limitInputPixels: false }).rotate(); // turn phone photos the right way up; metadata is dropped
  const size = height ? { width: box, height, fit: "fill" } : { width: box, height: box, fit: "inside", withoutEnlargement: true };
  const buf = await img.resize(size).webp({ quality, effort: 5 }).toBuffer();
  fs.writeFileSync(out, buf);
}

async function picture(abs) {
  const ext = path.extname(abs).toLowerCase();
  const base = abs.slice(0, -ext.length);
  const full = `${base}.webp`, sm = `${base}-sm.webp`;
  if (ext === ".webp" && done(full) && fs.existsSync(sm)) return;
  log(`picture ${url(abs)} -> ${url(full)} + ${path.basename(sm)}`);
  changed++;
  if (DRY) return;
  const input = fs.readFileSync(abs); // read first: the output may replace the input
  if (ext === ".webp") keep(abs);
  await webp(input, sm, PIC.sm, PIC.qSm);
  await webp(input, tmpOf(full), PIC.full, PIC.q);
  fs.renameSync(tmpOf(full), full);
  remember(full, path.basename(abs), "picture");
  if (ext !== ".webp") { rewriteRefs(url(abs), url(full)); retire(abs); }
}

// ---------- films ----------
let ff = null;
function haveFfmpeg() {
  if (ff !== null) return ff;
  ff = spawnSync("ffmpeg", ["-version"]).status === 0 && spawnSync("ffprobe", ["-version"]).status === 0;
  return ff;
}
function probe(abs) {
  const out = execFileSync("ffprobe", ["-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate:format=bit_rate,duration", "-of", "json", abs], { encoding: "utf8" });
  const j = JSON.parse(out);
  const v = j.streams.find((s) => s.codec_type === "video");
  const [n, d] = (v?.r_frame_rate ?? "30/1").split("/").map(Number);
  return { codec: v?.codec_name, w: v?.width ?? 0, h: v?.height ?? 0, fps: d ? n / d : 30, audio: j.streams.some((s) => s.codec_type === "audio"), rate: Number(j.format?.bit_rate ?? 0), duration: Number(j.format?.duration ?? 0) };
}
function ffmpeg(args) {
  const r = spawnSync("ffmpeg", ["-hide_banner", "-loglevel", "error", "-y", ...args], { stdio: ["ignore", "inherit", "inherit"] });
  if (r.status !== 0) throw new Error(`ffmpeg failed: ${args.join(" ")}`);
}

async function film(abs) {
  const ext = path.extname(abs).toLowerCase();
  const base = abs.slice(0, -ext.length);
  const out = `${base}.mp4`, poster = `${base}.webp`, posterSm = `${base}-sm.webp`;
  if (ext === ".mp4" && done(out) && fs.existsSync(poster) && fs.existsSync(posterSm)) return;
  if (!haveFfmpeg()) { problems.push(`${url(abs)}: ffmpeg is not installed, film left as it is`); return; }
  const info = probe(abs);
  // already a light web file: only move the index to the front and drop the metadata
  const light = info.codec === "h264" && Math.max(info.w, info.h) <= FILM.box && info.fps <= FILM.fps + 0.5 && info.rate > 0 && info.rate <= FILM.okRate;
  log(`film ${url(abs)} (${info.w}x${info.h}, ${(info.rate / 1e6).toFixed(1)} Mbit/s${info.audio ? ", with sound" : ""}) -> ${url(out)}${light ? " (already light: fast start only)" : ""} + cover`);
  changed++;
  if (DRY) return;
  const tmp = tmpOf(out);
  const audio = info.audio ? ["-c:a", "aac", "-b:a", "96k", "-ac", "2"] : ["-an"];
  if (light) {
    ffmpeg(["-i", abs, "-map", "0:v:0", ...(info.audio ? ["-map", "0:a:0"] : []), "-c:v", "copy", ...(info.audio ? ["-c:a", "copy"] : ["-an"]), "-map_metadata", "-1", "-movflags", "+faststart", tmp]);
  } else {
    // longest side at most FILM.box, even sizes (H.264 needs them), never enlarged
    const scale = `scale='if(gt(iw,ih),trunc(min(${FILM.box},iw)/2)*2,-2)':'if(gt(iw,ih),-2,trunc(min(${FILM.box},ih)/2)*2)':flags=lanczos`;
    const fps = info.fps > FILM.fps + 0.5 ? [`fps=${FILM.fps}`] : [];
    ffmpeg(["-i", abs, "-map", "0:v:0", ...(info.audio ? ["-map", "0:a:0"] : []), "-vf", [scale, ...fps, "format=yuv420p"].join(","),
      "-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf", String(FILM.crf), "-maxrate", FILM.maxrate, "-bufsize", FILM.bufsize,
      ...audio, "-map_metadata", "-1", "-movflags", "+faststart", tmp]);
  }
  // the cover picture: a frame half a second in (the very first frame is often black)
  const frame = `${base}.cover.tmp.png`;
  const at = info.duration > 1 ? FILM.posterAt : 0;
  ffmpeg(["-ss", String(at), "-i", tmp, "-frames:v", "1", frame]);
  const input = fs.readFileSync(frame);
  fs.rmSync(frame);
  retire(abs); // for an .mp4 the web file then takes its place
  fs.renameSync(tmp, out);
  await webp(input, poster, 1600, PIC.q);
  await webp(input, posterSm, PIC.sm, PIC.qSm);
  remember(out, path.basename(abs), "film");
  remember(poster, path.basename(out), "cover");
  if (ext !== ".mp4") rewriteRefs(url(abs), url(out));
}

// ---------- virtual tour rooms ----------
async function tours() {
  for (const f of walk(TOURS).filter((p) => p.endsWith(".json"))) {
    let t;
    try { t = JSON.parse(fs.readFileSync(f, "utf8")); } catch { continue; } // a file another tool is still writing
    if (typeof t.slug !== "string" || !/^[a-z0-9-]+$/.test(t.slug) || !Array.isArray(t.rooms)) continue;
    for (const r of t.rooms) {
      if (typeof r?.image !== "string" || !r.image || typeof r.slug !== "string") continue;
      const target = `/media/tours/${t.slug}/${r.slug}.webp`;
      const out = fromUrl(target), sm = fromUrl(target.replace(/\.webp$/, "-sm.webp"));
      const src = fromUrl(r.image);
      if (r.image === target && fs.existsSync(out) && done(out) && fs.existsSync(sm)) continue;
      if (!fs.existsSync(src)) { problems.push(`${t.slug}/${r.slug}: picture ${r.image} not found`); continue; }
      const meta = await sharp(src, { limitInputPixels: false }).metadata();
      const ratio = (meta.width ?? 0) / (meta.height ?? 1);
      if (Math.abs(ratio - 2) > 0.04) { problems.push(`${t.slug}/${r.slug}: ${r.image} is ${meta.width}x${meta.height}; a 360 degree room picture must be twice as wide as it is high (4096x2048 or larger). Left as it was.`); continue; }
      if ((meta.width ?? 0) < PANO.full) log(`  note: ${r.image} is only ${meta.width} wide; 4096 or more looks sharper`);
      log(`tour room ${t.slug}/${r.slug}: ${r.image} -> ${target} + ${path.basename(sm)}`);
      claimed.add(src);
      changed++;
      if (DRY) continue;
      const input = fs.readFileSync(src);
      const w = Math.min(PANO.full, meta.width ?? PANO.full);
      fs.mkdirSync(path.dirname(out), { recursive: true });
      await webp(input, tmpOf(out), w, PANO.q, Math.round(w / 2));
      fs.renameSync(tmpOf(out), out);
      await webp(input, sm, Math.round(w / 2), PANO.qSm, Math.round(w / 4));
      remember(out, path.basename(src), "tour-room");
      if (r.image !== target) {
        // point this room at its new picture, touching nothing else in the file
        const text = fs.readFileSync(f, "utf8");
        fs.writeFileSync(f, text.split(JSON.stringify(r.image)).join(JSON.stringify(target)));
        if (src.startsWith(UPLOADS + path.sep)) retire(src);
      }
    }
  }
}

// ---------- run ----------
await tours();
for (const abs of walk(UPLOADS)) {
  const name = path.basename(abs), ext = path.extname(abs).toLowerCase();
  if (claimed.has(abs) || name.startsWith(".") || isSmall(name) || /\.tmp\./.test(name) || !fs.existsSync(abs)) continue;
  try {
    if (VIDEO.has(ext)) await film(abs);
    else if (IMAGE.has(ext)) {
      // a cover this script made for a film sits next to the film: leave it
      if (ext === ".webp" && cache.files[url(abs)]?.kind === "cover" && done(abs)) continue;
      await picture(abs);
    }
  } catch (e) {
    problems.push(`${url(abs)}: ${e.message}`);
  }
}
// forget files that are gone
for (const u of Object.keys(cache.files)) if (!fs.existsSync(fromUrl(u))) delete cache.files[u];
if (!DRY) {
  const sorted = Object.fromEntries(Object.entries(cache.files).sort(([a], [b]) => a.localeCompare(b)));
  fs.writeFileSync(CACHE_FILE, JSON.stringify({ note: "Written by tools/process-media.mjs: fingerprints of processed media. Do not edit.", files: sorted }, null, 2) + "\n");
}
log(changed ? `${changed} file(s) ${DRY ? "to process" : "processed"}` : "nothing new");
for (const p of problems) console.warn(`[media] WARNING ${p}`);
// a broken upload must not block the rest of the site from going live; the warning shows in the Actions log
