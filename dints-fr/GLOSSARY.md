# Dints.com - French (fr-FR) Glossary

Terminology used in the French version of www.dints.com, served under `/fr/`.
Spanish (`/es/`) and Portuguese (`/pt/`) columns will be added once French is
signed off. Every translated string lives in `strings.json`; this file records
the decisions behind them.

## 1. Never translated

| Kept as-is | Why |
|---|---|
| Dints, Dints International, Dints International Ltd | Company names |
| MCA Group, Kanu Equipment, GPC, SMCG, ETS MSSZ, Simandou 2040 | Customer and project names |
| UK Export Finance, British Exporters Association | Organisation names |
| Geoffrey de Mowbray | Person |
| Pro, Premium, Enterprise, Wealthis, Loonis Studio, Apple Pay, Whatsapp | Product and brand names |
| Atkinson Hyperlegible Next / Mono | Font names |
| Postal addresses (e.g. 15-19 Bloomsbury Way, London WC1A 2TH, United Kingdom) | So mail still arrives |
| Email addresses, phone numbers, Incoterms, OEM, ECA, SLA, API, FAQ | Codes and standard abbreviations |

Place names inside sentences use the French form (Londres, Afrique du Sud,
Guinée, Pérou, Philippines). Place names inside postal addresses stay in English.

## 2. Navigation

| English | French |
|---|---|
| HOME | ACCUEIL |
| Solutions | Solutions |
| Discover / Source / Finance / Deliver | Découverte / Sourcing / Financement / Livraison |
| Industries | Secteurs |
| Agriculture | Agriculture |
| Construction (& Infrastructure) | Construction (et infrastructures) |
| Healthcare | Santé |
| Hospitality | Hôtellerie |
| Clean Energy | Énergies propres |
| Mining | Mines |
| Use cases | Cas d'usage |
| Machinery & Equipment | Machines et équipements |
| Leasing & Rentals | Crédit-bail et location |
| Project Delivery | Réalisation de projets |
| Rebuilds & Refurbishments | Reconstruction et reconditionnement |
| Export Credit Agency Support / ECA Support | Accompagnement crédit export / Accompagnement ECA |
| Inventory & Floorplan | Financement des stocks |
| Company | Entreprise |
| About Us / ABOUT | À propos / À PROPOS |
| Contact Us / CONTACT US | Nous contacter / CONTACT |
| Insights / INSIGHTS | Analyses / ANALYSES |
| FOR SUPPLIERS / FOR PARTNERS | FOURNISSEURS / PARTENAIRES |
| DASHBOARD | MON ESPACE (shorter than ESPACE CLIENT, so the menu fits at the same widths as English) |
| Get Started | Commencer |
| Learn More | En savoir plus |

## 3. Business terms

| English | French |
|---|---|
| procurement | approvisionnement (achats when about buying) |
| sourcing / to source | sourcing / sourcer |
| supplier | fournisseur |
| OEM | OEM (constructeur d'origine) |
| dealer | concessionnaire |
| genuine OEM parts | pièces d'origine OEM |
| approved alternatives | alternatives agréées |
| spare parts | pièces détachées |
| multi-brand / multi-supplier | multimarque / multifournisseur |
| one point of contact | un interlocuteur unique |
| RFQ | demande de devis |
| quotation | devis |
| credit facility | ligne de crédit / facilité |
| extended payment terms | délais de paiement étendus |
| export credit agency (ECA) | agence de crédit à l'exportation (ECA) |
| ECA-backed | garanti par une ECA |
| due diligence | due diligence |
| drawdown | décaissement |
| financial close | closing financier |
| working capital | fonds de roulement |
| cash flow | trésorerie |
| leasing | crédit-bail |
| floorplan finance | financement des stocks (floor plan) |
| rebuild / refurbishment | reconstruction / reconditionnement |
| collection (from supplier) | enlèvement |
| consolidation (freight) | groupage |
| air, sea, road and express freight | fret aérien, maritime, routier et express |
| customs clearance | dédouanement |
| multi-site delivery | livraison multisite |
| case study | étude de cas |

## 4. Money and numbers

| English | French |
|---|---|
| $50m | 50 M$ |
| $50 million | 50 millions de dollars |
| €15m | 15 M€ |
| $0.7m to $37.5m | de 0,7 M$ à 37,5 M$ |
| $2 billion+ | 2+ milliards $ ("Md$" reads oddly once the site styling capitalises it) |
| 20+ years / 30+ countries | 20+ ans / 30+ pays |
| Language link | English (FR pages) / Français (EN pages), in the footer's Company column |
| 24 hours | 24 heures |

## 5. Style rules (fr-FR)

- Formal **vous** throughout.
- Non-breaking space before `: ; ! ?`, curly apostrophes (’) and a real ellipsis (…).
  These are applied automatically by `tools/merge_translations.py`.
- Numbers: `1 234,50`. Currency symbol after the number.
- Headings in sentence case (French does not use title case).
  Text that is all capitals in English stays all capitals, with accents (É, À).
- FAQ questions are addressed to "vous" rather than "Dints" to avoid gendering the brand.
- No em dashes. Commas, colons or a plain hyphen instead.
