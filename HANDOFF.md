# Handoff: where the project stands (15 Nov 2026)

Read `DESIGN.md` first. Older owner feedback is in `docs/chat-history.md`.

## What the site is now

- **Look:** light ground, white rounded surfaces, rounded ink black panels for 3D and film, one amber accent from the logo. Big Shoulders for headings, Hanken Grotesk for text. Two earlier looks (black and gold with Geist, then paper and ink) were rejected by the owner.
- **Home page** (`src/pages/index.astro`), in the order a client needs it:
  1. Looping film hero (still for reduced motion or data saving), headline, the one amber action with a line of reassurance, four figures in a glass bar.
  2. "Built around how you work": the visitor picks architects, engineers, developers or agencies and sees their own problem, what they get, the services they use and a quote button. The choice is remembered. Data: `audiences` in `src/data/site.ts`.
  3. Eight services as picture cards (a swipe row on phones).
  4. The interactive building (`Explorer.astro`, `src/scripts/explorer.ts`): six scroll stages; click any part in the 3D model, BIM and Materials stages to fly in and read a call out; "Look inside" in the same stages lifts the roof, shows one floor at a time or slices the house open; the last stage plays three film clips and asks for the project.
  5. Four steps; the card you have scrolled to turns black. "Send your brief" sits under them.
  6. Recent work (film tiles with a player that offers the next step), questions, closing action with the 3D logo.
- **Navigation:** flat bar attached to the top edge (no glass, no rounding), Services list, interactive logo, turns ink over black sections. Flat pass of 15 Nov 2026: radius scale, edge to edge dark sections, one button label, shorter phone layouts. See `DESIGN.md`.
- **Work page** (`/visuals/`): opens with the exterior film, then the virtual tours (`#tours`), the projects and the films; every picture and drawing opens large. Virtual tours are part of Work (owner, 16 Nov 2026): there is no Tours menu item.
- **Rule from the owner:** every element needs a reason for where it sits, and the site must feel built for the visiting client so they click through to "Start a project".

## 3D model and media pipeline (`tools/`)

- `build-model-navis.py` (site version 1.1): Navisworks FBX of the detailed house to `public/models/house.glb` and `src/data/house-model.json`. Uses the real model tree for discipline, category, type and level, joins each instance into one part, keeps 17 finish classes as shared materials, turns faces outward, thins only pieces over 12,000 triangles, scrubs names and checks the result. 700 parts, 270,666 triangles, 1.68 MB. `explorer.ts` reads the part data from the node extras (`d`, `c`, `t`, `l`, `f`), the finish class from each material name, and level heights from the scene extras.
- `build-model.py`: Revit FBX of the earlier house to `public/models/adu.glb` (still used by `render-shots.py`, `render-film.py` and `clash-test.py`). Classifies and scrubs names, checks face orientation, paints glass and frames per face (the export has no materials), Draco compresses.
- `extract-textures.py`: pulls the packed texture maps from the finished Blender scene into `public/media/tex/` (siding, roof, stucco, plaster, deck, concrete, grass). The web model has no UVs, so `explorer.ts` lays them on by box projection.
- `render-final-shot.py`, `render-clip.py` (wide, detail, garden), `render-portfolio.py`: Cycles shots and stills from `E:/Portfolios/ADU Residence/02 Scenes/scene.blend` (moved there 16 Nov 2026; stills in `03 Stills`, film frames in `04 Film`, the make scripts read those folders, override with `ADU_DIR`).
- `make-hero.sh` (looping hero film, wide and upright), `make-clips.sh` (the three clips in the last 3D stage), `make-portfolio.sh` (stills adu-9 to adu-12 and the exterior film).
- `make-preview.py <folder>`: relative path copy of `dist/` for the shareable preview. Publish `entry.html` from it.
- The owner will send more Revit, STL and Blender files and wants the same stills and clips made from each.

## Known gaps

