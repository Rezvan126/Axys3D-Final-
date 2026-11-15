# Axys3D design brief

Rules for every change to this site. Follow them exactly; ask the owner before deviating.
Rewritten 15 Nov 2026 when the owner asked for a new look ("Apple kind of touch", new colours and fonts allowed, real 3D from our own models, light to load, perfect on every screen).

## Owner preferences

- **Do exactly what was asked, completely.** Removing a page means removing every link to it. The Services overview page stays removed; "Services" in the menu is a list of the eight service pages, not a page of its own.
- **Real work only.** Every picture, film and model comes from the studio's own portfolio. No stock photos, no invented clients, team members, testimonials, logos or numbers, no "demonstration" case studies.
- **Never show architect, client or site information.** No addresses, names, permit numbers or title blocks. Model element names are cleaned by `tools/build-model-navis.py` (and `tools/build-model.py` for the earlier house), which also checks the finished file and prints `PRIVACY OK` or the words it found.
- **No decoration nobody asked for.** No grid line backgrounds, faint background art, pulsing dots or endless decorative loops.
- **No old school effects.** No card flips, bounces, glows, gradient text or busy hover tricks. One quiet fade and rise on scroll, once.
- **Never let text overlap text.** Tooltips open above their trigger.
- **Alignment matters.** Items in a row share tops, bottoms and heights. Measure, do not eyeball.
- **No dashes in text a visitor reads** (hyphens, en and em dashes). `src/integrations/no-dashes.mjs` strips them at build time; write without them anyway.
- **Light to load.** See the performance budget below.

## Visual system (`src/styles/ax.css`)

Third look, 15 Nov 2026, with a flat pass the same day. The owner rejected black, gold and Geist ("looks Claude generated"), then said the paper and ink version looked like an article or a newspaper, then said the rounded glass version was not user friendly and that the phone version "looks like an app". The rule now: it must feel like a product page on a website. Not a document, not an app.

