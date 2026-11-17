# Editing the website yourself

You change words, pictures, films and projects in a private editor called **Pages CMS**. Open it from **yourdomain/admin** (it sends you to app.pagescms.org). When you press **Save**, the site updates itself: about **3 minutes** later the change is live.

You never need to touch code. If something looks wrong, nothing is lost: see "Undo a change" below, or ask Claude.

**Privacy, every time:** before you upload a picture or film, remove architect names, logos, tags, street names and locations. Do not type client, architect, street or town names anywhere. The editor repeats this reminder next to every picture and text box.

---

## 1. One time setup (Claude helps you with each step)

You do steps A, B, C and E yourself in the browser. Claude does step D on this computer. It takes about 20 minutes.

**A. Make a GitHub account** (GitHub keeps the site's files and its full history)
1. Go to github.com and choose **Sign up**. The free plan is enough.
2. Use your business email. Turn on two step sign in when GitHub offers it.

**B. Make a private place for the site** (a "repository")
1. On GitHub, click **+** (top right), then **New repository**.
2. Name: `axys3d-site`. Choose **Private**. Do not add a README or anything else.
3. Click **Create repository** and send Claude the address it shows, for example `https://github.com/yourname/axys3d-site`.

**C. Add your Hostinger login to GitHub** (so GitHub can upload the site for you)
1. In Hostinger, open **hPanel**, then **Websites**, then **Manage** next to your site, then **Files**, then **FTP Accounts**.
2. Note the **FTP IP** (or hostname) and the **FTP username**. If you do not know the FTP password, use **Change FTP password** there and note the new one.
3. On GitHub, open your repository, then **Settings**, then **Secrets and variables**, then **Actions**, then **New repository secret**. Add three secrets, one at a time, with exactly these names:
   - `FTP_SERVER`: the FTP IP or hostname
   - `FTP_USERNAME`: the FTP username
   - `FTP_PASSWORD`: the FTP password
4. Type these yourself. Never paste the password into a chat, an email or the site.

**D. Claude sends the site to GitHub** (Claude runs this on this computer; a GitHub sign in window opens and you sign in yourself)

```
git remote add origin https://github.com/YOURNAME/axys3d-site.git
git push -u origin v1.1:main
```

The working version (`v1.1`) becomes the live version, called `main`, at this moment. From then on, `main` is what the editor changes and what is published. The first publish uploads the whole site and takes about 10 minutes; after that, about 3.

To watch it: on GitHub, open **Actions**. A yellow dot means busy, a green tick means live, a red cross means something went wrong (tell Claude; the old site stays up).

If the first publish stops at "Upload to Hostinger" with a message about TLS or a secure connection, Hostinger does not accept the encrypted connection on your plan. Then add, under **Settings**, **Secrets and variables**, **Actions**, tab **Variables**, a variable `FTP_PROTOCOL` with the value `ftp`, and run it again (**Actions**, **Publish the website**, **Run workflow**).

**E. Connect the editor**
1. Go to **app.pagescms.org** and choose **Sign in with GitHub**.
2. When asked, allow Pages CMS to see **only** the `axys3d-site` repository.
3. Open `axys3d-site`, branch `main`. You now see the editor: Work page, Home page, Text pages, Team on the Hire us page, Contact and profile links.
4. Bookmark **yourdomain/admin**. That is your way in from now on.

---

## 2. Everyday tasks

The rule for every picture: **upload a new file**. You do not need to resize or convert anything; JPG, PNG or WebP of any size is fine. After you save, the site makes the web sizes itself.

**Replace a still render**
1. **Work page**, **Projects**, open the project.
2. Under **Pictures**, open the picture, click the picture box, **Upload** your new render, choose it.
3. Update **What the picture shows** if it changed. **Save**.

**Add a film**
1. **Work page**, **Films**. Use the **Add** button at the bottom of the list.
2. Give it a **Film name** and a **Small line under the name** (for example: Interior film).
3. **Short preview**: a clip of a few seconds; it plays silently on the tile. **Full film** (optional): the longer cut that opens in the player.
4. Leave **Cover picture** empty; the site takes one from the preview. **Save**.

**Add a new project**
1. **Work page**, **Projects**, then the **Add** button.
2. **Project heading**, **Short file name** (lowercase, for example `lake-house`; never a client or place name), **Short description**.
3. **Position on the page**: 1 is first. Tick **Show on the website**.
4. Add at least one **Picture** (the first one is shown large). Drawings, films and links are optional.
5. **Save**.

**Reorder projects**: change **Position on the page** in each project (1, 2, 3...). **Reorder films or pictures**: drag them in their list. **Save**.

**Hide a project**: open it, untick **Show on the website**, **Save**. It stays in the editor for later.

**Change text**
- Work page headings and lines: **Work page**, **Work page words, opening film and tours**.
- Home page figures and questions: **Home page**, **Opening film, figures and questions**.
- Services, industries, guides, About and Contact: **Text pages**.
- Email, Upwork, Fiverr and social links: **Contact and profile links**. An empty link is simply not shown.
- Team photos, badges, figures and profile links on the Hire us page: **Team on the Hire us page**. Open a person, click the photo to upload a new one (any size; it shows as a small circle), change the figures from their Upwork profile, and update "When the figures were last copied". Untick **Show on the website** to hide someone.

**Replace a virtual tour room picture**
1. **Work page**, **Virtual tours**, open the tour, open the room under **Rooms**.
2. **New 360 degree picture for this room**: upload a 360 degree picture that is twice as wide as it is high, 4096 x 2048 or larger. **Save**.
3. Leave the arrow numbers as they are. If an arrow ends up pointing the wrong way, ask Claude to fix it.

---

## 3. Send these to Claude instead

- New 3D models (Revit, STL, Blender, FBX) and anything that should become a new **3D model, virtual tour, render set or film**.
- A **new virtual tour**, or moving the arrows in an existing tour.
- New renders or films made **from a model** (Claude renders them the same way as the current ones).
- Changes to the **look or layout** of a page, new sections, or the **Services** page text if you are unsure (those pages are built from the headings in the text).
- Anything that went red in **Actions**.

---

## 4. Undo a change

- **Quick fix:** open the same item in the editor and put the old words or picture back, then **Save**.
- **Anything else:** tell Claude "undo my last change" (or describe it). Every save is kept in GitHub's history, so any earlier version can be brought back exactly.
- To look yourself: on GitHub open the repository, then **Commits**. Each save is one line with the time and what changed.
- Your original uploads are kept in that history too, even after the site has made web versions of them.

---

## 5. Good to know

- **About 3 minutes** from Save to live (the first publish takes longer). Refresh the page; if you still see the old version, wait a minute.
- **Films over about 100 MB** must be made smaller before you upload them (GitHub refuses large files). Ask Claude, or export at 1920 wide or smaller. Short previews should be a few seconds long.
- Pictures: any size is fine, but very large files (over 50 MB) upload slowly.
- Two people saving the same item at the same moment: the second save asks you to reload. Nothing is lost.
- The mail settings for the contact form live only on Hostinger and are never changed by publishing.
