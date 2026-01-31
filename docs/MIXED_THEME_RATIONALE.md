# Voku Mixed-Theme Design: Functional Rationale

**Date:** January 25, 2026  
**Version:** v0.2+  
**Design Philosophy:** Content-driven theming based on vision science and cognitive psychology

---

## Executive Summary

Voku implements a **content-driven mixed-theme interface** where background luminance is determined by content type rather than user preference. This approach is grounded in evidence from cognitive psychology (Piepenbrock et al., 2013-2014), vision science (Helmholtz-Kohlrausch effect), and modern design systems (Material Design 3, Linear).

**Core Principle:** Light surfaces for text-heavy content (positive polarity effect), dark surfaces for navigation/glanceable metrics (spatial recession + color salience).

---

## Implementation Map

### Light Surfaces (Text-Heavy Content)

| Component | Rationale | Research Support |
|-----------|-----------|------------------|
| **Transactions Table** | Highest text density: merchant names, dates, categories. Sustained scanning behavior. | Piepenbrock (2014): 20-26% reading speed advantage for positive polarity |
| **Summary Category Table** | Text-heavy breakdown with merchant categories requiring careful review | Dobres et al. (2017): 18% faster judgment time in light mode |
| **History Detail Panel** | Metric names and values require focus when analyzing workout performance | Material Design 3: Tonal elevation - "higher surfaces are lighter" |

### Dark Surfaces (Glanceable + Navigation)

| Component | Rationale | Research Support |
|-----------|-----------|------------------|
| **Sidebar** | Navigation chrome should recede, not compete with content | Linear: "opacities of black and white" for elevation hierarchy |
| **Summary Metric Cards** | Large display numbers ($801.20), glanceable not sustained reading | Helmholtz-Kohlrausch: Colors appear brighter on dark backgrounds |
| **History Session List** | Master-detail pattern: dark for navigation, light for content | Apple HIG: Base colors for receding interfaces |
| **Page Backgrounds** | Ambient "digital world" with grid texture | Creates spatial depth through luminance contrast |

---

## Research Evidence

### 1. Reading Performance (Positive Polarity Effect)

**Finding:** Dark text on light backgrounds produces 20-26% faster reading speed and higher comprehension accuracy.

**Mechanism:** Higher screen luminance causes pupil constriction, reducing spherical aberrations and creating sharper retinal imaging. Effect scales with text size—smaller fonts show greater advantage.

**Citations:**
- Piepenbrock et al. (2013) *Human Factors*: "Positive display polarity is particularly advantageous for small character sizes"
- Piepenbrock et al. (2014) *Ergonomics*: "Smaller pupil size and better proofreading performance with positive than with negative polarity displays"
- Dobres et al. (2017) MIT AgeLab: 18% longer task time in dark mode for nighttime reading
- Sethi & Ziat (2023) *Ergonomics*: Higher cognitive load in dark mode reflected in pupil diameter

### 2. Data Visualization (Helmholtz-Kohlrausch Effect)

**Finding:** Saturated colors appear brighter at equivalent luminance on dark backgrounds. Professional dashboards (Bloomberg, Grafana, Power BI) default to dark for this reason.

**Mechanism:** On dark backgrounds, colorful elements don't compete with ambient luminance, creating stronger perceptual "pop" for data points.

**Citations:**
- Bloomberg Terminal (2021): Shifted to "brighter and more saturated colors" on dark for color vision deficiency users
- Grafana design team: "Dark colors suit better the observability purpose"
- Power BI documentation: "Layering colorful visualizations on top of a dark background helps data stand out"

### 3. Spatial Hierarchy (Tonal Elevation)

**Finding:** Mixed-surface interfaces communicate depth through luminance contrast. Light surfaces advance (content), dark surfaces recede (chrome).

**Citations:**
- Material Design 3: Tonal elevation system—surfaces get lighter as they move toward user
- Linear: LCH color space for perceptually uniform theme generation across 98+ variables
- Apple HIG: Two-level background system (base/elevated) with automatic switching

### 4. The Preference-Performance Gap

