# Gemini raw Stage D design — 2026-09-06

Mindway Gemini produced three candidate designs. They targeted a made-up
Price API (`amount` / `tax_rate` / `ROUND_*`) instead of the pin
`Price(currency, excl_tax, incl_tax=..., tax=...)`, and
`weak-profits-zero-override` had a syntax error
(`def calculate_net_profit((self)`).

These files are the unedited design artefacts. Evaluable candidates
under `../candidates/` are CoS pin-API adaptations that keep Gemini's
stated intents. Method attribution lives in `arm.json`.

Not paper S1. No mutation score.
