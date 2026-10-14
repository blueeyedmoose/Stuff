# French site: things for you to review

## 1. Images with English text inside them (11)

These are flattened artwork, so their text can't be translated by editing the
page. They show unchanged on the French site. New French versions would need
to be exported from whatever tool made them, then swapped in.

| Image (Webflow asset name) | Shows | Used on |
|---|---|---|
| ChatGPT Image Oct 5 2026 at 03_26_45 PM-1.svg | Supplier search, "127 matches" | Home, Discover |
| ChatGPT Image Oct 5 2026 at 03_26_46 PM-2.svg | "Available credit $9,729,916" | Home, Finance |
| ChatGPT Image Oct 5 2026 at 03_26_47 PM-3.svg | "Quote Summary" | Home, Source |
| ChatGPT Image Oct 5 2026 at 03_26_48 PM-4.svg | "Tracking # SHP-653" | Home |
| ChatGPT Image Oct 5 2026 at 04_26_20 PM-1.png | "Available credit", Mining Equipment | For Partners |
| ChatGPT Image Oct 5 2026 at 04_26_21 PM-2.png | "Industrial Retrofit", In-Market Collaboration | For Partners |
| ChatGPT Image Oct 5 2026 at 04_26_21 PM-3.png | "Active shipments" | For Partners |
| ChatGPT Image Oct 5 2026 at 05_38_40 PM-1.png | "Active markets" | For Suppliers |
| ChatGPT Image Oct 5 2026 at 05_38_40 PM-2.png | "Available credit", Mining Equipment | For Suppliers |
| ChatGPT Image Oct 5 2026 at 05_38_41 PM-3.png | "Order bundle" | For Suppliers |
| ChatGPT Image Oct 5 2026 at 05_38_41 PM-4.png | "Delivery overview" | For Suppliers, Deliver |

## 2. Issues in the English site (copied faithfully into French)

The French pages mirror these exactly. Fix them in English first and they'll
carry over on the next rebuild.

1. **Company menu, "Contact Us"** links to `/template/licenses` (the template's
   licence page) instead of `/contact-us`.
2. **Use cases menu** starts with an empty, invisible link to `/product/enterprise`,
   the template's demo "Enterprise plan" page.
3. **Source page structured data** (what Google reads) has the FAQ question
   "What is Wealthis and how does it work?". Wealthis is the template's name.
4. **Template copy still present:** "Smart Tools to Power Your Finances" (Deliver page)
   and "Quick answers to help you get the most out of your smart tools" (Discover page).
5. **Page titles** of `/checkout`, `/product/enterprise` and `/template/licenses`
   read "Wealthis - Webflow Ecommerce website template".
6. **For Suppliers meta description** is cut off mid-word ("...so you don't export alo").
7. **For Partners** has a typo: "opportunties".
8. **20 template pages are still published** and listed in `sitemap.xml`, though nothing
   links to them: /home-v2, /home-v3, /overview, /contact-v1, /contact-v2, /career,
   /checkout flow pages, /account/*, /utility/*, /template/style-guide, /template/changelog,
   /product/pro, /product/premium, /category/plans, /401.
9. **Header menu** runs off the right edge between about 992px and 1,080px wide (small
   laptops). This happens in English and French alike.

## 3. Translation choices worth a glance

- **Service pillars as French nouns:** Discover / Source / Finance / Deliver become
  Découverte / Sourcing / Financement / Livraison.
- **DASHBOARD** becomes **MON ESPACE**. It's short enough to keep the menu the same width as English.
- **Insights** becomes **Analyses**.
- **Place names** use French in sentences (Londres, Afrique du Sud) and stay English
  in postal addresses.
- **Language link** is in the footer's Company column ("English" on French pages,
  "Français" on English pages), so the header stays exactly as it is.
  A header switcher can be added later in Webflow.
- **Template-only pages** (checkout, Enterprise plan, licences) are translated
  faithfully, but they'd be better removed from the site in both languages.

All decisions are recorded in `GLOSSARY.md`. Every string, English and French
side by side, is in `strings.json`.
