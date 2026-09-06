# S1 Stage D

Rewrite generators versus the Stage C discriminating yardstick.
Not paper S1. `mutation_score=not-stored`.

```bash
python3.12 subjects/django-accounting/oracle.py
python3.12 subjects/django-accounting/check-discrimination.py
python3.12 subjects/django-accounting/evidence/stage-d/evaluate-candidate.py --candidate price-faithful
python3.12 subjects/django-accounting/check-stage-d.py
```

Cursor candidates are under `arms/cursor/candidates/`. Gemini
receipts under `arms/gemini/` stay historical (#23), including the
weak-profits accept. Claude Code stays `awaiting-external-run`.
Stage C live invariants include an expenses>collected org so
clamp-to-zero `profits()` is rejected without widening the golden
and without rewriting those Gemini receipts. Do not edit `legacy/`.
