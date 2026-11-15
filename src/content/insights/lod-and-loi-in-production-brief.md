---
title: "LOD 100 to 500 explained: what each BIM level of development means"
category: "BIM delivery"
readTime: "7 min"
summary: "A plain-English guide to LOD 100, 200, 300, 350, 400 and 500, the difference between LOD and LOI, and how to choose the right level for each stage of your project."
badgeText: "Guide"
ctaLabel: "Read the guide"
seoTitle: "LOD 100 to 500 Explained: BIM Level of Development Guide"
seoDescription: "What LOD 100, 200, 300, 350, 400 and 500 mean in BIM, how LOD differs from LOI, and how to pick the right level for each project stage."
publishDate: 2026-10-20
keywords: ["LOD in BIM", "level of development", "LOD 300", "LOD 400", "LOD vs LOI", "BIM modeling"]
image: "/media/svc-bim.webp"
imageAlt: "BIM model of a residence coloured by discipline"
faq:
  - q: "What does LOD mean in BIM?"
    a: "LOD stands for Level of Development. It describes how complete and reliable a model element is, from a rough placeholder (LOD 100) to a field-verified, as-built element (LOD 500)."
  - q: "What is the difference between LOD 300 and LOD 400?"
    a: "LOD 300 elements have accurate size, shape, location and orientation, good enough for construction documents. LOD 400 adds the detail needed to fabricate and install the element, such as connections and assembly information."
  - q: "Is LOD the same as LOI?"
    a: "No. LOD usually refers to geometry and reliability, while LOI (Level of Information) describes the non-graphic data attached to an element, such as manufacturer, performance values or maintenance details."
---

When an architect asks for a "BIM model", the most important follow-up question is: **to what level of development?** A model built to the wrong LOD either wastes time on detail nobody needs, or falls short exactly when the contractor starts relying on it. This guide explains each level in plain language, so you can write a clear brief and know what you are paying for.

## What LOD means

**LOD (Level of Development)** describes how complete and how reliable a model element is. It is not a measure of how pretty the model looks. A wall at LOD 300 might look identical to one at LOD 200 in a render, but only the LOD 300 wall can be measured and trusted for construction drawings.

The most widely used definitions come from the **BIMForum LOD Specification**. Most project teams, BIM execution plans (BEPs) and contracts refer to it.

## The levels, one by one

### LOD 100: concept

Elements are shown as symbols, masses or placeholders. You can read overall size, height and position on site, but nothing should be measured from them.

**Typical use:** early feasibility, massing studies, area checks.

### LOD 200: approximate geometry

Elements are generic systems with approximate size, shape and location. A wall is "a wall about this thick" rather than a specific build-up.

**Typical use:** schematic design, early coordination, planning visuals.

### LOD 300: precise geometry

Size, shape, location and orientation are accurate and can be measured directly from the model. This is the level most construction documentation is produced at.

**Typical use:** design development, permit and construction drawings, quantity take-off.

### LOD 350: interfaces between systems

Adds the parts needed to coordinate between disciplines: supports, connections and clearances, such as where a duct passes through a beam.

**Typical use:** MEP and structural coordination, clash detection.

### LOD 400: fabrication ready

Elements carry enough detail to be fabricated and installed: exact assemblies, connections and fixing details.

**Typical use:** shop drawings, prefabrication, trade contractor models.

### LOD 500: as built

Elements are verified on site and match what was actually built. Strictly speaking this describes field verification rather than more geometry.

**Typical use:** handover to the owner, facility management.

## LOD vs LOI: geometry and information

**LOI (Level of Information)** describes the non-graphic data attached to an element: manufacturer, fire rating, U-value, maintenance interval and so on. A door can be geometrically simple (LOD 200) and still carry rich information (high LOI) if the facility manager needs it.

A good brief specifies both: **how accurate the geometry must be, and which data each element must carry.**

## How to choose the right level

1. **Start from the use, not the number.** Ask what the model will be used for at each milestone: planning visuals, permit drawings, coordination or fabrication.
2. **Set LOD per element type, not per project.** Structure may need LOD 350 for coordination while furniture stays at LOD 200.
3. **Name the stage.** "LOD 300 for walls, floors and openings at permit submission" is clear. "LOD 300 model" is not.
4. **Agree who approves it.** Every package should have a named reviewer who confirms it meets the agreed level before it moves on.

## Common mistakes that cost time

- Asking for "LOD 400" everywhere, which multiplies modeling hours with no benefit to the design team.
- Mixing up LOD and visual quality. A photoreal render says nothing about model accuracy.
- Leaving LOI out of the brief, then discovering at handover that the model has no usable data.
- Not freezing the design revision the model is built from, so the "approved" model is already out of date.

## How we work with LOD

At Axys3D we agree the level for each element type before modeling starts, build in your templates, and check every package against that level before it reaches you. See our [BIM production](/services/bim-production/) and [Revit production](/services/revit-production/) services, or [send us your brief](/contact/) and we will recommend the right level for each stage.
