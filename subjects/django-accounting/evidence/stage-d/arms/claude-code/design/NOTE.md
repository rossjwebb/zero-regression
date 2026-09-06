# Claude Max Stage D design note

- Source: Claude · Max (Opus 5), 2026-09-06.
- Chat: https://claude.ai/chat/6f4ed17a-5001-40ee-969d-e5a28147091f
- `CLAUDE_MAX_DESIGN_COMPLETE` candidates=3. Design-only.
- Price raw designs use the pin constructor but omit `incl_tax=None`
  when unknown and add operators the pin does not have.
- `weak-profits-clamp-nonneg` is a design note; the evaluable rewrite
  is aligned to the pin calculator with only a `profits()` clamp.
- Evaluable candidates are pin-API adaptations keeping Max intents.
