---
name: Industrial Logistics & Parts Search
colors:
  surface: '#f8f9fb'
  surface-dim: '#d9dadc'
  surface-bright: '#f8f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f4f6'
  surface-container: '#edeef0'
  surface-container-high: '#e7e8ea'
  surface-container-highest: '#e1e2e4'
  on-surface: '#191c1e'
  on-surface-variant: '#414754'
  inverse-surface: '#2e3132'
  inverse-on-surface: '#f0f1f3'
  outline: '#727785'
  outline-variant: '#c1c6d6'
  surface-tint: '#005bc0'
  primary: '#005bbf'
  on-primary: '#ffffff'
  primary-container: '#1a73e8'
  on-primary-container: '#ffffff'
  inverse-primary: '#adc7ff'
  secondary: '#555f6b'
  on-secondary: '#ffffff'
  secondary-container: '#d9e3f1'
  on-secondary-container: '#5b6571'
  tertiary: '#006d2a'
  on-tertiary: '#ffffff'
  tertiary-container: '#16893a'
  on-tertiary-container: '#000701'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc7ff'
  on-primary-fixed: '#001a41'
  on-primary-fixed-variant: '#004493'
  secondary-fixed: '#d9e3f1'
  secondary-fixed-dim: '#bdc7d5'
  on-secondary-fixed: '#121d26'
  on-secondary-fixed-variant: '#3e4853'
  tertiary-fixed: '#8ffa9b'
  tertiary-fixed-dim: '#73dc82'
  on-tertiary-fixed: '#002108'
  on-tertiary-fixed-variant: '#00531e'
  background: '#f8f9fb'
  on-background: '#191c1e'
  surface-variant: '#e1e2e4'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 26px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: 0.01em
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.04em
  sku-display:
    fontFamily: JetBrains Mono
    fontSize: 18px
    fontWeight: '700'
    lineHeight: 24px
    letterSpacing: 0.05em
  sku-inline:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.03em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-mobile: 0.75rem
  margin: 1.5rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
  space-2xl: 3rem
---

## Brand & Style

This design system is engineered for industrial environments where speed, clarity, and zero-error execution are mission-critical. Designed for warehouse operators, inventory managers, and logistics technicians handling rugged tablets, handheld scanners, and desktop terminals—often under harsh warehouse lighting or while wearing work gloves.

### Design Movement: Industrial Functionalism
The visual language merges **Utilitarian Minimalism** with **High-Contrast Pragmatism**:
- **High Legibility First:** Data density is balanced against severe scannability. Critical metadata such as Bin Locations, Stock Keeping Units (SKUs), and stock levels are prioritized visually.
- **Physical-Touch Ergonomics:** All interactive zones strictly honor an expanded physical footprint (minimum 44px, scaling to 48px–52px on mobile/tablet viewports) to eliminate mis-taps.
- **Fail-Safe Feedback:** Distinct, unambiguous color-coded alerts and status badges prevent costly picking errors.
- **Anti-Glare Neutrality:** Surfaces use low-reflectance neutral backdrops paired with crisp white functional cards to maintain optimal contrast across varying screen brightness levels.

## Colors

The palette delivers strict WCAG AAA / AA compliance, prioritizing clear functional feedback and eliminating chromatic ambiguity.

### Surface & Background Tokens
- **Canvas / App Background:** `#F4F5F7` — Grounded industrial grey that reduces eye fatigue under warehouse fluorescent lighting.
- **Card / Panel Surface:** `#FFFFFF` — Pure white for distinct card isolation over the canvas.
- **Subtle Surface / Neutral Chip:** `#E4E7EB` with text `#3E4C59`.
- **Divider & Structural Borders:** `#CBD2D9` (hairline structure) and `#E2E8F0` (card wrappers).

### Text Hierarchy
- **Text Primary:** `#1F2933` (Dark Slate) — High-contrast readability for part numbers, titles, and shelf indices.
- **Text Secondary / Muted:** `#616E7C` — Reserved for descriptive attributes, timestamps, and secondary specifications.
- **Text Disabled:** `#9AA5B1` — Visible yet explicitly inert.

### Status & Feedback Semantics
- **Brand Focus / Interactive Primary:** `#1A73E8` — Dedicated focus rings, selected rows, and actionable primary commands.
- **Success / Auto-Answer / In Stock:** `#1E8E3E` (Border/Icon/Text) paired with `#E6F4EA` (Background Tint).
- **Warning / Review Needed / Low Stock:** `#E37400` (Border/Icon/Text) paired with `#FEF7E0` (Background Tint).
- **Danger / Reject / Critical Error:** `#D93025` (Border/Icon/Text) paired with `#FCE8E6` (Background Tint).

## Typography

Typography centers entirely on legibility, robust optical weights, and non-ambiguous character recognition (`0` vs `O`, `1` vs `l`).

- **Workhorse Sans (`Inter`):** Powers all headlines, body copy, form fields, and status indicators. Bold weights (`600` and `700`) are used aggressively for data labels, inventory levels, and location markers to speed up glanceable comprehension.
- **Inventory Monospace (`JetBrains Mono`):** Dedicated to SKUs, Serial Numbers, Bin Coordinates, and Hardware Barcodes. Standardized monospace tabular alignment ensures numbers and codes line up precisely in dense picklists.
- **Scale Rules:** The base reading scale is bumped up from conventional web applications (standard body is 16px, large body 18px) to account for arm's-length device viewing on warehouse vehicle mounts and pick carts.

