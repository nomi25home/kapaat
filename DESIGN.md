# Kapaat Design System — v2

How Kapaat 2 looks and behaves. The source of truth is [`frontend/src/styles.css`](frontend/src/styles.css); this document explains it. Earlier versions: [docs/history](docs/history/).

## Principles

1. **Phone first.** Most use is one-handed, standing in front of a shelf. Design at 390 px, then let it breathe on desktop (content is capped at 760 px).
2. **One job per screen.** Home finds things, a bin page shows a bin, an item page shows an item. Secondary actions live in sheets.
3. **Plain words.** Buttons say what happens: *Move*, *Check out*, *Retire*, *Print label*. No jargon beyond *room*, *zone*, *bin*.
4. **Nothing is lost.** Offboarding retires instead of deleting, and every change shows in history.

## Color

Tokens are CSS custom properties. Light is the default; dark follows `prefers-color-scheme`. Components only use tokens, never literal colours.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#f4f7f9` | `#0f1923` (Midnight) | page background |
| `--surface` | `#ffffff` | `#1a2d3d` (Deep Navy) | cards, sheets, bottom nav |
| `--surface-alt` | `#eaf0f3` | `#243547` (Steel) | thumbnails, segmented track, tags |
| `--line` | `#d5dee3` | `#2e4356` | borders, list dividers |
| `--text` | `#13222e` | `#e8edf0` | body text |
| `--muted` | `#5d6f7a` | `#93a4ad` | secondary text, labels |
| `--primary` | `#08748f` | `#4cd7f6` (Kapaat Cyan) | primary buttons, links, active nav |
| `--primary-ink` | `#ffffff` | `#062430` | text on primary |
| `--primary-soft` | `#d9f4fb` | `#143b4a` | selected chips, info banners |
| `--success` | `#138a52` | `#4edea3` | success |
| `--warning` / `--warning-soft` | `#855600` / `#fff1d6` | `#f5c26b` / `#3a3020` | "Checked out" badge |
| `--danger` / `--danger-soft` | `#c0392b` / `#fbe5e2` | `#ff8a7d` / `#3a2224` | destructive buttons, "Retired" badge, errors |

Light-mode cyan is darker than the brand cyan so white button text and links on light backgrounds reach 4.5:1. Bin colours are user-chosen and only appear as small swatches.

## Type

| Role | Stack | Size |
|---|---|---|
| UI and body | `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif` | 15 px / 1.45 |
| Codes (bin codes, tokens, OTP) | `ui-monospace, "JetBrains Mono", "DM Mono", Menlo, Consolas, monospace` | inherits |
| Page title | sans, 700 | 18 px |
| Section label (`h3`) | sans, 600, uppercase, 0.06 em tracking | 13 px |
| Small / meta | sans | 13 px |

No web fonts are loaded: the app works offline and self-hosted without third-party requests. Inputs are 16 px so iOS doesn't zoom on focus.

## Spacing and layout

- 4 px base; common gaps are 6, 8, 10, 12, 14 and 16 px. Groups are spaced with flex/grid `gap`, not margins.
- Page: single column, `max-width: 760px`, side gutter `max(16px, safe-area inset)`, `grid-template-columns: minmax(0, 1fr)` so no child can widen the page.
- Touch targets are at least 40 px (buttons 42 px, inputs 44 px, list rows 60 px).
- Radius: 10 px cards, 9 px controls, 999 px chips, 16 px sheets.
- Safe areas: the top bar and bottom nav pad by `env(safe-area-inset-*)`.

## Components

| Component | Notes |
|---|---|
| **Top bar** | Sticky, translucent `--bg` with blur. Back button, title (ellipsis), up to one action. |
| **Bottom nav** | Five tabs: Home, Scan, Add (filled circle), Places, More. Fixed, 64 px + safe area. |
| **Card / list** | `.card` with `.list` rows separated by 1 px `--line`. Rows: 44 px thumbnail or icon, title, one muted meta line, optional badge. |
| **Chips** | Horizontal-scrolling filter row; selected chip uses `--primary-soft` with a `--primary` border. |
| **Segmented control** | Two or three options (Items/Bins, Item/Bin, scan modes). |
| **Sheet** | Bottom sheet on phones, centred dialog from 640 px. Escape and backdrop close it. Used for edit, move, check-out, retire. |
| **Selection bar** | Appears above the bottom nav in select mode: count, *Select all*, *Move*. Inverted colours. |
| **Toast** | One line, bottom-centre above the nav; errors use `--danger` and stay longer. |
| **Badges** | "Out" (warning), "Retired" (danger). |
| **Scanner** | Square video with a framing box; manual code entry below. |

Icons are inline 24 px stroke SVGs (`frontend/src/components/Icon.tsx`), `currentColor`, 1.9 px stroke.

## Interaction rules

- Destructive actions (retire, delete room/zone) open a sheet that explains the consequence; nothing destructive happens on a single tap.
- After a change: toast + refreshed data; stay on the same screen (e.g. retiring a bin keeps you on its page, now marked Retired).
- Empty states say what to do next and link to it.
- Offline: reads come from the last fetched data; writes show an error toast.

## Labels (PDF)

Rendered server-side (`backend/app/labels/`) so sizes are exact:

- QR code on the left, square, full label height minus a 2 mm margin, drawn as vectors.
- Right side: bin code in bold (auto-shrunk to fit), name, then *room › zone*; long text ends with an ellipsis.
- Tiny grey "kapaat" mark bottom-right.
- Plain-paper sheets: 4 mm gutters, corner crop marks offset 0.8 mm from each label, dashed cut outline. Sticker-sheet presets use the manufacturer's margins and pitch.

## Accessibility

- Text pairs meet WCAG AA (4.5:1) in both themes. Lowest pairs: light primary on `--primary-soft` 4.7:1, light danger on `--danger-soft` 4.5:1. Check new pairs before adding them.
- All icon buttons have `aria-label`; sheets are `role="dialog"` with `aria-modal`.
- Focus is visible (2 px `--primary` outline).
- Lists and actions are reachable by keyboard; `/` isn't hijacked.

## Checklist for UI changes

- [ ] Works at 390 px with no sideways scrolling, and at desktop width
- [ ] Looks right in light and dark
- [ ] Uses tokens only; no new colours or fonts
- [ ] Destructive actions confirm in a sheet
- [ ] New screens have an empty state
