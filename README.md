# Axys3D website

The marketing site for Axys3D, an AEC visualization and BIM studio. It is built with Astro 6 and is fully static. The owner edits it with Pages CMS, and GitHub Actions publishes it to Hostinger over FTP.

## Status for the developer taking over

**Done:**
- The repository is private.
- `main` is the current site (v1.1). Branch `v1.0` holds an older version, kept for reference only.
- Pages CMS is connected. Its GitHub App is installed on this repository only, and the editor is at https://app.pagescms.org/attiqn770/axys3d-site/main. The config is `.pages.yml`, and the owner's guide is `EDITING.md`.
- The publish workflow (`.github/workflows/deploy.yml`) runs on every push to `main`. It processes uploaded media, builds, then uploads `dist/` by FTP. Run #1 passed.

**Left to do (this is the hand over):**
1. **Hosting.** Hostinger (or any PHP host with FTP; the contact form is PHP).
2. **Secrets.** In repo Settings > Secrets and variables > Actions, add `FTP_SERVER`, `FTP_USERNAME` and `FTP_PASSWORD`. Optionally add the repository variable `FTP_PROTOCOL` set to `ftp` if the host refuses FTPS (the default is `ftps`).
   - Until `FTP_SERVER` exists, the workflow builds but skips the upload on purpose.
   - The upload goes to `public_html/`.
3. **Mail settings.** The contact form posts to `mail/contact-handler.php` (PHPMailer). The handler and PHPMailer are in the repo and deploy with the site.
   - The SMTP settings file `mail/mail-config.php` is git ignored, and the deploy never uploads or deletes it. Create it on the server by hand in `public_html/mail/`.
   - `contact-handler.php` shows which settings it reads.
4. **First publish.** Go to Actions > Publish the website > Run workflow. Then check the live site and send the contact form once.
5. **Domain.** Point the domain at the host and set `site` in `astro.config.mjs` if it changes. The canonical URLs and sitemap use it.

## Run it locally

Use Node 22.12 or later (see `.nvmrc`).

```bash
npm ci
npm run dev        # local dev server
npm run build      # static build into dist/
npm run check      # type and content checks
```

`node tools/process-media.mjs` makes the web sizes of anything uploaded in the editor (`public/media/uploads/`). It needs `ffmpeg` for films. The workflow runs it on every publish.

## Where things are

| What | Where |
|---|---|
| Pages | `src/pages/` |
| Shared parts (navbar, tours, team cards, film reel) | `src/components/` |
| Content the editor changes | `src/content/` (projects, films, team, page texts, site settings) |
| Virtual tours | `src/data/tours/*.json` and `public/media/tours/<slug>/` |
| Design rules (colours, type, spacing, the owner's rules) | `DESIGN.md` |
| Full project history and render pipelines | `HANDOFF.md` |
| Owner's editing guide | `EDITING.md` |

## Owner's rules (please keep)

- **Privacy:** no architect, client, street or town names anywhere. That covers pictures, file names and text.
- **Real work only:** no stock images and no invented people or numbers.
- **No dashes in visible text.** A build step removes them anyway.
- **Payments:** through Upwork and Fiverr only.
- **Secrets:** `public/mail/mail-config.php` and all passwords stay out of git.
