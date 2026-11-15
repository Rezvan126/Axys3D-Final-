import { defineCollection } from "astro:content";
import { z } from "astro/zod";
import { glob } from "astro/loaders";

// Reusable SEO fields (page-level title/description)
const seoFields = {
  seoTitle: z.string().max(70).optional(),
  seoDescription: z.string().max(160).optional(),
};


// 2. Individual Services Collection
const services = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/services" }),
  schema: z.object({
    title: z.string(),
    serviceNumber: z.string(),
    serviceLabel: z.string(),
    description: z.string(),
    bestFitBuyers: z.array(z.string()),
    projectStages: z.array(z.string()),
    engagementContext: z.array(z.string()),
  }),
});

// 3. Industries Page Collection
const industriesPage = defineCollection({
  loader: glob({ pattern: "index.md", base: "./src/content/industriesPage" }),
  schema: z.object({
    heroTitle: z.string(),
    heroSubtitle: z.string(),
    heroDescription: z.string(),
    industrySections: z.array(
      z.object({
        id: z.string(),
        targetBuyer: z.string(),
        title: z.string(),
        description: z.string(),
        ctaLabel: z.string(),
        ctaLink: z.string(),
      }),
    ),
    ...seoFields,
  }),
});

// 4. Individual Industries Collection
const industries = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/industries" }),
  schema: z.object({
    title: z.string(),
    serviceLabel: z.string().optional(),
    description: z.string(),
    operatingContext: z.string().optional(),
    buyerPressures: z.array(z.string()).optional(),
    productionRequirements: z.array(z.string()).optional(),
    engagementModel: z
      .array(
        z.object({
          step: z.string().optional(),
          title: z.string().optional(),
          description: z.string(),
        }),
      )
      .optional(),
    typicalServices: z.array(z.string()).optional(),
    responsibilityBoundary: z.string().optional(),
  }),
});


// 8. Insights Page Master Header Data
const insightsPage = defineCollection({
  loader: glob({ pattern: "index.md", base: "./src/content/insightsPage" }),
  schema: z.object({
    heroTitle: z.string(),
    heroSubtitle: z.string(),
    heroDescription: z.string(),
    ...seoFields,
  }),
});

// 9. Individual Insights Articles
const insights = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/insights" }),
  schema: z.object({
    title: z.string(),
    category: z.string(),
    readTime: z.string(),
    summary: z.string(),
    badgeText: z.string(),
    ctaLabel: z.string(),

    // SEO
    seoTitle: z.string().optional(),
    seoDescription: z.string().max(160).optional(),
    publishDate: z.coerce.date().optional(),
    updatedDate: z.coerce.date().optional(),
    keywords: z.array(z.string()).optional(),
    image: z.string().optional(),
    imageAlt: z.string().optional(),
    faq: z.array(z.object({ q: z.string(), a: z.string() })).optional(),

    // Purana field. Build na toote isliye rakha hai.
    // Jab saari .md files me publishDate ho jaye, to ye line delete kar dena.
    publishedDate: z.string().optional(),
  }),
});

// 10. About Page Collection
const aboutPage = defineCollection({
  loader: glob({ pattern: "index.md", base: "./src/content/aboutPage" }),
  schema: z.object({
    heroEyebrow: z.string(),
    heroTitle: z.string(),
    heroDescription: z.string(),
    whyTitle: z.string(),
    whySubtitle: z.string(),
    whyDescription: z.string(),
    principles: z.array(
      z.object({
        num: z.string(),
        title: z.string(),
        description: z.string(),
      }),
    ),
    deliveryTitle: z.string(),
    deliveryDescription: z.string(),
    ctaLabel: z.string(),
    ctaLink: z.string(),
    ...seoFields,
  }),
});

// 11. Contact Page Collection
const contactPage = defineCollection({
  loader: glob({ pattern: "index.md", base: "./src/content/contactPage" }),
  schema: z.object({
    heroEyebrow: z.string(),
    heroTitle: z.string(),
    heroDescription: z.string(),
    checklistTitle: z.string(),
    checklistSubtitle: z.string(),
    checklistItems: z.array(z.string()),
    disclaimerText: z.string(),
    formTitle: z.string(),
    formSubtitle: z.string(),
    formFields: z.object({
      name: z.string(),
      workEmail: z.string(),
      company: z.string(),
      projectType: z.string(),
      projectStage: z.string(),
      disciplines: z.string(),
      sourceInformation: z.string(),
      projectBrief: z.string(),
      deliverables: z.string(),
      targetDate: z.string(),
      additionalInformation: z.string(),
    }),
    projectTypes: z.array(z.string()),
    projectStages: z.array(z.string()),
    disciplineOptions: z.array(z.string()),
    sourceOptions: z.array(z.string()),
    deliverableOptions: z.array(z.string()),
    channelTitle: z.string(),
    channelSubtitle: z.string(),
    channelDescription: z.string(),
    channelActionNote: z.string(),
    ...seoFields,
  }),
});

export const collections = {
  services,
  industriesPage,
  industries,
  insightsPage,
  insights,
  aboutPage,
  contactPage,
};