## Layout & Spacing

### Center-Column Architecture
- **Max Content Width:** Strict **720px** centered container (`margin: 0 auto`). This restricts eye travel, preventing horizontal tracking fatigue across wide industrial monitors while translating effortlessly into an edge-to-edge layout on tablets and handheld mobile computers.
- **Rhythm & Padding:** All spacing increments conform to a standard 4px/8px modular scale. Spacing tokens serve as visual buffers to keep distinct inventory groups separated.

### Breakpoints & Adaptability
- **Mobile (< 640px):** Single-column stack. Container padding drops to `margin-mobile` (16px). All button groups stack vertically or convert into sticky bottom action bars.
- **Tablet (640px – 1024px):** Single centered column (up to 720px). Touch target safety buffers increase to isolate tap zones.
- **Desktop (> 1024px):** Fixed 720px central command card column with ambient margins, keeping inputs and parts verification tightly clustered directly within the operator's line of sight.

## Elevation & Depth

To maintain high contrast and utilitarian stability, this design system avoids heavy blurred drop shadows or skeuomorphic embellishments. Depth is handled primarily through surface contrast and structural borders.

- **Level 0 (App Canvas):** `#F4F5F7` flat base.
- **Level 1 (Cards, Search Panels, Data Blocks):** Pure white `#FFFFFF` surface framed with a 1px solid `#E2E8F0` border, grounded by an ultra-crisp ambient shadow: `box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.08)`.
- **Level 2 (Active Modals, Barcode Scanner Overlays, Sticky Bars):** Pure white `#FFFFFF`, border `1px solid #CBD2D9`, `box-shadow: 0 4px 12px 0 rgba(0, 0, 0, 0.12)`.
- **Focus / Touch Indication:** Elements do not rely on elevation to indicate activation. Active items trigger an unequivocal outline: `2px solid #1A73E8` with a `2px` offset.

## Shapes

The design system embraces a **Soft / Industrial Rectilinear** geometry (Roundedness Level 1):
- **Base Components:** Radius of `0.25rem` (4px). Applied to input fields, buttons, status chips, SKU tags, and table cells.
- **Large Cards & Modals:** Radius of `0.5rem` (8px).
- **Rationale:** Sharp and near-rectilinear geometry maximizes data density within the 720px column and matches the physical aesthetic of rugged industrial hardware. Pill shapes are avoided to preserve a crisp, technical look.

## Components

### 1. Touch Targets & Interaction Standard
- **The 44px Rule:** Every interactive component (buttons, chip toggles, inputs, table actions) has an absolute minimum height and width of `44px` (ideal `48px` on mobile/tablet viewports).
- **Focus Rings:** All focused items must show `outline: 2px solid #1A73E8; outline-offset: 2px;` to ensure compatibility with physical barcode scanner keyboards and hardware tab navigation.

### 2. Search Field & Inputs
- **Search Header Input:** Minimum height `52px`, font size `18px`, padded `space-md` horizontally. Background `#FFFFFF`, border `1px solid #CBD2D9`, border-radius `4px`.
- **Action Slots:** Integrated clear button and barcode/camera scanner trigger button (each `44x44px` tap target).

### 3. Buttons
- **Primary Action (e.g., Confirm Pick, Search):** Background `#1F2933`, text `#FFFFFF`, font weight `600`, minimum height `48px`. Active state `#12181F`.
- **Accent / Direct Command:** Background `#1A73E8`, text `#FFFFFF`.
- **Secondary / Utility Button:** Background `#FFFFFF`, border `1px solid #CBD2D9`, text `#1F2933`. Hover/Active: Background `#E4E7EB`.
- **Destructive Action:** Background `#D93025`, text `#FFFFFF`.

### 4. Status Chips & Pill Badges
- **Structure:** Height `32px` for inline metadata or `44px` when interactive/tappable. Padding `0.25rem 0.75rem`. Border radius `4px`.
- **Auto Answer / In Stock:** Background `#E6F4EA`, text `#1E8E3E`, border `1px solid #1E8E3E`.
- **Review Needed / Low Stock:** Background `#FEF7E0`, text `#E37400`, border `1px solid #E37400`.
- **Error / Reject / Out of Stock:** Background `#FCE8E6`, text `#D93025`, border `1px solid #D93025`.
- **Neutral Attribute Chips:** Background `#E4E7EB`, text `#3E4C59`, border `1px solid #CBD2D9`.

### 5. Part Result Cards
- Container: Background `#FFFFFF`, border `1px solid #E2E8F0`, radius `8px`, shadow `0 1px 3px rgba(0, 0, 0, 0.08)`.
- Internal Layout: Card header displays the SKU tag (`JetBrains Mono`, 18px bold, `#1F2933`) paired with the status chip on the right. Card body exposes the Part Name (16px semi-bold) and Warehouse Bin Location (e.g., `BAY-04 // AISLE-12 // SHELF-C` in high-contrast bold).
- Card Footer: Touch-friendly quantity incrementor/decrementor controls (each button minimum 44px).

### 6. Warehouse Location Tags
- Distinct visual box for warehouse coordinates: Background `#F4F5F7`, border `1px dashed #CBD2D9`, monospace font, high-contrast dark text (`#1F2933`).