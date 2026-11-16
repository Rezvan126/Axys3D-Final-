// Social profiles shown in the footer. Edited in Pages CMS: src/content/siteSettings/index.json.
// A link with an empty url is hidden, so visitors never land on a dead "#" link.
import settings from "../content/siteSettings/index.json";

export const social: { name: string; url: string }[] = (settings.social ?? []).map((s: { name: string; url?: string }) => ({ name: s.name, url: s.url ?? "" }));
