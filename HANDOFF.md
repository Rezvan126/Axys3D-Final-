# Handoff: where the project stands (15 Nov 2026)

Read `DESIGN.md` first. Older owner feedback is in `docs/chat-history.md`.

## What the site is now

- **Look:** light ground, white rounded surfaces, rounded ink black panels for 3D and film, one amber accent from the logo. Big Shoulders for headings, Hanken Grotesk for text. Two earlier looks (black and gold with Geist, then paper and ink) were rejected by the owner.
- **Home page** (`src/pages/index.astro`), in the order a client needs it:
  1. Looping film hero (still for reduced motion or data saving), headline, the one amber action with a line of reassurance, four figures in a glass bar.
  2. "Built around how you work": the visitor picks architects, engineers, developers or agencies and sees their own problem, what they get, the services they use and a quote button. The choice is remembered. Data: `audiences` in `src/data/site.ts`.
  3. Eight services as picture cards (a swipe row on phones).
  4. The interactive building (`Explorer.astro`, `src/scripts/explorer.ts`): six scroll stages; click any part in the 3D model, BIM and Materials stages to fly in and read a call out; the last stage plays three film clips and asks for the project.
  5. Four steps; the card you have scrolled to turns black. "Send your brief" sits under them.
  6. Recent work (film tiles with a player that offers the next step), questions, closing action with the 3D logo.
- **Navigation:** flat bar attached to the top edge (no glass, no rounding), Services list, interactive logo, turns ink over black sections. Flat pass of 15 Nov 2026: radius scale, edge to edge dark sections, one button label, shorter phone layouts. See `DESIGN.md`.
- **Work page** (`/visuals/`): opens with the exterior film; every picture and drawing opens large.
- **Rule from the owner:** every element needs a reason for where it sits, and the site must feel built for the visiting client so they click through to "Start a project".

## 3D model and media pipeline (`tools/`)

- `build-model.py`: Revit FBX to the web model (`public/models/adu.glb`). Classifies and scrubs names, checks face orientation, paints glass and frames per face (the export has no materials), Draco compresses.
- `extract-textures.py`: pulls the packed texture maps from the finished Blender scene into `public/media/tex/` (siding, roof, stucco, plaster, deck, concrete, grass). The web model has no UVs, so `explorer.ts` lays them on by box projection.
- `render-final-shot.py`, `render-clip.py` (wide, detail, garden), `render-portfolio.py`: Cycles shots and stills from `assets-src/gellert/scene.blend`.
- `make-hero.sh` (looping hero film, wide and upright), `make-clips.sh` (the three clips in the last 3D stage), `make-portfolio.sh` (stills adu-9 to adu-12 and the exterior film).
- `make-preview.py <folder>`: relative path copy of `dist/` for the shareable preview. Publish `entry.html` from it.
- The owner will send more Revit, STL and Blender files and wants the same stills and clips made from each.

## Known gaps

- The site still leans on one project. More projects, people on the About page, a real titled drawing sheet, prices or turnaround times, and a source for the 4.8/5 rating are what the client-persona review asked for next.
- The scroll driven parts were tested in a desktop browser at phone size, not on a real phone.
- Shell note for whoever edits by script on this machine: heredocs in Git Bash turned `\\b` into a backspace character more than once. Write patch scripts to a file instead.

## Waiting on the owner

1. Upwork and Fiverr profile links and real rates (`src/data/hire.ts`). Buttons go to Contact until then.
2. Social profile links (`src/data/social.ts`).
3. Confirm the domain `https://axys3d.com` (`astro.config.mjs`).
4. More projects that may be shown, and with what details.
5. Montalvo project: the Revit file needs exporting (FBX or IFC) before it can become a second 3D model; the renders mentioned were not in the shared folder.
6. `public/mail/mail-config.php` holds the mail settings and is blocked by `.htaccess`; move real credentials out of the site folder on the host if possible. It is never included in the preview.
7. The project is not a git repository in this folder. Nothing has been committed, pushed or deployed.

## Useful commands

- `npx astro dev --background` then `npx astro dev stop` (if styles look stale: stop, delete `node_modules/.vite` and `.astro`, start again)
- `npx astro check` and `npx astro build`
- Rebuild the 3D model: `blender -b --factory-startup --python tools/build-model.py -- assets-src/gellert/model.fbx public/models/adu.glb assets-src/gellert/model-report.json`
- Agents in `.claude/agents/`: `axys-competitor-research`, `axys-ui-designer`, `axys-ui-qa`, `axys-client-reviewer`.

## Permit sheets and clash report (added 15 Nov 2026)

- `src/components/Sheets.astro`: four real permit sheets (A104, A107, A108, MEP100) with a zoom viewer. Shown on the Revit and BIM service pages. Source: Drive folder `1v6GU6Nq13lQidYFjikaifGlHDobArpDQ`, "Complete Permit Ready Drawings, Revit Model.pdf", pages 4, 7, 8, 12. Title blocks were already blank; two site photos on A107 are masked. Images in `public/media/sheets/`.
- `src/components/ClashReport.astro`: a real clash test, structure against services, on the house model. Shown on the MEP and BIM pages. Data in `src/data/clash.json`, pictures in `public/media/clash/`.
- `tools/clash-test.py`: `blender -b -P tools/clash-test.py -- <model.fbx> <out dir>` writes clash.json and pictures. Reuses the naming rules in build-model.py.
- Revit versions: the owner said old and latest both. Stated in the Sheets note and in a home FAQ, with no year numbers.
- `tools/make-preview.py` now rewrites `data-full`, which fixes the picture viewer on the Work page in the shared preview.
- A stray folder `C:\assets-src` was created by an early run of the clash script. It holds only five test pictures and can be deleted by hand.
