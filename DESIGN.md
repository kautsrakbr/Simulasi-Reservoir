---
name: CoreReservoir
description: Enterprise subsurface engineering desktop UI for reservoir simulation setup, run, and analysis
colors:
  shell: "#EEF2F6"
  workspace: "#F7F9FB"
  surface: "#FFFFFF"
  surface-alt: "#F1F4F8"
  sidebar: "#E4E9F0"
  border-subtle: "#D7DEE7"
  border-strong: "#B8C3D1"
  text-primary: "#1F2937"
  text-secondary: "#5B6676"
  text-disabled: "#93A1B2"
  primary: "#0F5C8E"
  primary-hover: "#2E7DAE"
  primary-pressed: "#0C4A73"
  primary-soft: "#DCEAF7"
  primary-border: "#A9CCE5"
  success: "#2D6A4F"
  warning: "#A86A15"
  danger: "#B2413F"
  info: "#2563A6"
  oil: "#B7791F"
  gas: "#0F766E"
  focus: "#0F5C8E"
  chart-1: "#0F5C8E"
  chart-2: "#0F766E"
  chart-3: "#6B8E23"
  chart-4: "#B7791F"
  chart-5: "#A14F49"
  chart-6: "#5C6F91"
  gridline: "#DDE4EC"
typography:
  page-title:
    fontFamily: "Segoe UI, sans-serif"
    fontSize: "20px"
    fontWeight: 600
  section-title:
    fontFamily: "Segoe UI, sans-serif"
    fontSize: "17px"
    fontWeight: 600
  card-title:
    fontFamily: "Segoe UI, sans-serif"
    fontSize: "14px"
    fontWeight: 700
  body:
    fontFamily: "Segoe UI, sans-serif"
    fontSize: "12.5px"
    fontWeight: 400
  field-label:
    fontFamily: "Segoe UI, sans-serif"
    fontSize: "12px"
    fontWeight: 500
  mono:
    fontFamily: "Cascadia Mono, Consolas, monospace"
    fontSize: "11.5px"
    fontWeight: 400
rounded:
  input: "4px"
  panel: "8px"
  dialog: "8px"
  pill: "10px"
spacing:
  unit: "8px"
  field-gap: "12px"
  label-to-input: "6px"
  section-gap: "24px"
  panel-padding: "18px"
  page-padding: "24px"
components:
  field-input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.input}"
    height: "32px"
    padding: "0 10px"
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    rounded: "{rounded.input}"
    height: "32px"
    padding: "0 16px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.surface}"
    rounded: "{rounded.input}"
  panel-section:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.panel}"
    padding: "{spacing.panel-padding}"
---

# Design System: CoreReservoir

## 1. Overview

**Creative North Star: "The Subsurface Instrument Panel"**

CoreReservoir reads like an instrument panel for a reservoir simulator, not a SaaS dashboard. The surface stays cold-neutral and quiet so that the one petroleum-blue accent (`#0F5C8E`) carries all the meaning it's given: selection, primary action, focus. Density is real — engineers spend hours moving between grid, PVT, rock, and initial-condition setup — but every group is separated by alignment, whitespace, and a hairline border rather than a shadow. Status, phase, and well-type color (success/warning/danger/info, oil/water/gas, production/injection) all use a single muted, desaturated family per concept rather than bright Tailwind-style accents, so the whole app reads as calm and deliberate instead of cheerful. The system explicitly rejects SaaS marketing dashboards (cheerful gradients, oversized rounded buttons, colorful badge-everything), consumer mobile patterns (large radii, bouncy motion, icon-only actions), and generic AI-admin templates (purple/cyan gradients, identical shadowed card grids, gray text on tinted backgrounds) — see PRODUCT.md Anti-references.

