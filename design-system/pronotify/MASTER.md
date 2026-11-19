# Design System Master File

> **LOGIC:** When building a specific page, first check `design-system/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

---

**Project:** proNotify
**Generated:** 2026-08-29 01:43:27
**Category:** SaaS (General)

---

## Global Rule — Dark Theme Only

> ⚠️ **proNotify is a fixed dark-theme site.**
> The UI renders dark **regardless of the browser's light/dark preference** or `data-theme` attribute.
> **Do NOT** design/paint light-mode variants. Keep everything dark.

**Dark mode by default is REQUIRED here** (this overrides the generic "no dark mode by default" anti-pattern).

---

## Color Palette (Dark)

All tokens below are the live values used in `login/index.vue`, `layout/console/index.vue` and the admin pages. Reuse these exact values.

| Role | Hex | CSS Variable |
|------|-----|--------------|
| Background (page) | `#1F1F1F` | `--pn-bg` |
| Sidebar / topbar | `#171717` | `--pn-side` |
| Card | `#1A1A1C` | `--pn-card` |
| Card / row 2 | `#212121` | `--pn-card-2` |
| Input field | `#242424` | `--pn-input` |
| Primary | `#409EFF` | `--pn-primary` |
| Primary hover | `#66B1FF` | `--pn-primary-hover` |
| Accent / CTA | `#EA580C` | `--pn-accent` |
| Border (default) | `#2A2A2A` | `--pn-border` |
| Border (strong) | `#333333` | `--pn-border-strong` |
| Text (primary) | `#DADADA` | `--pn-text` |
| Text (strong) | `#EAEAEA` | `--pn-text-strong` |
| Muted text | `#9B9DA1` | `--pn-muted` |
| Faint text | `#7A7A7A` | `--pn-faint` |
| On Color (text on primary) | `#FFFFFF` | `--pn-on-primary` |
| Success | `#67C23A` | `--pn-success` |
| Warning | `#E6A23C` | `--pn-warning` |
| Danger | `#F56C6C` | `--pn-danger` |
| Shadow | `0 20px 60px rgba(0,0,0,0.4)` | `--pn-shadow` |

**Color Notes:** Trust blue primary on a dark charcoal base; orange applied only to the accent/CTA role. Keep contrast ≥ 4.5:1 (text `#DADADA`/`#EAEAEA` on `#1A1A1C` and `#1F1F1F` satisfies this).

### Typography

- **Heading Font:** Poppins
- **Body Font:** Poppins
- **Mood:** modern, professional, clean, corporate, minimal
- **Google Fonts:** [Poppins](https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap)

**CSS Import:**
```css
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
```

**Stack:**
```css
font-family: 'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans Thai', sans-serif;
```

### Spacing Variables

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | `4px` / `0.25rem` | Tight gaps |
| `--space-sm` | `8px` / `0.5rem` | Icon gaps, inline spacing |
| `--space-md` | `16px` / `1rem` | Standard padding |
| `--space-lg` | `24px` / `1.5rem` | Section padding |
| `--space-xl` | `32px` / `2rem` | Large gaps |
| `--space-2xl` | `48px` / `3rem` | Section margins |
| `--space-3xl` | `64px` / `4rem` | Hero padding |

### Shadow Depths

| Level | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.2)` | Subtle lift |
| `--shadow-md` | `0 4px 6px rgba(0,0,0,0.3)` | Cards, buttons |
| `--shadow-lg` | `0 10px 20px rgba(0,0,0,0.4)` | Modals, dropdowns |

---

## Component Specs

### Buttons

```css
/* Primary Button (deep blue on dark) */
.btn-primary {
  background: #409EFF;
  color: #FFFFFF;
  padding: 12px 24px;
  border-radius: 10px;
  font-weight: 600;
  letter-spacing: 0.5px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.3);
  transition: all 200ms ease;
  cursor: pointer;
}

.btn-primary:hover {
  background: #66B1FF;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.35);
  transform: translateY(-1px);
}

.btn-primary:active {
  transform: scale(0.99);
}
```

### Cards

```css
.card {
  background: #1A1A1C;
  border: 1px solid #2A2A2A;
  border-radius: 12px;
  padding: 20px;
  box-shadow: var(--shadow-sm);
  transition: all 200ms ease;
  cursor: pointer;
}

.card:hover {
  border-color: #409EFF;
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}
```

### Inputs

```css
.input {
  padding: 12px 16px;
  border: 1px solid #333333;
  border-radius: 10px;
  font-size: 14px;
  background: #242424;
  color: #EAEAEA;
  transition: box-shadow 200ms ease;
}

.input:hover {
  box-shadow: 0 0 0 1px #444444 inset;
}

.input:focus {
  border-color: #409EFF;
  outline: none;
  box-shadow: 0 0 0 1.5px #409EFF inset;
}
```

### Modals

```css
.modal-overlay {
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
}

.modal {
  background: #1A1A1C;
  border: 1px solid #2A2A2A;
  border-radius: 16px;
  padding: 32px;
  box-shadow: var(--shadow-lg);
  color: #DADADA;
}
```

---

## Style Guidelines

**Style:** Minimal Dark / Professional

**Keywords:** dark charcoal, deep blue primary, subtle borders, soft shadows, layered, calm, trustworthy

**Best For:** SaaS admin consoles, dashboards, internal tools, financial/property management platforms

**Key Effects:** Consistent `#1F1F1F` canvas, `#1A1A1C` surface cards with `#2A2A2A` hairline borders, blue `#409EFF` primary with `#66B1FF` hover, orange `#EA580C` only for accent/CTA.

### Page Pattern

**Pattern Name:** Hero + Features + CTA

- **Conversion Strategy:** Deep CTA placement. For CTA label text, verify at least 4.5:1 against the button fill; use 7:1 only when the product explicitly targets AAA normal-text contrast. Keep focus and component boundaries independently visible. Disable hero parallax under reduced motion and render its static final state.
- **CTA Placement:** Hero (sticky) + Bottom
- **Section Order:** Hero with headline/image > Value prop > Key features (3-5) > CTA section > Footer

---

## Anti-Patterns (Do NOT Use)

- ❌ **Light mode variants** — the site is dark-only. Never ship a light palette.
- ❌ Excessive animation
- ❌ Emojis as icons — Use SVG icons (Element Plus / Heroicons / Lucide)
- ❌ Missing `cursor:pointer` — All clickable elements must have `cursor:pointer`
- ❌ Layout-shifting hovers — Avoid scale transforms that shift layout
- ❌ Low contrast text — Maintain 4.5:1 minimum contrast ratio on dark backgrounds
- ❌ Instant state changes — Always use transitions (150-300ms)
- ❌ Invisible focus states — Focus states must be visible for a11y
- ❌ Using `#2563EB` / light `#F8FAFC` background tokens (from the old light system) — these are obsolete

---

## Pre-Delivery Checklist

Before delivering any UI code, verify:

- [ ] Page uses dark tokens (`#1F1F1F` / `#1A1A1C` / `#DADADA` / `#409EFF`) — never light
- [ ] No emojis used as icons (use SVG instead)
- [ ] All icons from consistent icon set (Element Plus / Heroicons / Lucide)
- [ ] `cursor-pointer` on all clickable elements
- [ ] Hover states with smooth transitions (150-300ms)
- [ ] Text contrast 4.5:1 minimum against dark surfaces
- [ ] Focus states visible for keyboard navigation
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive: 375px, 768px, 1024px, 1440px
- [ ] No content hidden behind fixed navbars
- [ ] No horizontal scroll on mobile
