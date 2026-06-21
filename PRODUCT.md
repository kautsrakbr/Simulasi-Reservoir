# Product

## Register

product

## Users

Petroleum/reservoir engineers, engineering students, and technical researchers running reservoir simulation cases. They work in long sessions (hours), move repeatedly between setup, validation, run, and results review, and need to trust the numbers without re-deriving them. New users (students, junior engineers) must be able to learn the tool without a manual; experienced users need density and speed once familiar.

## Product Purpose

CoreReservoir is a desktop reservoir simulation application (PySide6) that takes a user from defining a model (grid, PVT, rock/relperm, initial conditions, solver settings) through running a fully-implicit solver to reading numerical and visual results. Success is a user who can tell within seconds whether a model is ready to run, watch a run without feeling the app has hung, and trust that a displayed result is correct and traceable to its inputs.

## Brand Personality

Serious, precise, controlled. Three words: **disciplined, stable, professional**. The target class is enterprise subsurface/engineering software (the professionalism of tools like Petrel or tNavigator, not their literal visual brand) — calm, data-dense, built for hours of focused technical work, never playful or decorative.

## Anti-references

- SaaS marketing dashboards: cheerful gradients, oversized rounded buttons, colorful badge-everything.
- Consumer mobile UI patterns: large corner radii, bouncy motion, icon-only primary actions.
- Generic AI-generated admin templates: purple/cyan gradients, identical shadowed card grids, gray text on tinted backgrounds.
- Anything that reads as a toy or a prototype rather than a tool meant for paid technical work.

## Design Principles

1. **Workflow over object structure** — pages and navigation follow the user's mental model (setup → validate → run → analyze), not the backend class hierarchy.
2. **Status before detail** — every page should let the user answer "is this ready / correct?" in seconds, before they read a single raw number.
3. **Progressive disclosure** — never force all parameters into one long form; group, section, and collapse advanced settings.
4. **Quiet color, loud meaning** — color is reserved for state (ready/warning/error/selected) and one petroleum-blue accent for primary actions; never decorative.
5. **Density without fatigue** — pack real engineering information per screen, but keep alignment, spacing, and hierarchy rigorous enough to stay comfortable for hours.

## Accessibility & Inclusion

- Maintain ≥4.5:1 contrast for body/field text and ≥3:1 for large text against all backgrounds (current cyan-on-light theme needs verification against this bar).
- Visible keyboard focus outline on every interactive control (field, button, tab, table cell) using the dedicated focus color, not a subtle border tint.
- Status must never be conveyed by color alone — pair every status color (ready/warning/error) with a label or icon.
- Respect OS-level reduced-motion where animation is used (status transitions, panel expand/collapse).