- The site still leans on one project. More projects, people on the About page, a real titled drawing sheet, prices or turnaround times, and a source for the 4.8/5 rating are what the client-persona review asked for next.
- The scroll driven parts were tested in a desktop browser at phone size, not on a real phone.
- Interactive building, version 1.1: the last stage still plays the films of the earlier house (set in the `render` object at the top of `Explorer.astro`) until the new films are ready. `tools/make-preview.py` still renames only `adu.glb` and `logo.glb` for the shared preview and needs `house.glb` added. The export has no demolition group (the "02 Demo" node is a saved view), so nothing was dropped for that; phase is not in the export, level is shown instead. Frame rate was measured only on a fast desktop card (about 4 ms a frame, 940 draw calls), not on a mid range laptop or a real phone. On phones the model alone (1.68 MB) is over the 1.5 MB first view budget.
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
- Rebuild the 3D model: `blender -b --factory-startup --python tools/build-model-navis.py -- assets-src/amber/navis/amber.fbx public/models/house.glb src/data/house-model.json` (the last lines must read `PRIVACY OK` and `MODEL_OK`)
- Rebuild the earlier house: `blender -b --factory-startup --python tools/build-model.py -- "E:/Portfolios/ADU Residence/01 Source/model.fbx" public/models/adu.glb assets-src/gellert/model-report.json`
- Agents in `.claude/agents/`: `axys-competitor-research`, `axys-ui-designer`, `axys-ui-qa`, `axys-client-reviewer`.

## Permit sheets and clash report (added 15 Nov 2026)

- `src/components/Sheets.astro`: four real permit sheets (A104, A107, A108, MEP100) with a zoom viewer. Shown on the Revit and BIM service pages. Source: Drive folder `1v6GU6Nq13lQidYFjikaifGlHDobArpDQ`, "Complete Permit Ready Drawings, Revit Model.pdf", pages 4, 7, 8, 12. Title blocks were already blank; two site photos on A107 are masked. Images in `public/media/sheets/`.
- `src/components/ClashReport.astro`: a real clash test, structure against services, on the house model. Shown on the MEP and BIM pages. Data in `src/data/clash.json`, pictures in `public/media/clash/`.
- `tools/clash-test.py`: `blender -b -P tools/clash-test.py -- <model.fbx> <out dir>` writes clash.json and pictures. Reuses the naming rules in build-model.py.

## Amber house renders (added 15 Nov 2026)

New stills and clips of the white infill house from the owner's Blender scene, relit and re-shaded. Not wired into any page yet: nothing under `src/` was changed. The owner decides whether they replace the current renders.

- Source `assets-src/amber/scene.blend` is never written. `tools/amber-setup.py` builds the improved scene in memory and saves `assets-src/amber/scene-v2.blend` (Cycles, AgX, golden hour sky and sun, new plaster, black metal, glass, frosted glass, asphalt and pavement shaders, toned down grass, lights inside the rooms and at the door, the street carried on both ways, hill and trees around the modelled patch, copies of the two neighbours further along the street, a street tree and a low hedge row).
- `tools/amber-views.py`: the six still cameras. `tools/amber-stills.py`: final stills. `tools/amber-clip.py`: the three clips (hero push in, wide slide, detail drift), 120 frames each. `tools/amber-sheet.py`: test sheets and the comparison sheet. `tools/make-amber.sh`: grade and encode. `tools/amber-inspect.py` and `amber-probe*.py` are the fact finding scripts used on the original file.
- Outputs in `public/media/`: `amber-1.webp` to `amber-6.webp` (1920x1080) with `-sm` versions (800x450), in the order hero, low three quarter, entry and garage, upper windows, wide, from up the street; `amber-film-hero.mp4`, `amber-film-wide.mp4`, `amber-film-detail.mp4` (1280x536, 5 s, silent) each with a `.webp` poster.
- Raw renders: `assets-src/amber/renders/stills/` and `assets-src/amber/renders/film/<shot>/`; test rounds in `renders/test/`; comparison sheet `renders/contact.jpg`.
- Re-run (Git Bash, from the project root; give Blender absolute output folders, a relative one lands on the drive root):
  1. `"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" --disable-autoexec -b assets-src/amber/scene.blend -P tools/amber-setup.py -- save`
  2. `... -b assets-src/amber/scene-v2.blend -P tools/amber-stills.py -- E:/Axys3D-Final--main/assets-src/amber/renders/stills` (add `test` for 720x405 previews, add view names to render only those; existing finals are skipped, delete a file to redo it)
  3. `... -b assets-src/amber/scene-v2.blend -P tools/amber-clip.py -- E:/Axys3D-Final--main/assets-src/amber/renders/film/hero hero` (and `wide`, `detail`)
  4. `bash tools/make-amber.sh` then `python tools/amber-sheet.py contact`
