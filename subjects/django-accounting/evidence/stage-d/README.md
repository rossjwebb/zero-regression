# S1 Stage D

Rewrite generators versus the Stage C discriminating yardstick.
Not paper S1. `mutation_score=not-stored`.

```bash
python3.12 subjects/django-accounting/oracle.py
python3.12 subjects/django-accounting/check-discrimination.py
python3.12 subjects/django-accounting/evidence/stage-d/evaluate-candidate.py --candidate price-faithful
python3.12 subjects/django-accounting/check-stage-d.py
```

Cursor candidates are under `arms/cursor/candidates/`. Claude Code
and Gemini slots are `awaiting-external-run` with PROMPT.md files.
Do not edit `legacy/`.
