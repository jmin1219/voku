---
created: 2026-01-25
updated: 2026-01-25
---
# Voku Design System — Workshop for Thought

**Philosophy:** Voku is a cognitive prosthetic, not a consumer app. The interface should feel like a well-worn workshop or architect's studio—grounded in physical materials, tonal depth, and selective color as data markup.

---

## Core Principle

**"Workshop for Thought"** aesthetic:
- Warm charcoal walls (not void black)
- Quality paper surfaces for content (not stark white)
- Selective color as data emphasis (like blueprint markup)
- Tonal depth through 7 levels (not binary dark/light)

**Inspiration:** Architect's studio, woodworking shop, craftsman's workspace

---

## Color Palette

### Tonal System (7 Levels)

```css
/* Dark surfaces (charcoal, not black) */
--level-1: #1a1816    /* Deep base - main background */
--level-2: #252321    /* Elevated - cards on dark */
--level-3: #2f2c29    /* Raised - hover states */
--level-4: #3a3734    /* High - active states */

/* Light surfaces (paper, not white) */
--level-5: #e8e4df    /* Content base - paper texture */
--level-6: #f2efea    /* Content hover - lighter paper */
--level-7: #f9f7f4    /* Content peak - brightest focus */
```

### Typography

```css
/* On dark surfaces */
--text-dark-primary: #f2efea      /* Warm white */
--text-dark-secondary: #9a9286    /* Warm gray */
--text-dark-muted: #706b62        /* Darker warm gray */

/* On light surfaces */
--text-light-primary: #252321     /* Warm black */
--text-light-secondary: #5a564f   /* Darker warm gray */
--text-light-muted: #7a756d       /* Medium warm gray */
```

### Domain Colors (Selective Accent)

```css
/* Fitness - Burnt orange (warm, energetic, earthy) */
--fitness-primary: #e6773a
--fitness-secondary: #d4622a
--fitness-muted: #c45520

/* Finance - Teal cyan (cooler, serious, professional) */
--finance-primary: #36b8c8
--finance-secondary: #2a9fad
--finance-muted: #208793

/* Semantic */
--color-success: #5a9f6e
--color-warning: #d4a134
--color-error: #c8554e
--color-info: #5d8fb0
```

### Borders

```css
--border-dark: #3a3734       /* On dark surfaces */
--border-light: #d4cfc8      /* On light surfaces */
--border-subtle: #c4bfb8     /* Subtle dividers */
```

---

## Design Philosophy

### 1. Tonal Depth Over Binary Contrast

**Why:** Binary dark/light creates harsh jumps. 7 tonal levels allow smooth transitions between surfaces.

**Application:**
- Sidebar: Level 2 (recedes slightly from background)
- Cards on dark: Level 2 → Level 3 on hover
- Content panels: Level 5 → Level 6 on hover
- Active states: Level 4 (dark) or Level 7 (light)

### 2. Warm Neutrals for Cognitive Comfort

