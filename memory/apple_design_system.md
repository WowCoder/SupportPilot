---
name: Apple Design System
description: SupportPilot uses Apple design system from DESIGN.md - SF Pro fonts, Apple Blue (#0071e3), negative tracking, glass navigation
type: reference
---

## Apple Design System (from DESIGN.md)

All frontend pages must follow the Apple design system defined in `DESIGN.md` at the root directory.

### Key Design Tokens (in `static/css/style.css`)

**Colors:**
- Black: `#000000`
- Light Gray: `#f5f5f7`
- Near Black: `#1d1d1f`
- Apple Blue (ONLY accent): `#0071e3`
- Body Link: `#0066cc` (light bg), `#2997ff` (dark bg)

**Typography:**
- Display: `'SF Pro Display', 'SF Pro Icons', 'Helvetica Neue', sans-serif`
- Text: `'SF Pro Text', 'SF Pro Icons', 'Helvetica Neue', sans-serif`
- Negative letter-spacing at all sizes (e.g., -0.28px at 56px, -0.374px at 17px)

**Components:**
- Navigation: Glass effect (`rgba(0, 0, 0, 0.8)` + `backdrop-filter: saturate(180%) blur(20px)`)
- Buttons: Primary Blue (`#0071e3`), Pill links (980px radius), Filter buttons
- Cards: 8px radius, single shadow `rgba(0, 0, 0, 0.22) 3px 5px 30px 0px`
- Forms: 8px radius inputs, 2px `#0071e3` focus outline

**How to apply:** When creating or updating any frontend page, use the CSS custom properties from `static/css/style.css`. Do NOT define custom colors or styles - always reference DESIGN.md.
