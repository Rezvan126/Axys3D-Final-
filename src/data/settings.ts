// Site wide settings edited in Pages CMS: src/content/siteSettings/index.json.
import settings from "../content/siteSettings/index.json";

// the address shown on every page and used in the structured data
export const email: string = settings.email;
export const upworkUrl: string = settings.upworkUrl ?? "";
export const fiverrUrl: string = settings.fiverrUrl ?? "";