**Critical Finding:** User preference doesn't predict user performance. 2025 study found cognitive test scores higher in light mode across all groups, yet no significant differences based on stated preference.

**Implication:** Evidence-based design decisions prioritize measured outcomes over stated preferences.

**Citations:**
- Taylor & Francis (2025): 173 participants, higher cognitive scores in light mode regardless of preference
- Ettling et al. (2025): Pupil dilation higher in dark mode (cognitive load) despite lower perceived workload
- Nielsen Norman Group: ~33% prefer light, 33% prefer dark, 33% context-dependent

---

## Interview Defense Framework

### Q: "Why mix light and dark surfaces?"

**Answer:** "I implemented content-driven theming based on Piepenbrock's research showing 20-26% reading performance advantage for positive polarity displays—dark text on light backgrounds—especially for text-heavy content. The transaction table has highest text density with merchant names and dates, so it got light treatment to optimize scanning speed. Summary metrics stayed dark because they're glanceable display numbers where the Helmholtz-Kohlrausch effect benefits color salience against dark backgrounds. History uses master-detail pattern: dark list for navigation chrome, light detail panel for content—following Material Design's tonal elevation principles. This creates spatial hierarchy through luminance contrast while maintaining the neon aesthetic for data-focused components."

**Demonstrates:**
- Specific research citations (not just "best practice")
- Content-type driven decisions (not blanket theme)
- Awareness of vision science (pupil constriction, color perception)
- Pattern precedents (Material, Linear)
- Tradeoff reasoning (performance vs aesthetic)

### Q: "How did you decide which components get which treatment?"

**Answer:** "I conducted content inventory analysis. Text-heavy components with sustained scanning behavior—transaction tables, category breakdowns, metric detail panels—received light backgrounds to leverage the positive polarity effect. Navigation chrome and glanceable metrics stayed dark for two reasons: spatial recession (sidebar should recede, not compete) and color salience (large display numbers benefit from the Helmholtz-Kohlrausch effect where colors appear brighter on dark). The research shows reading speed improves 20-26% with positive polarity, but that advantage only matters for actual reading tasks, not quick glances at numbers."

### Q: "Users prefer dark mode though—why go against preference?"

**Answer:** "Actually, the preference-performance gap is well documented. A 2025 study with 173 participants found cognitive test scores were significantly higher in light mode across all demographic groups, yet user preferences showed no correlation with performance. Users reported feeling less fatigued in dark mode while their pupil dilation indicated higher cognitive load. This demonstrates why evidence-based design decisions prioritize measured outcomes over stated preferences. I designed for performance where it matters—text-heavy content—while respecting aesthetic coherence with selective dark surfaces for navigation and data visualization."

### Q: "What about accessibility?"

**Answer:** "Light surfaces enable stronger contrast ratios. WCAG requires 4.5:1 for body text, but light backgrounds allow me to achieve 7:1 with dark gray text (#0f172a on #f8fafc), exceeding AA standards. For badge colors on light tables, I created darker, more saturated variants specifically adjusted for light backgrounds—for example, orange badges use #c2410c instead of #fb923c, maintaining semantic color mapping while ensuring readability. The dark surfaces maintain 3:1 for graphical elements. I'm also aware of APCA (Advanced Perceptual Contrast Algorithm) anticipated for WCAG 3.0, which addresses flaws in current contrast calculations."

---

## Technical Implementation

### Color System (globals.css)

```css
/* Light surface variables */
--bg-light: #f8fafc;           /* Off-white, not pure white */
--bg-light-hover: #f1f5f9;     /* Hover state */
--bg-light-elevated: #ffffff;  /* Elevated surfaces */

/* Text on light surfaces */
--text-on-light: #0f172a;              /* 7:1 contrast ratio */
--text-on-light-secondary: #475569;    /* Secondary text */
--text-on-light-muted: #64748b;        /* Muted text */
```

### Utility Classes

```css
.card-light {
  background: var(--bg-light);
  color: var(--text-on-light);
  border: 1px solid #e2e8f0;
}

.card-light:hover {
  background: var(--bg-light-hover);
}
```