**Key Characteristics:**
- Cold neutral shell/workspace, white surfaces, a visibly distinct (slightly darker) sidebar rail, one petroleum-blue accent used sparingly
- Hairline borders define structure; shadows reserved for dialogs, dropdowns, and genuinely floating/elevated panels only — never plain cards
- Two-font system: Segoe UI for interface text, Cascadia Mono for data/log/numeric content (tables, scientific-notation fields, the run log)
- Small radii everywhere (4–8px); never the large "mobile app" radius
- Status, phase, and well-type colors are each one muted, desaturated hue — never a bright multi-color badge soup

## 2. Colors

A cold, controlled neutral palette with a single petroleum-blue accent; every status/phase/type color is muted enough to read as serious rather than playful, and each physical concept (a Newton variable, a fluid phase, a well type) has exactly one color used identically everywhere it appears.

### Primary
- **Petroleum Blue** (`#0F5C8E`): the only accent. Primary buttons, selected nav item, selected table row, active tab underline, focus outline. Used on a small minority of any screen's surface area.
- **Petroleum Blue Hover** (`#2E7DAE`): hover state of the primary accent.
- **Petroleum Blue Pressed** (`#0C4A73`): pressed/active state of the primary accent.
- **Petroleum Blue Soft** (`#DCEAF7`): selected-row background, subtle highlight behind the active state — never a full-saturation fill for large areas.

### Neutral
- **Shell** (`#EEF2F6`): outermost app background (behind the navigation rail and top bar).
- **Workspace** (`#F7F9FB`): the central workspace background, very slightly lighter than shell so panels read as "lifted" without a shadow.
- **Surface** (`#FFFFFF`): panels, cards, form groups, dialogs, tables.
- **Surface Alt** (`#F1F4F8`): table header rows, secondary/passive panels.
- **Sidebar** (`#E4E9F0`): the navigation rail — deliberately a touch darker/cooler than the workspace so it reads as a distinct rail, not a blended extension of the page.
- **Border Subtle** (`#D7DEE7`): default hairline border between panels and around inputs.
- **Border Strong** (`#B8C3D1`): active dividers, focused group outlines.
- **Text Primary** (`#1F2937`): all body and label text. Never light gray — this is the bar that keeps contrast ≥4.5:1.
- **Text Secondary** (`#5B6676`): captions, helper text, secondary metadata only — never the only color on critical information.
- **Text Disabled** (`#93A1B2`): disabled field/button text.

### Status
- **Success** (`#2D6A4F`): "Ready" / converged / valid states. Soft background `#DCEEE3`, dark text-on-light `#1F4D38`.
- **Warning** (`#A86A15`): incomplete data, not-yet-validated states. Soft background `#F7E9D2`, dark text-on-light `#6B4710`. Never used for general emphasis.
- **Danger** (`#B2413F`): errors, destructive actions, failed runs only. Soft background `#F6DEDC`, dark text-on-light `#7A2B29`.
- **Info / Water** (`#2563A6`): supplementary informational notices, and the canonical color for water saturation (Sw) and injection wells everywhere they appear. Soft background `#DCE8F2`, dark text-on-light `#1B4566`.
- **Oil / Production** (`#B7791F`): the canonical color for oil phase and production wells everywhere they appear. Soft background `#F3E4C7`, shares warning's dark text `#6B4710` (same warm-amber family).
- **Gas** (`#0F766E`, teal): the canonical color for gas phase (Sg), kept visually distinct from "success" green. Soft background `#D9EDE9`, dark text-on-light `#0B4D44`.
- **Focus** (`#0F5C8E`): keyboard focus ring, same hue as primary so focus never competes with the accent.

### Chart / Visualization
- **Series 1–6** (`#0F5C8E`, `#0F766E`, `#6B8E23`, `#B7791F`, `#A14F49`, `#5C6F91`): fixed series mapping used consistently across plots. Gridlines use `#DDE4EC`; plot background is white or the workspace tint — never a heavy gradient fill. Scientific colormaps (viridis, plasma, Blues/Greens, etc.) used for heatmaps and property maps are data encodings, not part of this UI palette, and are not constrained by the rules above.

