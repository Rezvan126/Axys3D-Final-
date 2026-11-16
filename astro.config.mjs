// @ts-check
import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";
import noDashes from "./src/integrations/no-dashes.mjs";

// https://astro.build/config
export default defineConfig({
  // Live address: used for canonical links, share previews, structured data and the sitemap
  site: "https://axys3d.com",
  // left out of the sitemap: /tours/ only forwards to the tours on the Work page
  integrations: [sitemap({ filter: (page) => !/\/tours\/$/.test(page) }), noDashes()],
  // Old pages that were merged or removed: send visitors and search engines to the new place
  redirects: {
    "/work": "/visuals",
    "/services": "/#services",
    "/process": "/",
  },
});
