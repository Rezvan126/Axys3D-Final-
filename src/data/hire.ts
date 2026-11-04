// "Hire us" page data. Edit rates and profile links here; the page updates itself.
// Logos: Simple Icons (CC0). Upwork and Fiverr are trademarks of their owners.

export const platforms = {
  upwork: {
    name: "Upwork",
    color: "#6FDA44",
    // TODO: paste your Upwork agency or profile URL. While empty, the button goes to the Contact page.
    url: "",
    logo: "M18.561 13.158c-1.102 0-2.135-.467-3.074-1.227l.228-1.076.008-.042c.207-1.143.849-3.06 2.839-3.06 1.492 0 2.703 1.212 2.703 2.703-.001 1.489-1.212 2.702-2.704 2.702zm0-8.14c-2.539 0-4.51 1.649-5.31 4.366-1.22-1.834-2.148-4.036-2.687-5.892H7.828v7.112c-.002 1.406-1.141 2.546-2.547 2.548-1.405-.002-2.543-1.143-2.545-2.548V3.492H0v7.112c0 2.914 2.37 5.303 5.281 5.303 2.913 0 5.283-2.389 5.283-5.303v-1.19c.529 1.107 1.182 2.229 1.974 3.221l-1.673 7.873h2.797l1.213-5.71c1.063.679 2.285 1.109 3.686 1.109 3 0 5.439-2.452 5.439-5.45 0-3-2.439-5.439-5.439-5.439z",
  },
  fiverr: {
    name: "Fiverr",
    color: "#1DBF73",
    // TODO: paste your Fiverr profile or gig URL. While empty, the button goes to the Contact page.
    url: "",
    logo: "M23.004 15.588a.995.995 0 1 0 .002-1.99.995.995 0 0 0-.002 1.99zm-.996-3.705h-.85c-.546 0-.84.41-.84 1.092v2.466h-1.61v-3.558h-.684c-.547 0-.84.41-.84 1.092v2.466h-1.61v-4.874h1.61v.74c.264-.574.626-.74 1.163-.74h1.972v.74c.264-.574.625-.74 1.162-.74h.527v1.316zm-6.786 1.501h-3.359c.088.546.43.858 1.006.858.43 0 .732-.175.83-.487l1.425.4c-.351.848-1.22 1.364-2.255 1.364-1.748 0-2.549-1.355-2.549-2.515 0-1.14.703-2.505 2.45-2.505 1.856 0 2.471 1.384 2.471 2.408 0 .224-.01.37-.02.477zm-1.562-.945c-.04-.42-.342-.81-.889-.81-.508 0-.81.225-.908.81h1.797zM7.508 15.44h1.416l1.767-4.874h-1.62l-.86 2.837-.878-2.837H5.72l1.787 4.874zm-6.6 0H2.51v-3.558h1.524v3.558h1.591v-4.874H2.51v-.302c0-.332.235-.536.606-.536h.918V8.412H2.85c-1.162 0-1.943.712-1.943 1.755v.4H0v1.316h.908v3.558z",
  },
};

// Rates. Leave `price` empty to show "Quoted per project" instead of a number.
// Example: price: "$25", unit: "/ hour".
export const rates = [
  {
    name: "Fixed-price project",
    best: "A clear scope: a render set, a permit drawing set, a BIM model",
    price: "",
    unit: "",
    points: ["One fixed price agreed before work starts", "Paid in milestones you approve", "Revisions included as agreed in the offer"],
    platform: "Upwork or Fiverr",
  },
  {
    name: "Hourly or monthly support",
    best: "Ongoing production: a dedicated modeler or visualizer for your team",
    price: "",
    unit: "",
    points: ["Pay only for hours worked, tracked by the platform", "Weekly limits you control", "Scale up or pause any time"],
    platform: "Upwork",
    featured: true,
  },
  {
    name: "Ready-made packages",
    best: "Quick, well-defined jobs: a single render, a floor plan, a short walkthrough",
    price: "",
    unit: "",
    points: ["Basic, Standard and Premium tiers", "Price and delivery time shown upfront", "Order in a few clicks"],
    platform: "Fiverr",
  },
];