**Why:** Pure black (#000) and pure white (#FFF) create high contrast that fatigues eyes. Warm neutrals (#1a1816 to #f9f7f4) feel like physical materials.

**Inspiration:** 
- Charcoal: Drawing paper, workshop walls
- Paper: Quality stock, architect's vellum
- Warm grays: Concrete, brushed metal, natural stone

### 3. Color as Data Markup (Not Decoration)

**Why:** In workshops, color highlights what matters (blueprint red lines, hazard orange). Background stays neutral.

**Application:**
- Domain colors (orange/teal) used ONLY for:
  - Page headers (gradient text)
  - Data values (metric numbers)
  - Active navigation states
  - Category badges
- Never used for: backgrounds, large surfaces, decorative elements

### 4. Spatial Hierarchy Through Luminance

**Why:** Material Design 3 principle - surfaces get lighter as they advance toward user.

**Application:**
- Navigation (sidebar): Dark (recedes, chrome)
- Content panels (tables): Light (advances, focus)
- Metrics (glanceable): Dark (doesn't compete)
- Detail views: Light (sustained reading)

---

## Component Theming Map

| Component | Surface | Rationale |
|-----------|---------|-----------|
| **Sidebar** | Level 2 (dark) | Navigation chrome recedes |
| **Page backgrounds** | Level 1 + grid | Ambient workspace |
| **Quick action cards** | Level 2 (dark) | Brief interactions |
| **Metric cards** | Level 2 (dark) | Glanceable display numbers |
| **Data tables** | Level 5 (light) | Text-heavy, sustained reading |
| **Detail panels** | Level 5 (light) | Content focus, analysis |
| **Drop zones** | Level 2 → Level 3 | Dark for quick actions |
| **Results** | Level 5 (light) | Review extracted data |

---

## Badge System

### On Light Surfaces (Level 5-7)

```css
.badge-category-food-light {
  background: rgba(212, 98, 42, 0.15);
  color: #c45520;
  border: 1px solid rgba(212, 98, 42, 0.3);
}
```

**Strategy:** Darker, more saturated colors for readability on warm paper.

### On Dark Surfaces (Level 1-4)

```css
.badge-category-food-dark {
  background: rgba(230, 119, 58, 0.2);
  color: #e6773a;
  border: 1px solid rgba(230, 119, 58, 0.4);
}
```

**Strategy:** Brighter, less saturated for visibility on warm charcoal.

---

## Visual Effects

### Shadows (Not Glows)

Replaced neon glows with soft elevation shadows:

```css
.shadow-low: 0 1px 3px rgba(0, 0, 0, 0.3)
.shadow-medium: 0 4px 12px rgba(0, 0, 0, 0.25)
.shadow-high: 0 8px 24px rgba(0, 0, 0, 0.2)
```

**Why:** Shadows feel material/physical. Glows feel digital/artificial. Workshop metaphor requires physical depth cues.

### Accent Shadows (Selective)

```css
.accent-fitness: 0 0 20px -8px rgba(230, 119, 58, 0.4)
.accent-finance: 0 0 20px -8px rgba(54, 184, 200, 0.4)
```

**Use only for:** Active navigation, selected items, focal metric cards.

### Grid Texture

```css
.bg-grid-fitness: rgba(230, 119, 58, 0.06) /* Subtle warm orange */
.bg-grid-finance: rgba(54, 184, 200, 0.06) /* Subtle cool teal */
```

**Why:** Provides ambient domain identity without overwhelming. Like subtle texture in quality paper.

---

## Typography

**Font Stack:**
- **UI Text:** Inter (clean, modern, readable)
- **Data/Code:** JetBrains Mono (technical, precise)

**Hierarchy:**
- **H1 (Page titles):** 1.875rem (30px), bold, gradient text
- **H2 (Section titles):** 1.25rem (20px), semibold
- **Body:** 0.875rem (14px), regular
- **Small:** 0.75rem (12px), for labels/captions

---

## Spatial System

### Gestalt Proximity

- **Internal grouping:** 8-12px (elements that belong together)
- **Section spacing:** 24-32px (separate concerns)
- **Page padding:** 32px (breathing room)

### Elevation

**Dark surfaces:** Level 2 → Level 3 → Level 4
**Light surfaces:** Level 5 → Level 6 → Level 7

**Visual cue:** Subtle brightness increase, not dramatic shadows.

---

## Domain Identity

### Fitness (Orange/Red)

**Colors:**
- Primary: #e6773a (burnt orange)
- Secondary: #d4622a (darker orange)
- Muted: #c45520 (even darker)

**Psychology:** Warm, energetic, earthy. Associated with physical exertion, heat, movement.

**Application:**
- Page header gradients
- Workout metric values
- Active navigation in fitness section
- Workout type badges

### Finance (Teal/Cyan)

**Colors:**
- Primary: #36b8c8 (teal cyan)
- Secondary: #2a9fad (darker teal)
- Muted: #208793 (even darker)

**Psychology:** Cooler, serious, professional. Associated with water (flow), clarity, precision.

**Application:**
- Page header gradients
- Financial metric values
- Active navigation in finance section
- Category badges

---

## Component Library

### Cards

**Dark cards:**
```tsx
<Card className="card-dark">  {/* Level 2 background */}
<Card className="card-dark hover:bg-[var(--level-3)]">
```

**Light cards:**
```tsx
<Card className="card-light">  {/* Level 5 background */}
<Card className="card-light hover:bg-[var(--level-6)]">
```

### Tables

**Light tables (text-heavy content):**
```tsx
<TableRow className="hover:bg-[var(--level-6)]" style={{ borderColor: 'var(--border-light)' }}>
<TableHead style={{ color: 'var(--text-light-secondary)' }}>Header</TableHead>
<TableCell style={{ color: 'var(--text-light-primary)' }}>Data</TableCell>
```

**Dark tables (brief scans):**
```tsx
<TableRow style={{ borderColor: 'var(--border-dark)' }}>
<TableHead style={{ color: 'var(--text-dark-secondary)' }}>Header</TableHead>
<TableCell style={{ color: 'var(--text-dark-primary)' }}>Data</TableCell>
```

### Badges

```tsx
{/* On light surfaces */}
<span className="badge-category-food-light">Delivery</span>

{/* On dark surfaces */}
<span className="badge-fitness-dark">85 W</span>
```

### Buttons

Use shadcn defaults - they adapt to warm palette through CSS variables.

---

## Differentiation from Generic Dashboards

### What Voku Avoids

❌ Blue/purple VS Code gradients  
❌ Stark white backgrounds (#FFFFFF)  
❌ Pure black voids (#000000)  
❌ Neon glows everywhere  
❌ Bright accent colors as backgrounds  

### What Voku Embraces

✅ Warm charcoal & paper tones  
✅ 7-level tonal depth  
✅ Color as selective data markup  
✅ Physical material metaphors  
✅ Soft elevation shadows  

**Result:** Feels like custom-built thinking tool, not generic SaaS dashboard.

---

## Implementation Checklist

### ✅ Completed

- [x] Color system in globals.css (7 tonal levels)
- [x] Typography variables (dark/light contexts)
- [x] Domain color definitions (fitness orange, finance teal)
- [x] Badge system (light and dark variants)
- [x] Surface utilities (card-dark, card-light)
- [x] Shadow system (elevation, not glows)
- [x] Grid backgrounds (subtle warm tints)
- [x] All 6 pages updated:
  - [x] Home (warm charcoal cards)
  - [x] Fitness › Log (dark drop zone, light results)
  - [x] Fitness › History (dark master, light detail)
  - [x] Finance › Import (dark drop zone, warm results)
  - [x] Finance › Transactions (light table)
  - [x] Finance › Summary (dark metrics, light table)
- [x] Sidebar (warm charcoal, domain-colored active states)
- [x] Shell (warm backgrounds with subtle domain tints)

---

## Interview Defense

### Q: "Why this specific color palette?"

**Answer:** "I designed a 'Workshop for Thought' aesthetic inspired by physical workspaces—architect's studios, woodworking shops. The palette uses warm charcoal (#1a1816) instead of void black, and quality paper tones (#e8e4df) instead of stark white. This creates 7 levels of tonal depth rather than binary contrast. The warm neutrals reduce eye fatigue while maintaining spatial hierarchy through subtle luminance shifts. Domain colors—burnt orange for fitness, teal for finance—are used selectively as data markup, not decoration, following the principle that color should emphasize what matters, not fill every surface."

### Q: "How is this different from typical dark mode?"

**Answer:** "Most dark modes use pure black (#000) or cool grays that feel sterile. Voku uses warm charcoal with subtle brown undertones, creating a grounded, material feel. The 7-level tonal system allows surfaces to 'float' at different elevations through natural luminance gradients—sidebar at Level 2 (recedes), content panels at Level 5 (advance). This follows Material Design 3's principle that 'higher surfaces are lighter' but applies it through warm neutrals instead of cool grays. The result feels like a physical workspace rather than a digital interface."

### Q: "Why not use standard design system colors?"

**Answer:** "Voku is a portfolio piece demonstrating design thinking, not template application. Standard systems like Tailwind's slate palette or Material's grays are optimized for broad appeal. The warm workshop palette differentiates the project while serving the cognitive prosthetic metaphor—this is a tool for thinking, not consuming content. The warm tones reduce cognitive friction for extended sessions while the selective domain colors (orange fitness, teal finance) maintain clear spatial orientation. It's a deliberate stance that I can defend with both aesthetic and functional rationale."

---

## Future Considerations

### Chat Interface (v0.3+)

When implementing chat with subagents:

**Conversation bubbles:** Level 5-6 (warm paper, optimized for reading)  
**Chat chrome:** Level 1-2 (dark, recedes)  
**User messages:** Slight fitness orange tint  
**AI messages:** Slight finance teal tint  

**Rationale:** Sustained reading benefits from positive polarity effect. Color-coding by sender maintains conversational flow.

### Form-Heavy Pages

Any future forms should use Level 5 surfaces:
- Input fields on warm paper
- Labels in warm gray
- Focus states with domain color accents

---

## Technical Implementation

### Utility Classes

```css
/* Surface levels */
.surface-dark-1, .surface-dark-2, .surface-dark-3
.surface-light-5, .surface-light-6, .surface-light-7

/* Card shortcuts */
.card-dark  /* Level 2 background, warm text */
.card-light /* Level 5 background, dark text */

/* Badges */
.badge-fitness-light, .badge-fitness-dark
.badge-finance-light, .badge-finance-dark
.badge-category-{type}-{theme}  /* 13 category types × 2 themes */

/* Shadows */
.shadow-low, .shadow-medium, .shadow-high
.accent-fitness, .accent-finance
```

### Component Patterns

**Dark card:**
```tsx
<Card className="card-dark">
  <CardTitle style={{ color: 'var(--text-dark-primary)' }}>Title</CardTitle>
  <p style={{ color: 'var(--text-dark-muted)' }}>Description</p>
</Card>
```

**Light table:**
```tsx
<Card className="card-light">
  <Table>
    <TableRow style={{ borderColor: 'var(--border-light)' }}>
      <TableCell style={{ color: 'var(--text-light-primary)' }}>Data</TableCell>
    </TableRow>
  </Table>
</Card>
```

**Domain accent:**
```tsx
<div className="gradient-text-fitness">Fitness History</div>
<span className="badge-fitness-dark">85 W</span>
```

---

## Comparison: Before → After

### Before (Neon Digital World)

- Pure black backgrounds (#0a0a0f)
- Binary dark/light (no middle ground)
- Heavy neon glows (0.6 alpha)
- Blue/purple/pink accents (generic tech)
- Stark white tables (#f8fafc)
- User feedback: "painful to eyes" then "feels generic"

### After (Workshop for Thought)

- Warm charcoal (#1a1816)
- 7 tonal levels (smooth transitions)
- Soft elevation shadows
- Burnt orange/teal (distinctive, meaningful)
- Warm paper tables (#e8e4df)
- Goal: Comfortable, distinctive, defensible

---

## Brand Coherence

Despite mixed surfaces (dark/light), design maintains unity through:

1. **Warm temperature** - All tones have subtle brown/orange undertone
2. **Typography** - Inter + JetBrains Mono throughout
3. **Domain colors** - Orange fitness, teal finance (consistent)
4. **Spacing system** - 8-12px grouping, 24-32px separation
5. **Border treatment** - 1px default, 2px active
6. **Shadow style** - Soft, physical (not neon glows)

---

## Portfolio Narrative

**Story arc:**
"I initially implemented a high-contrast neon aesthetic based on user feedback for 'game-like energy.' User returned with 'too painful' then 'too generic' after corrections. This led me to research vision science (positive polarity effect), color psychology, and Material Design principles. The breakthrough came from reframing the problem: instead of 'dark mode vs light mode,' I designed a unified tonal system inspired by physical workspaces—the 'Workshop for Thought' palette. This uses 7 levels of warm neutrals (charcoal to paper) with selective domain colors as data markup. The result differentiates from typical tech dashboards while serving the cognitive prosthetic metaphor."

**Key decisions:**
- Tonal depth (7 levels) over binary contrast
- Warm neutrals (grounded) over cool grays (sterile)
- Color as emphasis (data markup) not decoration
- Material shadows (physical) over neon glows (artificial)

**Research grounding:**
- Piepenbrock (2014): Positive polarity for reading
- Material Design 3: Tonal elevation
- Color psychology: Warm = approachable, cool = professional

---

## Files Updated

### Core System
- `globals.css` - Complete color system rebuild (7 levels, warm palette)

### Components
- `Shell.tsx` - Warm charcoal base, domain-tinted grids
- `Sidebar.tsx` - Level 2 background, warm active states
- `Home.tsx` - Warm charcoal cards
- `Transactions.tsx` - Light table with warm paper background
- `Summary.tsx` - Dark metrics, light category table
- `History.tsx` - Dark master list, light detail panel
- `Log.tsx` - Dark drop zone, light results panel
- `Import.tsx` - Dark drop zone, warm result cards

---

## Design Maturity Signals

This design demonstrates:

1. **Systems thinking** - 7-level palette, not ad-hoc colors
2. **Metaphor coherence** - Workshop aesthetic carried through
3. **Evidence-based decisions** - Research citations for light/dark choices
4. **Iteration from feedback** - Painful → Generic → Distinctive
5. **Defensible rationale** - Every color has functional purpose
6. **Pattern awareness** - Material Design, Linear precedents
7. **Craft identity** - Aligns with "builder" personal philosophy

**Interview value:** Shows design sophistication beyond applying templates.
