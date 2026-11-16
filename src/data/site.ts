// Facts and short texts used on more than one page. Change a number here and it changes everywhere.
// The four figures and the home page questions are edited in Pages CMS: src/content/homePage/index.json.
// The film tiles moved to src/content/films/index.json.
import home from "../content/homePage/index.json";

// the editor leaves out empty values when it saves, so every text falls back to ""
export const figures = (home.figures ?? []).map((f) => ({ value: f.value, unit: f.unit ?? "", label: f.label }));

export const steps = [
  { title: "Send your brief", text: "Drawings, references and your deadline. A sketch or a PDF set is enough to start." },
  { title: "Get a clear quote", text: "We reply within one working day with scope, price, timeline and the number of revisions included." },
  { title: "Review every stage", text: "Work arrives in stages. Each one is checked in house first, and nothing moves on until you approve it." },
  { title: "Receive your files", text: "Native Revit, 3ds Max or Blender files, drawings and final images. They are yours to keep and reuse." },
];

export const faqs = (home.faqs ?? []).map((f) => ({ q: f.q, a: f.a }));

// The four kinds of team that hire us. Used by the "built for you" picker on the home page and by the Industries page.
export const audiences = [
  { slug: "architecture-design-practices", tab: "Architects", name: "Architects and design studios", who: "architects",
    problem: "Deadlines pile up faster than your team can draw.",
    deliver: ["Revit models and drawing sets in your templates", "Permit and construction drawings kept in step with the design", "Planning and client visuals"],
    services: ["revit-production", "bim-production", "architectural-visualization"], img: "svc-plan" },
  { slug: "engineering-multidisciplinary", tab: "Engineers", name: "Engineers and MEP consultancies", who: "engineers",
    problem: "Clashes found on site cost time and money.",
    deliver: ["Coordinated structural and MEP models", "Clash checks, each issue tracked to the right engineer", "Revit documentation"],
    services: ["mep-coordination", "bim-production", "revit-production"], img: "svc-mep" },
  { slug: "developers-asset-teams", tab: "Developers", name: "Developers and property teams", who: "developers",
    problem: "Buyers, investors and councils need to see it before it exists.",
    deliver: ["Planning and marketing renders", "Walkthrough films", "Interactive Unreal Engine tours"],
    services: ["architectural-visualization", "animation-motion", "real-time"], img: "adu-9" },
  { slug: "agencies-production-partners", tab: "Agencies", name: "Agencies and production partners", who: "agencies",
    problem: "More client work than your in house team can render.",
    deliver: ["Renders and films under your brand", "NDA from day one", "Nothing published without your permission"],
    services: ["architectural-visualization", "animation-motion", "3d-modeling"], img: "lounge" },
];
