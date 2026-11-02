# 🌿 Rasayanam — Design System & Visual Identity

> **"Rooted in the visual language of Ayurveda, guided by environmental science."**  
> Rasayanam bridges traditional Indian botanical wellness (*Prakriti* & *Prana*) with modern environmental data intelligence.

---

## 1. Design Philosophy

Air quality is often presented through cold, clinical, alarming dashboards. Rasayanam takes a fundamentally different approach:

1. **Prakriti (Nature & Earth):** Employs warm parchment backgrounds, herbal greens, botanical line art, and tactile textures inspired by Ayurvedic herbology, classical manuscripts, and nature.
2. **Prana (Breath & Vitality):** Uses mindful pacing, breathing rhythms, and gentle transitions to encourage awareness, emotional regulation, and calm rather than panic.
3. **Evidence-Led Science:** Strict separation between aesthetic inspiration and hard data. Traditional concepts inform the design language and supportive lifestyle care, while air quality data, machine learning forecasts, and health advisories strictly adhere to CPCB (Central Pollution Control Board) standards and empirical atmospheric models (CAMS).

---

## 2. Typography

The typographic hierarchy combines contemporary geometric clarity with classical editorial warmth:

| Typeface | Classification | Weights | Primary Role & Usage |
| :--- | :--- | :--- | :--- |
| **[Manrope](https://fonts.google.com/specimen/Manrope)** | Modern Geometric Sans | 400, 500, 600, 700, 800 | **Headings, Brand, Display & AQI Numbers:** High impact, punchy numerals (`clamp(58px, 7.2vw, 106px)`), station titles. |
| **[DM Sans](https://fonts.google.com/specimen/DM+Sans)** | Humanist Sans-Serif | 400, 500, 600, 700 | **Body & Interface:** Clean, legible paragraph text, navigation links, advisories, and UI labels. |
| **[DM Mono](https://fonts.google.com/specimen/DM+Mono)** | Monospace | 400, 500 | **Technical Data & Provenance:** Timestamps, pollutant units (`µg/m³`), status badges, kicker labels, and station codes. |
| **Georgia** | Transitional Serif | 400, Italic 500 | **Editorial Emphases & Traditional Accents:** Italicized headline words (*balance*, *today*, *air*), decorative leaf glyphs (`❧`), and botanical badges. |

---

## 3. Color Palette & Design Tokens

### 3.1 Core UI Tokens (`:root`)

Defined in `Rasayanam/static/index.html` and `Rasayanam/static/remedy.html`:

| CSS Variable | Hex / RGBA | Name | Role & Application |
| :--- | :--- | :--- | :--- |
| `--deep` | `#1C392B` | **Deep Forest Green** | Dark hero background, footer background, primary framing container. |
| `--green` | `#31533D` | **Ayurvedic Herbal Green** | Primary brand color, interactive button fills, active chart toggles. |
| `--ink` | `#26352A` | **Dark Charcoal Forest** | Primary text color on light backgrounds, strong readability without harsh pure black. |
| `--paper` | `#EEE9DA` | **Herbal Parchment** | Global background color with subtle micro-dot radial pattern (`rgba(92,77,48,0.07)`). |
| `--cream` | `#F8F4E9` | **Warm Soft Cream** | Surface color for panels, forecast cards, remedy containers, and modal dialogs. |
| `--lime` / Gold | `#D8C17C` | **Ayurvedic Brass / Herbal Gold** | Primary accent: Italic highlights, primary CTA pill (`#D6B66E`), gauge indicator arc. |
| `--muted` | `#777466` | **Earthy Olive Grey** | Subtitles, secondary copy, chart axes, inactive button states. |
| `--line` | `rgba(67, 73, 49, 0.18)` | **Herbal Hairline** | Subtle borders, table separators, card outlines, and dividers. |

---

### 3.2 Botanical & Heritage Accents

Secondary colors used for illustrative badges, remedy types, and cautionary callouts:

| Accent | Hex Code | Role & Application |
| :--- | :--- | :--- |
| **Turmeric Gold** | `#C89E4C` / `#C99A55` | Brandmark dot, heritage mandala stamp (`#D7C18E`), section kickers. |
| **Warm Copper** | `#A86F48` | Leaf emblems (`.note-leaf`), remedy seal borders, preparation indicators. |
| **Sage Mist** | `#C9D0B6` | Secondary illustration fills, ambient background gradients. |
| **Terracotta Alert** | `#A85D3C` / `#9C5036` | Medical disclaimers, caution banners (`#E0D4BD` background with `#A85D3C` border). |
| **Parchment Tan** | `#D9C6AA` | Accent cards in the insights grid (Seasonal context card). |

---

### 3.3 AQI Severity & Data Visualization Palette

The environmental data layer strictly adheres to the Central Pollution Control Board (CPCB) categories, tuned to match the warm botanical visual environment:

| Category | AQI Range | UI Hex Code | Backend CPCB Hex | Tone Description |
| :--- | :--- | :--- | :--- | :--- |
| **Good** | 0 – 50 | `#58A96B` | `#43A047` | Fresh leaf green |
| **Satisfactory** | 51 – 100 | `#A5B95B` | `#8BC34A` | Olive lime green |
| **Moderate** | 101 – 200 | `#E0B94F` | `#F2C230` | Warm golden amber |
| **Poor** | 201 – 300 | `#E88943` | `#F28C28` | Deep apricot / rust orange |
| **Very Poor** | 301 – 400 | `#E34E43` | `#E03B3B` | Coral crimson red |
| **Severe** | 401 – 500+ | `#C92E4A` | `#A4133C` | Deep danger ruby / wine |

#### Dynamic Dark Panel AQI Responses:
When a monitoring station experiences elevated pollution, the dark AQI gauge panel adapts dynamically to reflect environmental severity:
- **Poor (201–300):** `linear-gradient(145deg, #713B1F, #492B20)` + rust amber halo.
- **Very Poor (301–400):** `linear-gradient(145deg, #7C2926, #4B2024)` + crimson halo.
- **Severe (401+):** `linear-gradient(145deg, #6D1428, #350E20)` + pulsing danger glow animation (`@keyframes severeGlow`).

---

## 4. UI Components & Visual Motifs

### 4.1 The Heritage Mandala & Stamp
- **Location:** Hero section & Remedy seal.
- **Visual:** Rotated (`-8deg`) SVG circular mandala featuring concentric circles and petals representing the 4 elements and cardinal directions.
- **Color:** `#D7C18E` with `0.85` opacity and `0.8px` hairline strokes.

### 4.2 Mindful Breathing Pacer ("Prana Lab")
- **Visual Structure:** Concentric orbital rings with a glowing organic core.
- **Color Progression:** 
  - Radial gradient core: `#E5D39B` (gold) → `#A5AE7B` (light sage) → `#537653` (medium green) → `#31513B` (deep forest).
  - Orbital rings: `rgba(220, 195, 126, 0.3)` hairline strokes.
  - Active particles: `#D9C17C` with glowing box-shadow.
- **States:** Smooth scale transformations (`scale(1.18)` on inhale, `scale(0.76)` on exhale).

### 4.3 Interactive Air Quality Map & Heatmap
- **Map Shell:** Parchment-toned tile canvas (`#DFE5D8`) framed in `#F8F4E9`.
- **Marker Bubbles:** Circular pills (`42px`) with white borders, bold Manrope typography, and dynamic AQI band colors.
- **Alert Halos:** Semi-transparent dashed circular radii (`rgba` matching AQI category, `fillOpacity: 0.12`) triggered when AQI exceeds 200.
- **Heat Gradient:** Multi-stop interpolation:
  `0.15: #79A66D` → `0.35: #D0C66D` → `0.55: #E8A34E` → `0.75: #DC6848` → `1.0: #B72E45`.

### 4.4 Charts & Forecast Bars
- **Line Trends:** 2px stroke in `#58784F` over a soft gradient wash of `rgba(126, 151, 94, 0.18)`.
- **Forecast Bars:** Smooth vertical gradient `linear-gradient(180deg, #C7A66B, #627D5A)` with rounded top caps (`3px 3px 0 0`) and staggered entrance transitions.

---

## 5. Layout, Spacing & Elevation

- **Grid System:** Flexible CSS grid with standard container max-width `min(1320px, calc(100% - 64px))`.
- **Corner Radii:**
  - Standard Cards & Panels: `5px` to `7px` (crisp, editorial paper cards).
  - Buttons, Pills & Badges: `22px` to `40px` (tactile organic pebbles).
- **Surface Elevation:** Low-contrast organic drop shadows (`box-shadow: 0 18px 50px rgba(42, 55, 39, 0.08)`) simulating natural ambient light filtering through trees.
- **Micro-Texture:** Global background features an ultra-subtle 8px dot grid (`radial-gradient(rgba(92, 77, 48, 0.07) 0.65px, transparent 0.65px)`).

---

## 6. Motion & Accessibility

1. **Scroll Reveals:** Intersection-observer-driven `.reveal` classes triggering `transform: translateY(28px) → none` with an ease cubic bezier `(.2, .7, .2, 1)`.
2. **Reduced Motion Support:** Respects `prefers-reduced-motion: reduce` by zeroing transition and animation durations immediately.
3. **Color Contrast:** Deep forest text (`#26352A` and `#1C392B`) achieves AAA contrast ratios on parchment backgrounds (`#EEE9DA` and `#F8F4E9`). Warning texts and alerts maintain high visibility with bold weights and distinct iconography.