### Badge Color Adjustment

Dark background badges use bright, desaturated colors (e.g., #fb923c).  
Light background badges use dark, saturated colors (e.g., #c2410c).

This maintains semantic mapping (orange = food) while ensuring readability on different backgrounds.

---

## Future Considerations

### Chat Interface (Planned v0.3+)

When chat with subagents becomes functional, conversation bubbles will use **light surfaces** for the same reason—sustained reading of AI responses.

**Pattern:** 
- User messages: Light bubble on dark background (advances forward)
- AI messages: Light bubble on dark background (content focus)
- Chat chrome: Dark background with grid (recedes)

**Research support:** Positive polarity effect is strongest for extended reading sessions, which chat interfaces enable.

### Forms and Input Fields

Currently not styled for light surfaces. Future work should apply light treatment to form-heavy pages (Import, Log) for consistency.

**Principle:** If user is inputting or reviewing text fields, light surface optimizes that interaction.

---

## Design Coherence Maintained

Despite mixed theming, Voku maintains visual coherence through:

1. **Domain Color Identity:** Orange/red for fitness, cyan/violet for finance (consistent across all surfaces)
2. **Typography:** Inter + JetBrains Mono (unchanged)
3. **Spacing:** Gestalt proximity principles (8-16px grouping)
4. **Neon Accents:** Selective use of glows and gradient borders on focal points
5. **Grid Pattern:** Ambient texture on all dark backgrounds
6. **Border System:** 1px default, 2px for active states

---

## Metrics for Success

### Qualitative (Portfolio Review)
- "Demonstrates awareness of vision science"
- "Evidence-based decision framework"
- "Sophisticated understanding of modern design systems"

### Quantitative (If Measured)
- Reading speed on transaction table vs previous dark version
- Error rate on category identification
- Time to complete multi-step workflows

---

## References

**Primary Research:**
- Piepenbrock, C., Mayr, S., & Buchner, A. (2013). "Positive Display Polarity Is Particularly Advantageous for Small Character Sizes." *Human Factors*, 56(5), 942-951.
- Piepenbrock, C., Mayr, S., & Buchner, A. (2014). "Smaller pupil size and better proofreading performance with positive than with negative polarity displays." *Ergonomics*, 57(11), 1670-1677.
- Dobres, J., Wolfe, B., Chahine, N., & Reimer, B. (2017). "The Effect of Display Polarity on Glance Duration in Automotive Applications." *MIT AgeLab*.
- Sethi, A., & Ziat, M. (2023). "The dark side of the interface: examining the influence of different background modes on cognitive performance." *Ergonomics*.
- Ettling, J. et al. (2025). "An Eye Tracking Study on the Effects of Dark and Light Themes on User Performance and Workload." *ACM Symposium on Eye Tracking*.

**Design Systems:**
- Material Design 3: Tonal Elevation System
- Linear: LCH Color Space and Variable Generation
- Apple Human Interface Guidelines: Dark Mode Principles
- Bloomberg Terminal: Color Accessibility Documentation

**Industry Resources:**
- Nielsen Norman Group: Dark Mode vs. Light Mode Research
- W3C WCAG 2.1 & APCA (Advanced Perceptual Contrast Algorithm)
- Helmholtz-Kohlrausch Effect (vision science literature)

---

## Change Log

**2026-01-25:** Initial implementation
- ✅ Light surfaces: Transactions table, Summary category table, History detail panel
- ✅ Dark surfaces: Sidebar, metric cards, session list, page backgrounds
- ✅ Badge color system adjusted for both light and dark backgrounds
- ✅ Utility classes created in globals.css
- ✅ Documentation created for interview defense

---

## Next Steps

1. **Phase 3:** Apply light treatment to Import and Log pages (form-heavy)
2. **Phase 4:** Design chat interface with light conversation bubbles
3. **Usability Testing:** Measure reading speed on transaction table
4. **Documentation:** Add screenshots to design system docs
5. **Portfolio:** Create case study highlighting evidence-based approach
