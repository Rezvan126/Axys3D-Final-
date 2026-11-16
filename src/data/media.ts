// Pictures named in the editable data files (src/content/), turned into what an <img> needs.
// The data stores only the full size path, e.g. "/media/uploads/kitchen.webp". By convention the small
// copy sits next to it as "<name>-sm.webp" (tools/process-media.mjs writes both). Width and height are
// read from the WebP header at build time, so a new upload never needs its size typed in.
import { existsSync, openSync, readSync, closeSync } from "node:fs";
import { join } from "node:path";

const PUBLIC = join(process.cwd(), "public");
const onDisk = (url: string) => join(PUBLIC, ...url.replace(/^\//, "").split("/"));

// width and height from a WebP header (VP8, VP8L or VP8X); null for other files or when missing
export function webpSize(url: string): { w: number; h: number } | null {
  try {
    const fd = openSync(onDisk(url), "r");
    const b = Buffer.alloc(30);
    readSync(fd, b, 0, 30, 0);
    closeSync(fd);
    if (b.toString("ascii", 0, 4) !== "RIFF" || b.toString("ascii", 8, 12) !== "WEBP") return null;
    const kind = b.toString("ascii", 12, 16);
    if (kind === "VP8X") return { w: 1 + b.readUIntLE(24, 3), h: 1 + b.readUIntLE(27, 3) };
    if (kind === "VP8 ") return { w: b.readUInt16LE(26) & 0x3fff, h: b.readUInt16LE(28) & 0x3fff };
    if (kind === "VP8L") return { w: 1 + (((b[22] & 0x3f) << 8) | b[21]), h: 1 + (((b[24] & 0x0f) << 10) | (b[23] << 2) | ((b[22] & 0xc0) >> 6)) };
  } catch { /* missing or unreadable */ }
  return null;
}

// "/media/x.webp" -> "/media/x-sm.webp" (also for an upload that is still a .jpg or .png)
export const smallOf = (url: string) => url.replace(/\.[a-z0-9]+$/i, "-sm.webp");
// a film's cover picture sits next to it: "/media/x.mp4" -> "/media/x.webp"
export const posterOf = (url: string) => url.replace(/\.[a-z0-9]+$/i, ".webp");

export interface Pic { src: string; sm: string | null; w: number; h: number; smW: number; srcset?: string }

// `size` lets a data file keep the size a page has always declared (optional, never needed for new pictures)
export function pic(src: string, size?: { width?: number; height?: number }, fallback = { w: 1920, h: 1080 }): Pic {
  const real = webpSize(src) ?? fallback;
  const w = size?.width ?? real.w;
  const h = size?.height ?? real.h;
  const smUrl = smallOf(src);
  const small = smUrl !== src ? webpSize(smUrl) : null;
  return {
    src,
    sm: small ? smUrl : null,
    w,
    h,
    smW: small?.w ?? 0,
    srcset: small ? `${smUrl} ${small.w}w, ${src} ${w}w` : undefined,
  };
}

export const exists = (url: string) => existsSync(onDisk(url));
