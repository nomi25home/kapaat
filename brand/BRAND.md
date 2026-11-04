# Kapaat — Brand Kit

**Kapaat** (Hindi/Marathi/Punjabi: ਕਪਾਟ / कपाट — *cabinet, closet, cupboard*) is a self-hosted storage inventory app. The name is culturally rooted, phonetically memorable, and describes the product literally.

---

## Logo & Mark

| Asset | File | Use |
|---|---|---|
| Full logo (200 × 200) | `icons/kapaat-logo.svg` | App icon, README, social cards |
| Favicon mark (32 × 32) | `icons/kapaat-icon-32.svg` | Browser tab, small UI contexts |
| Horizontal wordmark (320 × 80) | `icons/kapaat-wordmark.svg` | Headers, documentation banners |
| Social card | `kapaat-social-card.png` | Link previews |

App icons are rendered from the logo and live in [`frontend/public/`](../frontend/public/): `favicon.svg`, `icon-192.png`, `icon-512.png`, `maskable-512.png` (full-bleed background, mark scaled into the Android safe zone) and `apple-touch-icon.png` (180 px). Re-render them whenever the logo changes.

The logo's cyan strokes use a gradient in `userSpaceOnUse` units. Don't switch it back to the default bounding-box units: a gradient on a perfectly straight line has a zero-height box and the shelf dividers disappear (fixed in v2.0.0).

### Mark concept

The mark is a stylized four-panel cabinet — two doors, two shelves — rendered in the brand cyan on a dark card. The doors and handles abstractly represent bins and the act of opening/closing storage compartments.

---

## Color Palette

| Role | Name | Hex | Usage |
|---|---|---|---|
| **Primary** | Kapaat Cyan | `#4cd7f6` | Interactive elements, links, active states, mark strokes |
| **Primary dark** | Deep Cyan | `#2ab8d8` | Hover, pressed, gradient end |
| **Background** | Midnight | `#0f1923` | App background, card fills |
| **Surface** | Deep Navy | `#1a2d3d` | Cards, drawers, modals |
| **Surface alt** | Steel | `#243547` | Table rows, hover states |
| **Outline** | Slate | `#869397` | Muted labels, borders, dividers |
| **On-surface** | Off-white | `#e8edf0` | Body text |
| **Secondary** | Seafoam | `#2ecc71` | Success states, quantity badges |
| **Warning** | Amber | `#f0a500` | Caution indicators |
| **Error** | Coral | `#e74c3c` | Destructive actions, error states |

### In the app

The palette above is the dark theme. Kapaat 2 also has a light theme that follows the device setting; its cyan is darkened to `#08748f` so text stays readable on white. The full token table, with light and dark values and contrast notes, is in [DESIGN.md](../DESIGN.md#color); the tokens live in [`frontend/src/styles.css`](../frontend/src/styles.css) and are mirrored in [`tokens.json`](tokens.json).

---

## Typography

| Role | Font | Fallback stack |
|---|---|---|
| **UI / body** | System UI | `system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif` |
| **Codes** (bin codes, tokens) | Platform monospace | `ui-monospace, 'JetBrains Mono', 'DM Mono', Menlo, Consolas, monospace` |

No web fonts are downloaded, so the app works offline and makes no third-party requests. Monospace is reserved for codes, which keeps bin codes like **B-0042** instantly recognisable on screen and on labels.

On printed labels the bin code is Helvetica Bold and the details Helvetica, chosen because every printer driver renders them identically.

---

## Tone of Voice

- **Direct.** Kapaat is a tool, not a platform. Buttons say exactly what they do: *Move*, *Check out*, *Retire*, *Print label*.
- **Compact.** UI text is short. No decorative copy inside the app.
- **Plain.** Use *room*, *zone*, *bin* and *label*; avoid database words like *record* or *entity* in the UI.

---

## Naming Rules

- Product name: **Kapaat** (capital K, lowercase rest). Never "KAPAAT" or "kapaat" in prose.
- Docker images: `ghcr.io/nomi25home/kapaat-api` and `kapaat-web` (all lowercase).
- GitHub repo: `nomi25home/kapaat`.

---

## Usage Guidelines

✅ **Do**
- Use the SVG mark on dark backgrounds (midnight or deep navy).
- Keep the cyan stroke weight proportional when scaling the mark.
- Pair the wordmark with the tagline *STORAGE INVENTORY* in small contexts.

❌ **Don't**
- Recolor the mark outside the brand palette without permission.
- Stretch or distort the cabinet proportions.
- Place the mark on light backgrounds without its dark card (the logo includes one; the bare 32 px mark does not).
- Use the name "Kapaat" to imply official endorsement of a fork or derivative.
