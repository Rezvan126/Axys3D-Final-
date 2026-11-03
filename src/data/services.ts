// Single source for the 8 services. Used by the Services page and the home page.
// To change a service's image, edit its `image` link (https://... or /images/...).

export interface Service {
  num: string;
  slug: string;
  title: string;
  blurb: string;
  includes: string[];
  image: string;
  /** 24x24 SVG path, shown when the image is missing or still loading */
  icon: string;
}

const unsplash = (id: string) =>
  `https://images.unsplash.com/${id}?auto=format&fit=crop&w=600&h=800&q=75`;

export const services: Service[] = [
  {
    num: "01",
    slug: "bim-production",
    title: "BIM Execution & Model Production",
    blurb:
      "Coordinated BIM models built to firm standards, from concept development through construction-ready detail.",
    includes: ["BIM Modeling", "Model Development", "Model Setup & Standards"],
    image: unsplash("photo-1627141234469-24711efb373c"),
    icon: "M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z M12 12l8-4.5 M12 12v9 M12 12L4 7.5",
  },
  {
    num: "02",
    slug: "revit-production",
    title: "Revit Production & Documentation",
    blurb:
      "Production-ready Revit documentation and drawing sets, coordinated across disciplines and issued on schedule.",
    includes: ["Construction Drawings", "Revit Documentation", "Drawing Coordination"],
    image: unsplash("photo-1721244654392-9c912a6eb236"),
    icon: "M5 3h14v18H5z M9 8h6 M9 12h6 M9 16h3",
  },
  {
    num: "03",
    slug: "mep-coordination",
    title: "MEP Coordination Support",
    blurb:
      "Clash-checked mechanical, electrical and plumbing coordination that keeps every system resolved before it hits site.",
    includes: ["Mechanical", "Electrical", "Plumbing"],
    image: unsplash("photo-1765850262030-1ae93e474473"),
    icon: "M3 7h10a4 4 0 014 4v10 M3 13h5 M17 3v4",
  },
  {
    num: "04",
    slug: "3d-modeling",
    title: "3D Modeling",
    blurb:
      "Accurate architectural, interior and object models built to support every downstream visualization need.",
    includes: ["Architectural Modeling", "Interior Modeling", "Furniture & Objects"],
    image: unsplash("photo-1503387837-b154d5074bd2"),
    icon: "M12 3l8 4-8 4-8-4 8-4z M4 12l8 4 8-4 M4 16.5l8 4 8-4",
  },
  {
    num: "05",
    slug: "3ds-max-production",
    title: "3ds Max Production",
    blurb: "Scene setup, materials and lighting built in 3ds Max to a consistent, production-grade pipeline.",
    includes: ["Scene Setup", "Materials & Texturing", "Lighting & Camera"],
    image: unsplash("photo-1726471809607-b7f016a1696e"),
    icon: "M12 8a4 4 0 100 8 4 4 0 000-8z M12 2v2 M12 20v2 M2 12h2 M20 12h2 M4.9 4.9l1.4 1.4 M17.7 17.7l1.4 1.4 M4.9 19.1l1.4-1.4 M17.7 6.3l1.4-1.4",
  },
  {
    num: "06",
    slug: "architectural-visualization",
    title: "Architectural Visualization",
    blurb: "Exterior, interior and site visualizations that read as photography long before the building exists.",
    includes: ["Exterior Visualization", "Interior Visualization", "Site Visualization"],
    image: unsplash("photo-1706808849802-8f876ade0d1f"),
    icon: "M6 21V4h12v17 M3 21h18 M10 8h4 M10 12h4 M10 16h4",
  },
  {
    num: "07",
    slug: "animation-motion",
    title: "Animation & Motion",
    blurb: "Walkthroughs, fly-throughs and camera sequences that move a project through space with intent.",
    includes: ["Walkthroughs", "Fly-through Animations", "Camera & Motion"],
    image: unsplash("photo-1722421492323-eaf9c401befe"),
    icon: "M3 6h12v12H3z M15 10l6-3v10l-6-3",
  },
  {
    num: "08",
    slug: "real-time",
    title: "Real-time / Unreal Engine",
    blurb:
      "Real-time environments in Unreal Engine: interactive walkthroughs and virtual showrooms your clients can explore.",
    includes: ["Interactive Walkthroughs", "Real-time Visualization", "Virtual Showrooms"],
    image: unsplash("photo-1706808849780-7a04fbac83ef"),
    icon: "M3 4h18v12H3z M8 20h8 M12 16v4 M10 7.5l4.5 2.5-4.5 2.5z",
  },
];