- **Never:** cream paper backgrounds, ruled tables and hairline column grids, small typewriter or monospace labels, "Fig. 01" style captions, square newspaper blocks. Also never: pill buttons, a floating rounded header, liquid glass, frosted panels, a pill inside a pill, circular arrow or play badges, sideways carousels on phones, rounded frames around full width sections.
- **Colour:** soft light ground `#f1f2f4`, white surfaces, ink `#0b0c0f`, greys `#3c3f47` and `#666a74`. The only colour is the amber from the logo, `#efa11f`. Sections that show 3D, film or the closing action are ink black (`.ax-dark`) and run edge to edge with square corners. The light and dark rhythm of the page stays.
- **Type:** Big Shoulders (tall condensed capitals) for H1, H2 and H3 so headings and sub headings speak in one voice; Hanken Grotesk for reading, labels, buttons and H4. The line under a heading (`.ax-lead`) is large and semi bold. Self hosted through Fontsource. No other fonts. On phones (600px and under): H1 40px, H2 30px, lead 17px, and no heading runs to four lines.
- **Radius scale (tokens in `ax.css`, never a raw number):** buttons 10px (`--ax-r-btn`), small buttons 8px (`--ax-r-btn-sm`), cards and panels 12px (`--ax-r-card`), pictures and film 8px (`--ax-r-media`), inputs 8px (`--ax-r-input`), chips and tags 6px (`--ax-r-chip`), full width sections 0. A full circle is allowed only for small status dots and tick marks.
- **Glass and blur:** none, with one exception. The small panels that float over the live 3D model (`.xp-views`, `.xp-call-card`, `.xp-layers`, `.xp-cut`, `.xp-pick` in `Explorer.astro`) use `rgba(14,16,20,.82)` with a 12px blur. Nothing else on the site uses `backdrop-filter`.
- **Buttons:** 50px high (small 44px). `.ax-btn--gold` is the one primary action per screen: flat amber, ink text, no glow. Over film or pictures the second action is `.ax-btn--glass`, which is now a plain 1px white outline (the class name is historic). Other secondary actions are `.ax-link`: words followed by a plain arrow, no badge.
- **One label for the primary action, sitewide: "Start a project".** Never "Get a quote", "Send your brief", "Start a project like this" and so on. Secondary links keep their own wording. The contact form's own submit button says "Send brief".
- **Glyphs, not badges:** arrows on links and cards, the play triangle on film tiles and the chevron on rows that open are plain glyphs with no circle behind them. Tap areas stay 44px.
- **Small labels:** `.ax-eyebrow` is plain condensed capitals in the headline face (no chip, no dot), amber on dark sections. Use one only when it adds something the heading does not say; never repeat the page name or the button under it. The home page uses none.
- **Header (`Navbar.astro`):** a flat bar attached to the top edge, full width, 60px high (56px on phones), square, solid, no blur. White with a 1px hairline over light sections; solid `#0e1014` with light words over dark sections (`.is-dark`). The current page is underlined in amber. Items: Services (opens a plain list of the eight services on hover, click, or with the arrow keys; Escape closes it), Work, Industries, Insights, About, Hire us, Contact, then the "Start a project" button. The button is left out on the contact page and hidden while the phone menu is open.
- **Phone menu:** a plain solid white panel under the bar. Text rows 52px high at 20px, hairline dividers, Services opens in place, one "Start a project" button at the bottom.
- **Logo in the header is interactive:** it tilts toward the pointer, the amber dot is pulled toward the cursor and springs back, and the dot jumps on click or tap. `Logo3D.astro` is the full 3D logo in the home page closing section (left out on phones to keep that section short).
- **Home page:** opens with the studio film edge to edge, the four figures in one plain row split by hairlines at its foot (visible without scrolling on a phone). "Built around how you work" uses underlined text tabs; the services named in it are plain text links. Services are picture cards on wide screens and a plain list on phones (small picture, name, arrow, 72px rows). The steps are four tiles with large numerals on wide screens (the one you reach turns black) and a compact numbered list on phones. Recent work shows three films on phones, then "See all work". Inner pages open with a picture or film panel (`.pg-hero-media`, `.pg-panel`) under the heading.
- **Service pages on phones:** "You get back" comes first with a "Start a project" button under it; "You send", "How it is checked", "When it helps" and "How we work together" are closed rows that open on a tap (`.sv-fold`). The clash table shows four rows and a "Show all" button.
- **Interactive building:** in the 3D model, BIM and Materials stages a click flies the camera to that part, fades the rest and opens the call out (`.xp-call`: category, type, size, level, how many in the model). The same three stages have the "Look inside" controls (`.xp-cut`): floors (All, Ground, Second, Third), roof on or off, and a slice that travels lengthways or across the house. Wide screens show them as a small panel top left (two columns on short screens); between 761 and 999px and on phones they stay closed behind one "Look inside" button, and on phones they open as a solid sheet over the words, never over the model. Every control is 44px high. The last stage plays the film clips with a Front, Wide, Detail switch. On phones the pinned walk is a quarter of a screen per stage, the stage bars can be tapped, and "Skip the walkthrough" is a full width outline button.
- **Motion:** `data-ax` fade and rise, once. Reduced motion respected everywhere.

## The 3D building (`src/components/Explorer.astro`, `src/scripts/explorer.ts`)

One real project, exported from our own Revit file, taken through six stages by scrolling: sketch, drawings, 3D model, BIM detail, materials, final render.

- Site version 1.1: the model is a three floor infill house with its full interior (joinery, stairs, fixtures, furniture), because the owner asked for "more detailed model ... so someone can view everything in it".
- Source model: Revit, exported through Navisworks as FBX, which keeps the real tree (level, category, family, type, instance, one mesh per material). `tools/build-model-navis.py` (run with Blender) reads discipline, category, type and level from that tree, strips identifying text, folds the export's materials into 17 finish classes and writes `public/models/house.glb` (Draco, about 1.7 MB, 700 parts, 271,000 triangles) plus `src/data/house-model.json`. The page reads its counts and floor names from that JSON; never type them in.
- The earlier house (`tools/build-model.py`, `public/models/adu.glb`) is kept: the service page stills and the clash report were made from it.
- Three.js and the model load only when the section nears the screen. The canvas draws only when something changes and pauses off screen. The shadow map is redrawn only when the model changes.
- BIM stage shows real element data (discipline, category, type, level) and has layer switches for the disciplines the model has parts in.
- Materials stage: one finish per class (white plaster and stucco, black trim, white oak joinery and floors, clear glass, tile, stone, porcelain, stainless), using the box projected maps in `public/media/tex`.
- The final stage's still and film clips are set in one `render` object at the top of `Explorer.astro`.
- No WebGL, reduced motion or data saver: the section becomes a plain list with the final render. The page must always read correctly without the canvas.
- Horizontal drag turns the model; vertical touch still scrolls the page.
- `tools/render-shots.py` renders the service page stills from the same model.

## Site structure

