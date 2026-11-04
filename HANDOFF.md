# Handoff: where the project stands

Branch: `fix/linux-build-casing` (local commits **not yet pushed**: GitHub account not connected to the session).
Read `DESIGN.md` first.

## Done

- Site builds on Linux (case-sensitive paths fixed; pages renamed lowercase).
- Original bronze home design restored (purple 28-Oct commit reverted).
- Home: sketch→render hero visual (owner dislikes it, see open items); stat cards (43+, 7-day milestone timeline, 172 card with "Recent work" list + static calendar booking tile, 4.8 rating + elevation sheet with Approved stamp); split services showcase (numbered list + preview panel); scroll-pinned "One building, four stages" (stage 1 = hand-drawn sketch, stage 3 grid removed); gallery; FAQ.
- Header redesign, liquid-glass nav pill, gold CTA. Fonts unified to Manrope + Inter, one heading scale.
- Services page and Work page removed; Visuals now holds case studies; Industries rewritten in plain language; Insights rebuilt for SEO (3 guides, structured data, sitemap, robots.txt, og image). New Hire us page.

## Open items (waiting on the owner)

1. **Hero visual**: owner wants it replaced with *ready-made portfolio work*. Candidates on Drive: Architectural › Compound modeling › Renders (medical pavilion 1–5, ORB front, portrait angle…), 215 Montalvo Rd final render film. **Blocked:** Drive file downloads need `drive.usercontent.google.com` and `lh3.googleusercontent.com` added to the environment's allowed domains. Then ask: (a) cross-fade of 4–5 renders or (b) one image.
2. **Hire us**: Upwork + Fiverr profile URLs and real rates → `src/data/hire.ts`.
3. **Domain**: set to `https://axys3d.com` (assumed from footer email), confirm.
4. **Case studies**: still demonstration examples; offer to write real ones from Drive projects (215 Montalvo Rd, 315 Amber Drive).
5. **GitHub**: connect account, then push the branch.
6. Earlier audit items not yet done: contact form posts to `localhost:8000` (must point to the real handler); `public/mail/mail-config.php` should not be committed; README has merge-conflict markers; About page has template filler (repeated "Marcus Mango", e-bike testimonials, fake client logos).

## Previews

- Main preview (artifact): https://claude.ai/artifact/2Z3bzdgxHTVfdVKUW8ieJE
- Hero test page: https://claude.ai/artifact/8StKZ8YEQXb7YjyqEqWD18
- Preview copies are built by a scratchpad script that makes `dist/` path-relative; rebuild with `npx astro build` and re-run it before publishing.
