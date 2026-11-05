// Owner rule: no dashes anywhere a visitor can read them (hyphens, en dashes, em dashes).
// Runs after every build over the finished HTML. Only visible text and readable attributes
// are changed (alt, title, aria-label, placeholder, page titles and descriptions);
// links, class names, scripts and styles are never touched.
import { readdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

// Prefixes that read as one word without the hyphen ("re-test" -> "retest").
const JOIN = new Set(["re", "pre", "co", "e", "multi", "non", "sub", "fly", "take", "mark", "set", "check", "sign", "hand", "add"]);
const JOIN_WORDS = { "take-off": "takeoff", "mark-ups": "markups", "mark-up": "markup", "fly-through": "flythrough", "fly-throughs": "flythroughs", "set-up": "setup", "sign-off": "sign off", "e-bike": "ebike", "e-bikes": "ebikes" };

export function stripDashes(s) {
  if (!/[-–—‒―]/.test(s)) return s;
  let t = s;
  // numbered steps: "01 — Validate" -> "01. Validate"
  t = t.replace(/^(\s*\d{1,2})\s*[—–]\s+/, "$1. ");
  // ranges between numbers: "2–3", "100-400", "Day 2 – 3" -> "2 to 3"
  t = t.replace(/(\d)\s*[–—-]\s*(\d)/g, "$1 to $2");
  // em/en dash or spaced hyphen used as a break inside a sentence
  t = t.replace(/\s+[—–‒―-]\s+(?=\S)/g, (m, off) => {
    const before = t.slice(0, off);
    // "Title — subtitle" with no other punctuation reads best with a colon
    return /[.,;:!?]/.test(before) ? ", " : ": ";
  });
  t = t.replace(/(\S)[—―](\S)/g, "$1, $2"); // "revisions—not"
  t = t.replace(/\s*[—–‒―]\s*$/g, "").replace(/^\s*[—–‒―]\s*/g, "");
  // whole words with a known one-word form
  for (const [k, v] of Object.entries(JOIN_WORDS)) {
    t = t.replace(new RegExp(`\\b${k}\\b`, "gi"), (m) => (m[0] === m[0].toUpperCase() ? v[0].toUpperCase() + v.slice(1) : v));
  }
  // other hyphenated words: join short prefixes, otherwise use a space
  t = t.replace(/\b([A-Za-z0-9]+)-(?=[A-Za-z0-9])/g, (m, w) => (JOIN.has(w.toLowerCase()) ? w : w + " "));
  // anything left (stray dashes)
  t = t.replace(/\s*[—–‒―]\s*/g, " ").replace(/(\s)-(\s)/g, "$1").replace(/ {2,}/g, " ");
  return t;
}

const ENTITY = { "&mdash;": "—", "&ndash;": "–", "&#8212;": "—", "&#8211;": "–", "&#x2014;": "—", "&#x2013;": "–" };
const READABLE_ATTR = /(\s(?:alt|title|aria-label|placeholder)=")([^"]*)(")/g;
const META_ATTR = /(<meta\b[^>]*\b(?:name|property)="(?:description|og:title|og:description|twitter:title|twitter:description)"[^>]*\bcontent=")([^"]*)(")/g;
const META_ATTR_REV = /(<meta\b[^>]*\bcontent=")([^"]*)("[^>]*\b(?:name|property)="(?:description|og:title|og:description|twitter:title|twitter:description)")/g;

export function processHtml(html) {
  for (const [e, c] of Object.entries(ENTITY)) html = html.split(e).join(c);
  // split into protected blocks and the rest
  const parts = html.split(/(<script\b[\s\S]*?<\/script>|<style\b[\s\S]*?<\/style>|<pre\b[\s\S]*?<\/pre>|<code\b[\s\S]*?<\/code>|<textarea\b[\s\S]*?<\/textarea>)/i);
  return parts
    .map((part, i) => {
      if (i % 2 === 1) return part;
      return part.replace(/(<[^>]*>)|([^<]+)/g, (m, tag, text) => {
        if (text) return stripDashes(text);
        return tag
          .replace(READABLE_ATTR, (_, a, v, b) => a + stripDashes(v) + b)
          .replace(META_ATTR, (_, a, v, b) => a + stripDashes(v) + b)
          .replace(META_ATTR_REV, (_, a, v, b) => a + stripDashes(v) + b);
      });
    })
    .join("");
}

async function walk(dir) {
  const out = [];
  for (const e of await readdir(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) out.push(...(await walk(p)));
    else if (e.name.endsWith(".html")) out.push(p);
  }
  return out;
}

export default function noDashes() {
  return {
    name: "axys-no-dashes",
    hooks: {
      "astro:build:done": async ({ dir, logger }) => {
        const root = fileURLToPath(dir);
        const files = await walk(root);
        for (const f of files) {
          const src = await readFile(f, "utf8");
          const out = processHtml(src);
          if (out !== src) await writeFile(f, out);
        }
        logger.info(`removed visible dashes in ${files.length} pages`);
      },
    },
  };
}