Menu: Services (a list of the eight service pages) · Work (`/visuals/`) · Industries · Insights · About · Hire us · Contact, then the "Start a project" button.

- Home: hero with a real render, figures, the 3D building, eight services as a list, recent work, how it works, questions, closing action.
- Work: one project in depth plus films from the portfolio. No client or site details.
- Case study pages were removed because they were fictional. Add real ones only with the client's permission.
- Redirects: `/work`, `/services`, `/process` in `astro.config.mjs`; old `/work/...` addresses in `public/.htaccess`.
- Page files and internal links are lowercase (Linux hosting).

## Figures (one source: `src/data/site.ts`)

172 projects delivered · 43+ studio partners · 7 days brief to first render · 4.8/5 rating · 8 services.

## Performance budget

- Home page before scrolling: one hero image (about 240 KB, 77 KB on phones), three small font files, under 60 KB of CSS and script.
- Films: short silent clips under 1 MB each, fetched only when played. Stills are WebP with a small version for phones.
- 3D: model about 1.7 MB (ceiling 5 MB), engine about 160 KB compressed, fetched on demand.
- Every image has width, height and lazy loading (except the hero).

## Checks before every publish

1. `npx astro build` passes.
2. No console errors; no sideways scroll at 390px.
3. Text overlap scan on all pages.
4. All on site links return 200.
5. Look at every changed section on desktop, tablet and phone.
6. Contrast 4.5:1 (3:1 large text), nothing under 12px, 44px tap areas, visible keyboard focus, reduced motion respected.
7. Run the `axys-ui-qa` and `axys-client-reviewer` agents (`.claude/agents/`). Anything they score under 8 gets fixed before launch.

## Source assets

Raw files from the owner live in `assets-src/` (ignored by git, never published). Portfolio films: `E:\Coraxys\Axys3D\Portfolio Videos`. Web versions are generated into `public/media/` with ffmpeg.

## Shareable preview

`npx astro build && python tools/make-preview.py <folder>` writes a copy with relative addresses for the Artifact host (entry page `entry.html`). Published at https://claude.ai/artifact/WWvVZyjS2mAqJwDmCArq7T.

## Virtual tour (`src/components/Tour.astro`, `src/scripts/tour.ts`)

A 360 degree room to room tour on the Work page, rendered from the studio's own Revit model. The project is called "Split level residence" and nothing else.

- **Placement:** its own ink black section straight after the Work page opening, before the project gallery, so the first thing in the showcase is something the visitor can move. One line of honest text, then "Start a project".
- **Nothing loads until "Start the tour" is pressed.** Before that the section is one poster picture. The press fetches three.js, the viewer and the first panorama. Only one panorama is held in memory at a time.
- **"Start the tour" is the plain white button, not amber.** The amber "Start a project" under the tour stays the one primary action.
- **Glass:** the room label, the full screen button, the hint and the hotspots sit over the live view, so they use the same glass as the 3D building panels (`rgba(14,16,20,.82)`, 12px blur). The room list is plain text buttons under the view, current room underlined in amber like the header.
- **Hotspots** are real buttons with the room name and a plain chevron (no circle), 44px high. Their directions come from the real standpoint positions in `src/data/tour.json`; never type angles into the component.
- **Phone:** the view is upright (4 by 5), the label and full screen button sit in the top corners, the hint at the bottom edge, the room list under the view. Nothing covers the middle. Sideways drag turns the view; up and down still scrolls the page (full screen frees both directions). Phones, data saver and weak cards get the 2048 pixel pictures.
- **Keyboard:** arrow keys turn, plus and minus zoom, Tab reaches every hotspot and room button; a hotspot that is out of view turns the view to itself when it takes focus. The wheel zooms only after the view has been clicked or is full screen, so it never traps page scrolling.
- **Reduced motion:** no opening drift, no inertia, rooms change at once.
- **Staging is declared:** the Revit model has joinery, kitchen, fixtures and beds but no loose furniture. All furniture, lamps, plants, art and accessories in the tour are virtual staging from free BlenderKit assets, placed by `tools/tour-dress.py` (list in `HANDOFF.md`); the neighbours and trees outside are set dressing. The owner allows virtual staging; do not describe the staging as part of the client's design.
- **Materials:** owner's standing rule, "for better materials use BlenderKit". Free assets only, fetched with `tools/tour-bkit.py`.
- **Privacy:** file names, JSON, alt text and labels carry no client, architect, address or person. `tools/tour-scene.py` and `tools/tour-dress.py` scrub and check names and print `PRIVACY OK`.