### Named Rules
**The One Accent Rule.** Petroleum Blue (`#0F5C8E`) is the only saturated color used for interaction (buttons, focus, selection). If a screen has more than one "loud" interactive color competing for attention, one of them is wrong.

**The One Concept, One Color Rule.** Every physical concept that gets a color — a Newton variable (pressure/Sw/Sg), a fluid phase (oil/water/gas), a well type (production/injection) — has exactly one assigned hue, used identically on every page it appears. Pressure/oil/production never silently drift to a different hue on one page than another.

**The Status-Is-Labeled Rule.** Every status color (success/warning/danger) must be paired with a text label or icon. Color alone never carries meaning.

## 3. Typography

**UI Font:** Segoe UI (fallback: system sans-serif)
**Data/Mono Font:** Cascadia Mono (fallback: Consolas, monospace)

**Character:** Calm and highly legible at small sizes; the mono face is reserved strictly for numeric/tabular/log content so the eye can tell "interface" from "data" at a glance.

### Hierarchy
- **Page Title** (600, 20px): top of each main page (Model, Grid, PVT, Rock, Initial...).
- **Section Title** (600, 17px): group/section headers within a page.
- **Card Title** (700, 14px): panel/card headers (e.g. "Project Info", "Newton & Convergence").
- **Body** (400, 12.5px): field values, descriptions, table text.
- **Field Label** (500, 12px): label above or beside every input.
- **Log/Mono** (400, 11.5px, Cascadia Mono): numeric tables, run logs, scientific-notation fields.

### Named Rules
**The Two-Family Rule.** Exactly two font families in the entire app: one UI sans (Segoe UI, no Variable/Display sub-fonts or "Aptos" fallbacks — one reliable family beats a multi-fallback chain), one data mono (Cascadia Mono). Never a third decorative face.

**The Calmer-Weight Rule.** Headers top out at 600–700 weight. The old theme's 800–900-weight hero values and badges read as shouting; nothing in this system needs more than 700.

## 4. Elevation

Flat by default. Depth comes from background-tone separation (shell → workspace → sidebar → surface) and 1px borders, not shadows. Shadows are reserved for transient/floating elements only: dialogs, dropdown menus, popovers, and the docked bottom control panels in the Connectivity 3D / Well Placement / Jacobian pages (those genuinely float over the workspace, unlike a plain card).

### Shadow Vocabulary
- **Floating** (`box-shadow: 0 -3px 24px rgba(15, 23, 42, 0.14)` upward, or `0 4px 16px rgba(15, 23, 42, 0.10)` downward): dialogs, dropdowns, popovers, and docked floating control panels only.
- **None (default)**: panels, cards, and tables sit flat against their background with a 1px `border-subtle` border — no drop shadow.

### Named Rules
**The Flat-Panel Rule.** A form section, table, or plain card never gets a drop shadow. If a panel needs to be distinguished from its background, give it a border and a surface-color change, not a shadow.

## 5. Components

### Buttons
- **Shape:** 4–7px radius, never the large "mobile" radius.
- **Primary:** Petroleum Blue (`#0F5C8E`) background, white text. One primary button per context (e.g. one `Run`, one `Save`).
- **Hover / Pressed:** background steps to `#2E7DAE` on hover, `#0C4A73` on press; a 2px `#0F5C8E` focus outline on keyboard focus, offset 1–2px from the control.
- **Secondary / Ghost:** transparent or `surface-alt` background, `border-subtle` border, `text-primary` label. Used for every action that isn't the single primary one.
- **Danger:** `#B2413F` reserved for destructive confirmation only (e.g. "Delete Project", "Stop Run" while a run is active).

### Status Badges
- **Style:** small pill or tag with the status's soft background and dark-on-light text (never a bright solid fill with light text — that's a "cheerful badge", the opposite of this system's intent), plus a short label (`Ready`, `Incomplete`, `Warning`, `Running`, `Failed`, `Done`).
- **Never** decorative or used for values that aren't actually a state.

