# S1 Stage D

Rewrite generators versus the Stage C discriminating yardstick.
Not paper S1. `mutation_score=not-stored`.

```bash
python3.12 subjects/django-accounting/oracle.py
python3.12 subjects/django-accounting/check-discrimination.py
python3.12 subjects/django-accounting/evidence/stage-d/evaluate-candidate.py --candidate price-faithful
python3.12 subjects/django-accounting/check-stage-d.py
```

Cursor candidates are under `arms/cursor/candidates/`. Gemini has
live receipts under `arms/gemini/`. Claude Code stays
`awaiting-external-run` with a PROMPT.md file. The live invariant
bundle includes an expenses>collected org so clamp-to-zero
`profits()` is rejected without widening the golden. Do not edit
`legacy/`.
