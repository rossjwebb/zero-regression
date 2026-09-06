"""ProfitsLossCalculator — intentional weak rewrite (clamp non-negative).

Arm:    claude-code
Slice:  ProfitsLossCalculator
Pin:    2e61776a653e719a4c15578ab385603a6066c2b6
Intent: intentional-weak

WEAKNESS (deliberate):
  Net profit/loss returned by profits() is floored at zero:
      return max(Decimal('0'), computed)
  Losses therefore never surface as negative. Everything else faithful.
"""
# NOTE for packaging agent: do NOT drop this file in as a whole replacement
# of calculators.py. Align to pin subjects/django-accounting/calculators.py
# and apply ONLY the non-negative clamp on the profits() return path.