- Privacy: object and image path names inside both .blend files still carry Revit type names and old folder paths with personal names. They never reach the renders, and the encode step strips metadata, but do not publish either .blend file.
- Things learned: instancing a whole neighbour collection stalls Cycles (nested grass scatter), so the street copies are linked object copies. Revit objects have origins far from their geometry, so test position by bounding box. The Nishita style sky needs film exposure near -3.7 here; at higher exposure AgX hides the over-exposure and every black turns brown.
- Revit versions: the owner said old and latest both. Stated in the Sheets note and in a home FAQ, with no year numbers.
- `tools/make-preview.py` now rewrites `data-full`, which fixes the picture viewer on the Work page in the shared preview.
- A stray folder `C:\assets-src` was created by an early run of the clash script. It holds only five test pictures and can be deleted by hand.

## Virtual tour, hillside house (added 16 Nov 2026; third pass the same night)

- **What:** a 360 degree, room to room tour of the split level residence, slug `hillside` in the tour library. Six standpoints: Entry, Living and dining, Kitchen, Primary bedroom, Primary bath, Back deck. Data `src/data/tours/hillside.json`, pictures `public/media/tours/hillside/` (see "Tour library").
- **Project files (owner's rule):** scenes and full resolution panoramas live in `E:\Portfolios\Split Level Hillside House\` (`02 Scenes\tour-base.blend`, `02 Scenes\tour.blend` with all textures packed, `05 Virtual Tour\<room>.png` and a copy of the JSON). That folder's `README.md` has the exact re-render commands. `assets-src/amber/tour/` keeps only logs and `bkit-assets.json`.
- **Pipeline:** `bash tools/make-tour.sh render` does everything (takes the GPU lock for the render step); without `render` it only grades and exports from the PNGs in the Portfolios folder.
  1. `tools/tour-scene.py`: Navisworks FBX to `tour-base.blend`. Same tree walk, drop list, name scrubbing and 17 finish classes as `build-model-navis.py`; undersides of floors and roofs painted as ceilings; 11 opening sized wall plugs left out; 110 warm ceiling lights placed by ray casting; lawn and street outside. Prints `PRIVACY OK` and `TOUR_SCENE_OK`.
  2. `tools/tour-dress.py`: `tour-base.blend` to `tour.blend`. BlenderKit materials laid on by world position with box projection at true size (the Revit meshes have no usable UVs; normal maps become bump from the height maps). BlenderKit staging as collection instances. Door leaves on the tour route removed (`e0432`, `e0808`, `e0811`, `e0820`, `e0806`, `e0814`, `e0831`, and `e0090` so the entry looks into a lit, furnished office). Third pass detail: 90 mm skirting on every interior wall face (454 boards), painted door casings, casings and sills on the punched windows (not on the angled street glazing or floor to ceiling units), switch and socket plates in every room, a trim ring and lit lens under every ceiling light, sheer curtains at the living, dining and bedroom glazing, near neutral glass, a glass shower screen with black profile on the bath pony wall, string lights and lanterns on the deck. Neighbouring houses, maples and birches outside; a free BlenderKit HDRI. Datablocks with an automatic ".NNN" suffix are renamed (`skirt_00315`) because the suffix can spell a banned number. Prints `PRIVACY OK` and `DRESS_OK`.
  3. `tools/tour-render.py`: modes `plan`, `test` (1024 by 512), `final` (4096 by 2048 or `TOUR_RES`, Cycles OptiX with denoising; `TOUR_TOTAL` seconds of sampling per room, default 330, spread over the 1024 pixel tiles because Cycles applies its time limit per tile), `at x y z` and `json` (merges rooms and hotspots into `src/data/tours/hillside.json` and keeps the library's own fields). Image maps: 2K for what sits close to the camera (floors, worktops, rugs, upholstery, bedding, tile), 1K for the rest, scaled in memory at render time. Per room exposure (`ev`) and per room sun (`sun`): the three back rooms are shot with a low warm sun behind the house so light reaches the deck. `TOUR_CPU=1` renders look tests on the processor while another job holds the GPU.
  4. `tools/make-tour.sh`: gentle grade, WebP at two sizes (quality 90 for 4096, 88 for the 2048 phone file), poster cut flat from the living room with ffmpeg `v360`, JSON, and a JSON copy into the Portfolios folder.
  5. `tools/tour-pack.py`: packs every external image into `tour.blend` (run after a rebuild).
  - BlenderKit: `tools/tour-bkit.py` searches and fetches headless with the owner's logged in add-on (`probe`, `batch "<type>:<words>" ...`, `get <asset_base_id> ...`). Free assets only: `is_free:true` is in every query and is checked again before each download. Every fetch is logged in `assets-src/amber/tour/bkit-assets.json`. `tools/tour-bkit-inspect.py -- <ids>` lists what each file holds.
  - Helpers: `tools/tour-probe.py`, `tools/tour-probe2.py`, `tools/tour-sheet.py`.
- **6144 test:** the living room at 6144 by 3072 is 731 KB at WebP quality 82 (the 4096 file is 600 KB at quality 90) and only marginally crisper at the same crop, so the tour stays at 4096.
- **Staging, said plainly:** the Revit model has no loose furniture. Everything movable in the pictures is virtual staging from free BlenderKit assets, plus a few plain shapes (coffee table, entry console, deck table, rug slabs, curtains are a BlenderKit parametric curtain). The neighbours, street trees and the view are set dressing. Walls, glazing, stairs, kitchen, joinery, bathroom fixtures and the vanity are the model. The bed in the primary bedroom replaces the model's own bed.
- **Left out after test renders:** second floor stair hall, third floor landing (closed doors all round), second bathroom (dark, with an odd boxed fixture in the model). The ground floor office is not a stop but is seen, dressed, through the open entry door.
- **Known limits:** on phones the view turns sideways only unless it is full screen, and iPhone Safari has no full screen for page elements. Not checked on a real phone.

## Tour library (added 16 Nov 2026)

Every finished tour is shown on the Work page in one section, `/visuals/#tours` (owner, 16 Nov 2026: "the virtual tours should go under the work section"). The featured tour (`hillside` by default, chosen in the editor as "Featured tour"; the first ready tour if its pictures are ever missing) sits inline; every other tour is a card under "More virtual tours." that opens its own viewer in place, just below the cards (script at the foot of `visuals.astro`; the card still links to the tour page when scripting is off). `/tours/<slug>/` stays as one page per tour for deep links, with "Work" as the active menu item and links back to `/visuals/#tours`. `/tours/` itself only forwards to `/visuals/#tours` (meta refresh, canonical `/visuals/`, noindex, left out of the sitemap). There is no Tours menu item; the footer's "Virtual tours" goes to `/visuals/#tours`.

**To add a project, drop two things in place and edit nothing else:**

1. Pictures in `public/media/tours/<slug>/`: `<room>.webp` (4096 by 2048) and `<room>-sm.webp` (2048 by 1024) for every room, plus `poster.webp` (1600 wide) and `poster-sm.webp` (800 wide).
2. Data in `src/data/tours/<slug>.json`: the shape `tools/tour-render.py json` writes (`title`, `note`, `size`, `small`, `rooms` with `slug`, `name`, `floor`, `yaw`, `pitch`, `spots`) plus `slug` (same as the folder, lowercase letters, digits and hyphens), `project` (the public name, never a client, architect or address), `summary` (one line for the card and page opening) and `rooms_count`. Optional: `poster_alt` (what the poster shows) and `order` (lower is listed first; default 100, then by name).
3. Run `npx astro build`. The page, the card, the sitemap entry and the preview copy appear by themselves.

How it works:

- `src/data/tours.ts` reads every JSON with `import.meta.glob` and lists a tour only when the data is complete and every picture above is on disk. Anything left out is named in the build log as `[tours] left out of the library: ...`, so a half rendered project never shows a broken card or page. Hotspots pointing at a room the tour lacks are dropped. Poster width and height are read from the WebP header.
- Picture paths are never in the JSON. The component puts the folder in one `data-base` attribute (already rewritten by `tools/make-preview.py`) and the viewer builds file names from it. No change to `make-preview.py` was needed; checked with the preview copy served locally: `/tours/`, a tour page and the Work page all start and load their panorama with status 200.
- `src/components/Tour.astro` props: `slug` (or `data` plus `base`), `id` (unique per page), `heading`, `level` (1 on a tour page), `lead`, `cta` (amber "Start a project", on by default), `links`, `eager`. Several tours can sit on one page; each loads three.js and its panorama only when its own "Start the tour" is pressed. Before that only the poster loads (the small one on phones), and phones get the `-sm` panoramas.
- Any button with `data-tour-open="<section id>" data-room="<room slug>"` opens that tour at that room. The tour page room list uses this.
- `src/components/TourCard.astro` is the library card (poster, rooms and floors, project name, summary).
- The old `src/data/tour.json` and `public/media/tour/` are gone (moved to `src/data/tours/hillside.json` and `public/media/tours/hillside/`). Run `tools/tour-render.py json` with the new path.

### BlenderKit assets used in the tour (all free; the Poly Haven ones and three Joris LM prints are CC0, the rest BlenderKit royalty free)

| Type | Name | Asset base id | Licence | Author | Where |
|---|---|---|---|---|---|
| material | Oak Wood Planks | 4e3b26b3-7538-40b6-bde4-edd581fb3c62 | CC0 | Poly Haven | all oak floors and stair treads |
| material | Oak Wood Natural Clean | d484a9ce-2084-4884-a6d0-41b11a8e29c2 | CC0 | Tomasz Bartkowiak-Ketzler | oak joinery, console, deck table |
| material | Painted Plaster Wall | 1886ea52-91f9-4091-8743-8e93bace40f3 | royalty free | chroma 3D | walls |
| material | Regular white marble tiles | 5898732b-2384-46a4-b646-06681b0334cf | royalty free | Adhe e | bath walls and floor, kitchen tile |
| material | Black matte metal | 14d8278b-9c10-4f5f-9611-89645f64d917 | royalty free | ydd 3D | window and door frames, rails |
| material | Wool Carpet | 15a270bf-cf3b-4611-bfdb-60551bd21ef0 | royalty free | Share Textures | rugs |
| hdr | Neighborhood Park Sunny Morning | 0a918314-7eed-4e93-a947-30c424f5ab60 | royalty free | EB Adventure Photoscans | sky and far horizon |
| model | Sofa WOWIN Ingrid | bec4cc4d-4d96-4ed3-98c2-cba0188296ca | royalty free | MNDV | living |
| model | Reni Lounge Chair | 6715a22e-4ac5-42c5-8c3f-c3a0d01366e6 | royalty free | Duy Ngo | living |
| model | Oslo Floor Lamp | 0318ccab-565c-4169-ad40-0001f537aba2 | royalty free | Duy Ngo | living |
| model | Indoor Plant Bird Of Paradise | c0835c81-78ef-45a3-be5c-edc543218ff4 | royalty free | Pandora Land | living |
| model | Stack of books | 87b81438-9883-4787-a86d-58135ec892a5 | royalty free | antoine f | living, entry |
| model | Vase with cotton flowers | 56f8cbf8-7765-489f-bf0d-2182195afa75 | royalty free | Mesk911 | living, entry, deck |
| model | Painting abstract procedural | 1ae164e0-8ea7-49fc-a9f3-bd0df870146b | royalty free | Matteo Pascale | dining wall |
| model | Modern minimal table set | aacf8c17-ebb3-479f-ba28-0ebb48212d46 | royalty free | Joris LM | dining |
| model | Beatrice Pendant Lamp | 1714f648-c401-4f56-bf1f-e4c136c03fe4 | royalty free | Duy Ngo | dining |
| model | Fiddle Leaf Fig Tree (Medium) | 86332944-a9a1-450a-b06c-8597a2d4546c | royalty free | Zulian Firmansyah | dining, deck planters |
| model | Waveform Pendant | 79d7030c-b2fc-4ff1-87e7-b69b8adb7c4c | royalty free | Fiq KM | kitchen island |
| model | Simple Fruit Bowl | 58c3f401-72f9-49f0-a9d2-07d21c4adcde | royalty free | cgi Moon | kitchen |
| model | Coffee machine | c9d4195e-31d4-46b8-81b3-12a7217e2d1e | royalty free | Georgy Uvarov | kitchen |
| model | Japanese woodcut print | b7f6b930-c923-430e-bdf4-a85ab35f8645 | CC0 | Joris LM | entry |
| model | Artificial tree Ficus 110 cm | c214eda7-a46c-46e9-9595-c8608af22ff8 | royalty free | Samuel Slavik | entry |
| model | Modern King Bed | f0938871-4743-4d86-8329-39a3652f183f | royalty free | Harrison Costa | primary bedroom |
| model | Night Stand Modern | a4e5c2d2-5545-4839-afd3-16f044b1e4fd | royalty free | Jordi Se-Cam | primary bedroom |
| model | Table Lamp Pletz Bethel | 678c8edf-4638-41e5-898e-87c027981bbe | royalty free | Patrik | primary bedroom |
| model | Black and white japanese aquarelle | 27603523-cfce-45a8-aac3-a39fde4f9211 | CC0 | Joris LM | primary bedroom |
| model | Azeen Rectangle Wood Mirror | eda3165f-82c3-4f27-a90a-62077f025db1 | royalty free | Felipe de Melo | primary bath |
| model | Stack of folded towels (fixed bottom) | 74fca3ee-3226-4629-afdb-3b63ca8b3049 | royalty free | Pawel Walasiewicz | primary bath |
| model | Soap Dispenser | 0e72fc22-d710-4e64-9cbe-dba928d7e16d | royalty free | Rahul Goyal | primary bath |
| model | Grey bath mat | 2fa61c23-51f3-412d-be58-4ae6de38a67f | royalty free | Joris LM | primary bath |
| model | Outdoor Lounge Sofa 3 Seat | cb8204b8-91f9-4cfe-936d-eebb9646ec90 | royalty free | Mike Radjabov | deck (re-covered off white) |
| model | Planter Box 01 | a07fca38-5e43-414d-bc8b-d4a4db3572d9 | CC0 | Poly Haven | deck |
| model | Brick House 135 | 86452dfc-7913-484f-8049-229765ee3a4a | royalty free | Alexander Novgorodtsev | neighbouring houses |
| model | European Maple Acer Campreste | e7032d9a-31fe-4a70-b305-3fefab646877 | royalty free | Digi Motion Studio | back garden trees |
| model | Tree Yellow Birch Betula Alleghaniensis | a74d64fb-d0c7-46c4-83e9-1bd52d2282bb | royalty free | Digi Motion Studio | street trees |
| material | Modern runner rug | 24ee476c-c10d-4846-be33-ec3d63aba688 | royalty free | Md. Monjur Rahman | entry runner (third pass) |
| model | Geome Sideboard | f96683ba-bfd0-473c-b3df-7461201594b3 | royalty free | Duy Ngo | primary bedroom |
| model | Curtain Parametric | 8f38fc13-71f5-40f9-9778-cf27f38a85b0 | royalty free | Joris LM | living, dining and bedroom curtains |
| model | Round mirror | 8170e951-0146-4e58-b518-2694b5f8f4d5 | royalty free | Joris LM | entry |
| model | Bouclette bench (1.04 m) | c7e93d6a-65f4-4f93-83e1-15fdfbd11ee8 | royalty free | Joris LM | entry |
| model | Snake Plant, Potted Indoor Plant | 6569fa36-4ede-4aa5-95af-383341ddf052 | royalty free | Oliver Kucera | entry, primary bath |
| model | Modern white wooden desk | 92d91951-81cb-456b-9034-301d7482b814 | royalty free | SaTales | office seen from the entry |
| model | HM Embody Chair White/Black | d4635b0e-70c1-4ac8-a453-1cd5eb956aab | royalty free | Demycs | office seen from the entry |
| model | Potted Plant 01 | fcd99862-9dc0-4735-bc8d-4b03b9f0a8f6 | CC0 | Poly Haven | office, deck |
| model | Potted Plant 02 | 4c6cff09-e9c6-4868-9172-dd89c3528cef | CC0 | Poly Haven | primary bedroom, deck |
| model | Bathroom heated towel rail | 24198e1f-3111-441a-95ed-c6da10d0fd72 | royalty free | Mesk911 | primary bath |
| model | Lantern 01 | 4926885c-bdf9-47c7-967a-76dba284a2d8 | CC0 | Poly Haven | deck |
| model | Outdoor Armchair with Pillows | 8a2a3748-2f2d-489d-8ad3-774ff15bbcd8 | royalty free | Mike Radjabov | deck (replaces the plain armchair) |
| model | Monestera Plant Small Potted | 5e3c65bb-ccfb-49c8-932c-495e5569ac25 | royalty free | Amanpreet Bajwa | deck |

Fetched, tried and deleted again because they were not used (free assets, removed from the cache and from `bkit-assets.json` on 16 Nov 2026, 302 MB): Large Grey Tiles and Marble 01 (read as flagstones and big beige tiles), Wool Boucle, Plain White Texture, Wooden Cutting Board, Stuttgart Suburbs HDRI (overcast with parked cars), Sunny Walk in the City Park HDRI, the 1.5 m Bouclette bench (no room at the bed foot), Snake plant in a pot (rendered as two floating leaves), Knaget coat rack, Christmas Lights (a single bulb on a curve; the deck string lights are built in `tour-dress.py`), Modern Sconce. The "Sunny Park Path" HDRI in the owner's cache was tried once and dropped because it is not a free asset. Assets that were already in the owner's cache were left alone.

## Garden addition: tour, stills and film (proj-b, added 16 Nov 2026)

Second project for the tour library, from the owner's Blender scene "RENDER PORTFOLIO.blend". Website slug `garden-addition`, public title "Hillside home with garden addition". Private project folder: `E:\Portfolios\Bayview\` (source, packed scene, full size stills, film masters, panoramas, README with the exact re-render commands). The folder name is a place name: it must never reach the site.

- **What the scene holds:** a Revit model of a hillside home with a new two storey addition (garden suite with kitchen, bedroom, bath and laundry below; family room, bedroom, bath and wet bar above; a deck over a spa terrace), on a terrain with roads, scattered grass and trees, plus two unrelated stock houses up the hill. Every Revit piece came on one white material, at 0.881 scene units per metre (all sizes in the scripts are metres times U).
- **Pipeline:** `tools/proj-b-scene.py` (privacy renames, terrain pushed under the floor, BlenderKit PBR materials by world position with box projection, glass panes found inside the window pieces, each wall face sorted inside or outside by ray casting so the old house gets grey stucco, the addition lap siding and every room painted plaster, BlenderKit HDRI turned to match a sun lamp with its own sun clamped out, lights in the model's downlights and fittings) then `tools/proj-b-dress.py` (staging per room, downlight grids where the model has none, garden shrubs and trees from the scene's own scatter, material touch ups, privacy scan, `pack`). Cameras in `tools/proj-b-shots.py`; renders by `tools/proj-b-render.sh` (GPU lock) and `tools/proj-b-all.sh` (unattended: tour, export, film, export, frame clean up); export by `tools/make-proj-b.sh`. Tour data: `tools/tours/garden-addition.json` through the generic `tools/tour-project.py`.
- **Tour:** eight standpoints, all marked `staged` (the model has kitchens, baths, laundry and the spa but no loose furniture; the two crude Revit sofas and tables are hidden): Garden suite, Garden suite bedroom, Spa terrace, Deck, Family room, Living and dining, Kitchen, Bedroom. Hotspots are aimed at the real openings (`aim` in the viewpoints file).
- **Stills:** `public/media/garden-addition-1..6.webp` (+ `-sm`): wide establishing, three quarter from the south west, deck planter detail (70 mm, f/2.2), living and dining, bedroom, late light on the west side.
- **Film:** `public/media/garden-addition-cine-a..d.mp4` (+ `.webp` posters) and the cut `garden-addition-cine.mp4`; master in `E:\Portfolios\Bayview\04 Film\`. A dolly push up the lawn past a tree, a lateral track past shrubs, a pedestal rise from the spa terrace to deck level, an interior slide to the living room window with a focus pull. 8 s each at 24 fps, 1920x804, eased moves with noise drift, motion blur, depth of field.
- **BlenderKit:** every asset used is logged with its id, licence and cache file in `E:\Portfolios\Bayview\bkit-assets.json` (54 free assets). Many sit in the same cache as the hillside tour: please do not delete cache folders listed there (the packed scene in `02 Scenes` no longer needs them, but a rebuild from the source does).
- **Not wired into any page.** Nothing under `src/components`, `src/scripts` or `src/pages` was touched; the library picks the tour up from the JSON and pictures.

## Editing without code: Pages CMS, media pipeline, publish (added 16 Nov 2026)

The owner edits content at app.pagescms.org (`/admin` is a noindex page with one button that goes there; it is out of the sitemap). Owner guide: `EDITING.md`. Nothing here was pushed or connected: there is no GitHub account or remote yet; the steps are in `EDITING.md`, section 1.

- **Content model.** Everything visual that used to be typed into pages now lives in `src/content/*` as content collections with zod schemas (`src/content.config.ts`):
  - `projects/<slug>.json`: one block per project on `/visuals/` (title, summary, order, visible, gallery of `{image, alt}`, optional drawings, films, links, tour slug, `pictureName` for the zoom button labels). The first visible project gets the anchor `#project`, the others `#project-2`, `#project-3`. Older gallery items carry `width`/`height` only to keep the sizes the page always declared; the editor drops them on the first save, after which the real size is used.
  - `workPage/index.json`: Work page words, opening film and cover, featured tour slug and its heading and lead, films heading and count, closing words, SEO title and description.
  - `homePage/index.json`: hero picture (wide and upright), hero film (wide and upright), alt, the four figures, the FAQ, how many film tiles on the home page. `src/data/site.ts` re-exports `figures` and `faqs` from it (About page uses the figures too).
  - `explorer/index.json`: the last stage of the 3D building (final still and the film angles), read by `Explorer.astro`.
  - `films/index.json`: the film tiles (`WorkReel.astro`) in order: title, kind, `clip` (short preview), `film` (full cut, optional), `poster` (optional; default is the clip's own `.webp` next to it), visible.
  - `siteSettings/index.json`: contact email (every page, through `src/data/settings.ts`), Upwork and Fiverr links (`src/data/hire.ts`), social links (`src/data/social.ts`). The error message in the contact form script still names info@axys3d.com directly.
  - Tours keep their own layout and loader (`src/data/tours/<slug>.json`, `public/media/tours/<slug>/`, `src/data/tours.ts` unchanged). The editor lists them as a collection; a room may gain an `image` key, which the loader ignores.
- **Pictures by convention.** Data stores only the full size path. `src/data/media.ts` finds `<name>-sm.webp` next to it and reads width and height from the WebP header at build time, so no sizes are typed in. A film's default cover is `<clip>.webp`.
- **Parity check.** After the move, `dist/` was built from the last commit and from the new code in two separate worktrees and compared page by page (HTML with hashed asset names and whitespace normalised, plus every CSS rule a page loads): identical. The tours change that followed was checked the same way; its only differences are the expected ones.
- **Media pipeline: `node tools/process-media.mjs`** (`--dry` lists the work). Uploads land in `public/media/uploads/` (media root in `.pages.yml` is `public/media`, so older files stay valid). Pictures become `<name>.webp` (longest side at most 1920, quality 82) and `<name>-sm.webp` (at most 800, quality 78), EXIF dropped, turned upright; a jpg or png is replaced by the `.webp`, every data file naming it is rewritten, and the original moves to `assets-src/media-originals/` (git ignored; still in git history). Films become H.264 High, yuv420p, longest side at most 1280, at most 30 fps, CRF 25 capped at 1.6 Mbit/s, fast start, no metadata, sound kept only when present (light H.264 files are only remuxed), plus a cover `<name>.webp` and `-sm` from a frame at 0.5 s. A tour room's `image` (360 degree, 2:1) becomes `public/media/tours/<slug>/<room>.webp` (4096 by 2048, quality 90) and `-sm` (2048 by 1024, quality 88), and the room's `image` is pointed at it; anything not 2:1 is refused with a warning. `tools/media-cache.json` (committed) holds a SHA1 of every file the script wrote, so reruns skip them. Tested on Windows with a 4000 by 2667 JPG, a 4096 by 2048 PNG panorama, a 1080p 60 fps MP4 with sound, an upright MOV, a re-upload under the same name and a wrong shaped panorama; the samples were deleted afterwards.
- **Publish: `.github/workflows/deploy.yml`** on every push to `main` (and by hand from Actions): Node from `.nvmrc`, ffmpeg from apt, `npm ci` (`.npmrc` sets `legacy-peer-deps` because `eslint-plugin-jsx-a11y` does not list eslint 10 yet; without it `npm ci` fails), `process-media`, commit of the prepared media back to `main` with `[skip ci]`, `astro build`, then `SamKirkland/FTP-Deploy-Action@v4.4.0` to `public_html/` with secrets `FTP_SERVER`, `FTP_USERNAME`, `FTP_PASSWORD` (variable `FTP_PROTOCOL`, default `ftps`). `mail/mail-config.php`, `mail/logs/**`, `.well-known/**` and `cgi-bin/**` are excluded, so the server copies are never uploaded over or deleted; the action only deletes files it uploaded itself (its state file `.ftp-deploy-sync-state.json` in `public_html/`).
- **Branches.** `v1.1` becomes `main` at go live (`git push -u origin v1.1:main`). Pages CMS commits to `main`; pull before working locally.
- **Repo size.** What would be committed is about 62 MB in some 430 files; no file over 20 MB. Everything heavy stays ignored: `assets-src/` (7.4 GB: .blend files up to 1.2 GB, a 252 MB .rvt, a 67 MB permit PDF, an 82 MB graded film), `releases/` (192 MB), `public/mail/mail-config.php`.
- **Checks for this setup.** `.pages.yml` was validated against Pages CMS's own config schema (its `lib/config-schema.ts`, bundled locally with a stub field registry); simulated editor saves (empty values and empty lists removed, unknown keys inside lists dropped) still build. Not tested: signing in to Pages CMS, its save round trip on the real repo, and the real FTP upload, which all need the accounts.
