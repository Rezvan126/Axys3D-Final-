# Axys3D design brief

Rules for every change to this site. Follow these exactly; ask before deviating.

## Owner preferences (learned the hard way)

- **Do exactly what was asked, completely.** "Remove a page" means remove the page *and* every menu/footer/button link to it.
- **No decoration nobody asked for.** No grid lines in backgrounds, no faint background art, no blinking/pulsing dots, no stock photos, no code-drawn "3D" placeholders.
- **Real work only.** Visuals must come from the owner's own portfolio (Google Drive "Portfolio" folder), never stock or generated stand-ins.
- **Never let text overlap other text.** Tooltips open *above* their trigger.
- **Alignment matters.** Cards in a row/column share tops, bottoms and heights. Check by measuring, not by eye.
- **Self-review before publishing**, don't wait for the owner to find issues.
- **No dashes anywhere visitors can read** (hyphens, en and em dashes), even where grammar would use one. Enforced automatically at build time by `src/integrations/no-dashes.mjs`; write new text without dashes anyway.
- **Keep the theme.** When asked to "improve" a section, keep colours, fonts and dark look unless told otherwise.

## Visual system

- **Background:** near-black `#050506`. Hero gradient (keep exactly): brown glow `rgba(143,100,68,.28)` at 73% 50% + brown wash `rgba(91,59,39,.30)` to bottom-right.
- **Bronze palette:** `#5b3b27` (brown), `#8f6444` (brown-hi / accent words), `#b8946f` (brown-lt / labels), `#d9b48c` / `#e3c8a8` (sand).
- **Font (one family, two weights):** Barlow, chosen for the AEC world (DIN / technical-lettering roots, like drawing title blocks). 400 for body text, 600 for headings, numbers, labels and buttons. Build hierarchy from size and weight only. Self-hosted via `@fontsource/barlow` (imported in `src/styles/global.css`, preloaded in `SEO.astro`) so every visitor gets the same files. No other fonts, no other weights.
- **Heading scale (global.css tokens):** H1 40–60px, H2 30–48px, H3 19–22px, H4 16px, all Barlow 600. Pages must not override sizes.
- **Header:** single floating glass bar; current page marked by the liquid-glass pill (spring motion, `Navbar.astro`). CTA = gold bevelled rim, pearl face, brown text.

## Site structure

Menu: Home · Industries · Process · Insights · Visuals · About · Hire us.

- **Removed:** Services overview page (services live on the home page `#services`; the 8 `/services/<slug>` detail pages remain). Work page (merged into Visuals). Redirects `/work → /visuals`, `/services → /#services` in `astro.config.mjs`.
- **Page files are lowercase** (`src/pages/about.astro` …) and every internal link is lowercase. Hosting is Linux: case matters.
- **Insights** = articles + case studies hub with filters; 3 SEO guides in `src/content/insights/`.
- **Hire us** (`/hire`) = Upwork/Fiverr hiring, rates, payments. Data in `src/data/hire.ts`.

## Figures (keep consistent everywhere)

43+ studio partners · 172 projects delivered · 7 days brief to first render · 4.8/5 rating · 8 services.
Booking month: current month until the 15th, then next month (computed automatically).

## Checks before every publish

1. `npx astro build` passes.
2. No JS errors; no horizontal scroll at 390px phone width.
3. Text-overlap scan on all pages (ignore hidden/collapsed text).
4. All on-site links return 200.
5. Screenshot every section changed, desktop and phone, and actually look at it.
6. UI/UX Pro Max pre-delivery checklist: text contrast 4.5:1 (3:1 for large text), no text under 12px, 44px tap areas on phones, visible keyboard focus (bronze ring), reduced motion respected.

## Design tools installed in this project

- `.claude/skills/ui-ux-pro-max/`: UI/UX Pro Max design knowledge base (styles, palettes, font pairings, UX rules). Search with `python3 .claude/skills/ui-ux-pro-max/scripts/search.py "<query>" --domain <ux|style|typography|color|product>`. Treat results as suggestions; this file wins.
- `.claude/skills/motion/` and `.claude/agents/motion-reviewer.md`: Motion AI Kit (animation best practices). The `motion` library is installed (`import { animate, inView, scroll } from "motion"`).
- Motion's hosted helper servers (MCP) are not set up: `npx motion-ai` is interactive and must be run in a real terminal.
