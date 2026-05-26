---
name: Terra
colors:
  surface: '#f7faf4'
  surface-dim: '#d8dbd5'
  surface-bright: '#f7faf4'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f1f5ee'
  surface-container: '#ecefe9'
  surface-container-high: '#e6e9e3'
  surface-container-highest: '#e0e3dd'
  on-surface: '#181d19'
  on-surface-variant: '#3d4a3e'
  inverse-surface: '#2d312d'
  inverse-on-surface: '#eff2eb'
  outline: '#6d7b6d'
  outline-variant: '#bccaba'
  surface-tint: '#006e29'
  primary: '#006e29'
  on-primary: '#ffffff'
  primary-container: '#63c771'
  on-primary-container: '#00511c'
  inverse-primary: '#77dc83'
  secondary: '#516351'
  on-secondary: '#ffffff'
  secondary-container: '#d3e8d1'
  on-secondary-container: '#566957'
  tertiary: '#5a6330'
  on-tertiary: '#ffffff'
  tertiary-container: '#aeb87c'
  on-tertiary-container: '#414918'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#93f99d'
  primary-fixed-dim: '#77dc83'
  on-primary-fixed: '#002107'
  on-primary-fixed-variant: '#00531d'
  secondary-fixed: '#d3e8d1'
  secondary-fixed-dim: '#b8ccb6'
  on-secondary-fixed: '#0f1f11'
  on-secondary-fixed-variant: '#394b3a'
  tertiary-fixed: '#dee8a8'
  tertiary-fixed-dim: '#c2cc8e'
  on-tertiary-fixed: '#191e00'
  on-tertiary-fixed-variant: '#434b1a'
  background: '#f7faf4'
  on-background: '#181d19'
  surface-variant: '#e0e3dd'
typography:
  headline-lg:
    fontFamily: Literata
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.3'
  body-md:
    fontFamily: Nunito Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  label-md:
    fontFamily: Nunito Sans
    fontSize: 14px
    fontWeight: '600'
    lineHeight: '1.2'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
---

# Terra — Organic Design

## North Star: "Rooted Warmth"
Calm, grounded, and human. Earthy tones, soft shapes, and natural textures create a warm, approachable experience.

## Colors
- **Primary (`#5abe69`):** Meadow green — core actions, navigation, and primary interactive states.
- **Secondary (`#697c69`):** Moss green — supporting elements and balanced UI segments.
- **Background (`#f7faf4`):** Warm cream — organic, never sterile white.
- **Tertiary (`#737c46`):** Olive gold — highlights, accents, and organic callouts.
- **Palette philosophy:** Earthy and desaturated. No neon or pure-hue colors.
- Use warm neutrals (`#747873`) throughout — every gray should have a subtle green or stony undertone.

## Typography
- **Headlines:** Literata — warm serif with a grounded personality.
- **Body/Labels:** Nunito Sans — friendly, rounded letterforms for accessibility.
- Generous line-height (1.6+ for body). Comfortable, unhurried reading.

## Elevation
- Very soft shadows only: `0 4px 20px rgba(74, 78, 74, 0.06)`.
- Prefer tonal separation over shadows — layer warm cream tones and soft greens.
- Borders: `outline_variant` at low opacity when structural definition is needed.

## Components
- **Buttons:** Primary = solid green (`#5abe69`), large border-radius (12px). Secondary = cream bg + green text + thin border.
- **Cards:** Warm cream fill, generous padding (24px), rounded corners (16px). No harsh borders.
- **Inputs:** Cream background, rounded, soft green focus ring.

## Rules
- Large touch targets, generous spacing. Design should feel breathable and never cramped.
- Avoid sharp corners and hard contrasts. Everything should feel soft and approachable.
- Images should feel natural and warm — avoid clinical or high-tech stock imagery.

## Results report (step 3)

Long-form report layout aligned to the transformation template API (`RealityCheckResponse`):

1. Hero — confidence pill, transformation title, lede
2. What You're Trying To Change — soft panel, quoted goal
3. Is Your Environment Ready? — two-column supporting vs resisting cards (Material Symbols icons)
4. First Bottleneck — feature panel with background image + glass card
5. How To Drive This Change — three phase cards (Start With / Avoid / Introduce Later)
6. What To Measure + When To Course Correct — dual-column feature section
7. Where This Usually Works Best — optional list (hidden when empty)
8. Core Organizational Insight — centered quote block
9. Operational Patterns — sidebar intro + source cards

**Not in UI:** resistance section (API may still return `likely_resistance`). Legacy pressure-simulation timeline removed.

**Assets:** `styles.css?v=29`, `app.js?v=29` — bump version when changing report markup or styles.
