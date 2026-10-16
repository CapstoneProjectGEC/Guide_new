# UI/UX DESIGN SYSTEM & HERITAGE VISUAL IDENTITY

**Project Title:** AI-Powered Smart Tourist Guide Platform for Karnataka  
**Document Version:** 1.0.0  
**Status:** Approved Baseline (Phase 1 Locked)  
**Author:** Unified Principal Engineering Team  

---

## 1. Design Philosophy: Heritage Modernity

The visual identity marries **contemporary AI SaaS craftsmanship** (inspired by Linear, Perplexity, and Apple) with the **timeless architectural majesty of Karnataka**—specifically the intricate star-shaped soapstone artistry of the Hoysala dynasty at Belur and Halebidu.

### Core Tenets:
1. **Intentionally Distinct**: Avoid generic Bootstrap cards, corporate blue palettes, or default templates. The platform exudes cultural gravity and modern refinement.
2. **Context-First Conversational UI**: The user interface recedes to highlight the dialogue between the tourist and the guide, supported by contextual side-drawers for deep citation and geospatial exploration.
3. **Restrained Micro-Motion**: Motion serves orientation and feedback (e.g., streaming tokens, smooth audio visualizers, drawer slide-outs). Gratuitous, distracting animations are strictly prohibited.
4. **Universal Accessibility (WCAG 2.1 AA)**: All text meets minimum 4.5:1 contrast ratios. All interactive controls are fully keyboard-navigable and screen-reader accessible.

---

## 2. Color Palette & Design Tokens

### 2.1 Primary Heritage Palette

```text
┌────────────────────────────────────────────────────────────────────────┐
│  TEMPLE GOLD (#D4AF37)         │  DEEP HERITAGE BROWN (#2C1810)        │
│  Primary accent, active pins,  │  Headings, high-contrast text,        │
│  glowing badges, focus rings   │  deep structural dividers             │
├────────────────────────────────┼───────────────────────────────────────┤
│  SOAPSTONE GREY (#4A4A4A)      │  IVORY (#FDFBF7)                      │
│  Secondary text, subdued       │  Canvas background, card surface,     │
│  borders, subtle icon accents  │  elevated panels in light mode        │
└────────────────────────────────┴───────────────────────────────────────┘
```

### 2.2 Functional Semantic Tokens

| Token Name | Light Mode Value | Dark Mode Value | Semantic Role |
| :--- | :--- | :--- | :--- |
| `--bg-canvas` | `#FDFBF7` (Ivory) | `#120E0C` (Midnight Basalt) | Main viewport canvas background |
| `--surface-card`| `#FFFFFF` (Pure White) | `#1C1614` (Deep Stone) | Elevated cards, message containers |
| `--surface-panel`| `#F7F3EB` (Soft Sandstone) | `#241C1A` (Carved Basalt) | Side drawer panels, modals |
| `--text-primary` | `#2C1810` (Heritage Brown) | `#F5EBE6` (Warm Marble) | High-contrast body & title copy |
| `--text-muted` | `#665C54` (Muted Umber) | `#A89F91` (Weathered Stone) | Timestamps, metadata, citations |
| `--accent-gold` | `#D4AF37` (Temple Gold) | `#E5C058` (Radiant Gold) | Active buttons, audio visualizer, focus |
| `--border-subtle`| `rgba(44, 24, 16, 0.12)` | `rgba(229, 192, 88, 0.15)` | Card boundaries, dividers |
| `--status-success`| `#2D6A4F` (Forest Green) | `#52B788` | Pipeline success, healthy status |
| `--status-error` | `#9B2226` (Terracotta Red) | `#E63946` | Fallbacks, connection drop, errors |

---

## 3. Typography System

The typography pairs a precision humanist sans-serif for interface clarity with specialized multilingual typography for natural Kannada glyph rendering.

### 3.1 Font Families
- **Primary Latin Font**: `Inter` (UI elements, conversational stream, numeric data) / `Outfit` (Display headings, heritage monuments).
- **Kannada Script Font**: `Noto Sans Kannada` (Clean, highly legible Kannada glyphs with optimal line-height).
- **Monospace Font**: `JetBrains Mono` (Admin chunk explorer, JSON telemetry).

### 3.2 Typographic Hierarchy

```text
Display 1 (H1)  : 36px / 44px Line Height  │ Bold (700)     │ Monument Headings
Title (H2)      : 24px / 32px Line Height  │ SemiBold (600) │ Section Dividers
Subtitle (H3)   : 18px / 26px Line Height  │ Medium (500)   │ Card Titles & Prompts
Body Regular    : 15px / 24px Line Height  │ Regular (400)  │ Conversational Text
Body Small      : 13px / 20px Line Height  │ Regular (400)  │ Citations, Tooltips
Caption         : 11px / 16px Line Height  │ Medium (500)   │ Latency badges, tags
```