### Panels / Form Sections
- **Corner Style:** 8px radius (`ui_kit.make_card`, `make_hero_banner`, and every plain results/dashboard card share this radius now — no more 10–14px outliers).
- **Background:** white (`surface`) against the lighter `workspace` page background.
- **Border:** 1px `border-subtle`; no shadow (see Elevation).
- **Internal Padding:** 16–20px, with 24px gaps between sibling sections on a page.
- **Header:** card title (14px, 700) optionally paired with a small status badge, left-aligned, no colored gradient bar.

### Inputs / Fields
- **Style:** 1px `border-subtle` stroke, white background, 4px radius, 32px height, label always above the field (`field-label` style), 6px gap between label and input.
- **Focus:** border shifts to `#0F5C8E` (Petroleum Blue) plus a soft outer focus ring; never just a color-only change with no outline, for accessibility.
- **Error:** border and helper text switch to `#B2413F` with a specific, operational message below the field (not a generic "invalid input").
- **Disabled:** `text-disabled` (`#93A1B2`) text on `surface-alt` background.

### Tables (QTableWidget / QTableView)
- **Header:** `surface-alt` background, `text-primary` bold 12px label, no gradient.
- **Rows:** 28–32px height, white background, `border-subtle` hairline row separators; selected row uses `primary-soft` background with `text-primary` text (never a saturated full-color fill).
- **Numeric columns:** right-aligned, Cascadia Mono for every numeric/data table (pressures, ratios, scientific-notation tolerances, PVT/rock values), not just the scientific-notation fields.

### Sidebar Navigation
- **Style:** distinct `sidebar` background (`#E4E9F0`), visibly darker than the workspace it sits beside.
- **Active item:** `primary-soft` background with `primary` text, rendered as an inset rounded "pill" (6px radius, small horizontal margin) rather than a flat strip spanning the full row width or a colored side-stripe.
- **Hover:** a faint accent tint only; no border, no stripe.

### Tabs (QTabBar)
- **Style:** flat tab strip, `border-subtle` bottom rule across the whole bar.
- **Active tab:** `text-primary` label, 2–3px `#0F5C8E` top/underline indicator — no filled pill, no gradient background.
- **Inactive tab:** `text-secondary` label, no border, no background fill.
- **Hover:** `border-subtle` background tint only; no color change on text.

## 6. Do's and Don'ts

### Do:
- **Do** use Petroleum Blue (`#0F5C8E`) as the only saturated accent, reserved for primary actions, selection, and focus.
- **Do** give every status (Ready/Incomplete/Warning/Running/Failed/Done), every fluid phase (oil/water/gas), and every well type (production/injection) exactly one color, used identically on every page.
- **Do** keep every status labeled with text, not color alone.
- **Do** use hairline `1px #D7DEE7` borders and background-tone shifts (shell → workspace → sidebar → surface) to separate areas, not shadows.
- **Do** keep label-above-field, 32px control height, and an 8px spacing grid consistent across every page.
- **Do** use Cascadia Mono for any numeric/scientific/log/table-data content, Segoe UI for everything else.

### Don't:
- **Don't** use cheerful gradients, oversized rounded buttons, or colorful badge-everything (SaaS marketing dashboard look) — direct anti-reference from PRODUCT.md.
- **Don't** use consumer mobile UI patterns: large corner radii, bouncy/elastic motion, icon-only primary actions.
- **Don't** use generic AI-admin-template tells: purple/cyan gradients, identical shadowed card grids, gray text on tinted backgrounds.
- **Don't** apply a drop shadow to a regular panel, card, or table — shadows are reserved for dialogs/dropdowns/popovers and genuinely floating docked panels only.
- **Don't** use more than two font families anywhere in the app, or font weights above 700.
- **Don't** let the same physical concept (a variable, a phase, a well type) show up in a different color on two different pages — that's the exact bug this redesign fixed in the Jacobian/Results pages.
- **Don't** put more than one "primary" (filled, accent-colored) button in the same context/page.
- **Don't** let body or field text drop below the readable contrast bar against its background; never use `text-disabled` gray for content that is actually active and important.
