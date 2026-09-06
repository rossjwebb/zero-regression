# Claude Max raw Stage D design — 2026-09-06

Claude · Max (Opus 5) produced three candidate designs
(https://claude.ai/chat/6f4ed17a-5001-40ee-969d-e5a28147091f).
`CLAUDE_MAX_DESIGN_COMPLETE` candidates=3. Design-only.

Price raw designs already use the pin constructor
(`currency`, `excl_tax`, `incl_tax`, `tax`) but omit `incl_tax=None`
when tax is unknown (`AttributeError` instead of the pin's `None`).
They also add operators the pin does not have.

`weak-profits-clamp-nonneg` is a design note, not a drop-in
`calculators.py`. The pin lives at
`legacy/accounting/apps/books/calculators.py`.

These files are the unedited design artefacts. Evaluable candidates
under `../candidates/` are pin-API adaptations that keep Max's
stated intents. Method attribution lives in `arm.json`.

Not paper S1. No mutation score.