---

## 4. Spacing, Radii, Shadows, and Elevation

### 4.1 Spacing Scale
Follows an 8-point harmonic grid:
- `space-1`: 4px
- `space-2`: 8px
- `space-3`: 12px
- `space-4`: 16px
- `space-6`: 24px
- `space-8`: 32px
- `space-12`: 48px

### 4.2 Border Radii (Soapstone Carving Geometry)
- **`radius-sm` (6px)**: Badges, inline citation tags, tooltip wrappers.
- **`radius-md` (10px)**: Input fields, buttons, interactive cards.
- **`radius-lg` (16px)**: Message bubbles, modal containers, side panels.
- **`radius-full` (9999px)**: Voice microphone button, pill filters, user avatars.

### 4.3 Elevation & Glassmorphism
- **Restrained Glass Effect**: Applied only to sticky top headers and floating voice bars (`backdrop-blur-md bg-opacity-80`). Never applied globally to dense body cards.
- **Shadow Scale**:
  - `shadow-sm`: `0 1px 3px rgba(44, 24, 16, 0.05)`
  - `shadow-md`: `0 4px 12px rgba(44, 24, 16, 0.08)`
  - `shadow-lg`: `0 12px 32px rgba(44, 24, 16, 0.12)`

---

## 5. Layout Architecture & Screen Breakpoints

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Top Navigation Bar                              │
│   [Logo: Hoysala Crest]  [Language: ಕನ್ನಡ / EN]  [Audio Mute]  [Dark]   │
├─────────────────┬──────────────────────────────────┬───────────────────┤
│  Left Panel     │          Center Viewport         │   Right Panel     │
│  (Session List  │      Conversational Stream       │  (Citation Drawer │
│  & Attractions) │      & Voice Assistant Bar       │  & Mini-Map)      │
│  [Desktop Only] │      [All Screen Sizes]          │  [Collapsible]    │
└─────────────────┴──────────────────────────────────┴───────────────────┘
```

### Breakpoints:
- **Mobile (`< 768px`)**: Single centered column. Left panel collapses to a drawer menu. Right citation panel opens as a bottom sheet.
- **Tablet (`768px - 1024px`)**: Split view with center conversational view and collapsible right panel.
- **Desktop (`> 1024px`)**: Full three-column layout with fixed left sidebar (280px), central chat thread (flex-1, max-w-3xl), and interactive right citation/map panel (380px).

---

## 6. Detailed Component Specifications

### 6.1 Conversational Chat Interface
- **Assistant Message Bubble**: Soft sandstone surface (`--surface-card`) with a subtle gold left border (2px) indicating authentic guide status.
- **Citation Badges**: Clickable pill tags styled in Temple Gold (`[Doc: Temple_info.pdf, p. 4]`). Hovering highlights the reference; clicking opens the right inspection drawer.
- **Streaming Indicator**: Subtle pulsing gold cursor rather than disruptive jumping dots.

### 6.2 Voice Assistant & Audio Visualizer
- **Microphone Trigger**: Centered, floating action button with concentric pulse animations indicating audio listening states.
- **Visualizer**: Real-time 32-bar frequency visualizer driven by HTML5 Web Audio API rendered in Temple Gold.
- **States**: `Idle` ➔ `Listening` (pulsing gold wave) ➔ `Processing` (indeterminate rotation) ➔ `Speaking` (synchronized amplitude waves).

### 6.3 Citation & Document Inspection Drawer
- **Header**: Document title, page number, and SHA-256 fingerprint badge.
- **Body**: Extracted chunk text with exact search terms highlighted in soft gold tint.
- **Geographic Link**: "View Location on Map" button anchoring to temple coordinates on the Leaflet widget.

### 6.4 Interactive Heritage Map Widget
- **Map Provider**: Leaflet + OpenStreetMap.
- **Tile Styling**: Subtle sepia or desaturated tone matching the ivory/basalt palette.
- **Custom Marker**: Intricate Hoysala stone-crest pin with pulsing gold highlight when a monument is referenced in the active chat turn.

### 6.5 Admin Dashboard UI
- **Visual Hierarchy**: Dense, highly organized, operational layout.
- **Pipeline Tracker**: 8-stage horizontal stepper (`BUILD` to `ACTIVE`) with real-time green/red telemetry indicators.
- **Telemetry Charts**: Smooth Recharts line graphs showing Ollama latency (ms) and memory usage over 5-second polling intervals.
- **Chunk Explorer**: Split pane with search filtering on the left and full chunk metadata JSON on the right.
