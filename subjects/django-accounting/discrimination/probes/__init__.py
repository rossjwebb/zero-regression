# SPDX-License-Identifier: Apache-2.0
"""Known-bad probes for the S1 Stage C discrimination gate.

Each probe patches pin callables already exercised by the 27-trace
replay. Probes must not edit ``legacy/``. ``golden_echo`` is the
meta-check: it returns ``expected.json`` without calling the pin.
"""

KNOWN_BAD = (
    "bad_price_tax_zero",
    "bad_fully_paid",
    "bad_profits",
)

# Replay case that must appear in oracle stderr when the probe is installed.
EXPECTED_MISMATCH_CASE = {
    "bad_price_tax_zero": "price_from_tax",
    "bad_fully_paid": "invoice_fully_paid",
    "bad_profits": "profits_period_2024_jan_feb",
}

GOLDEN_ECHO = "golden_echo"
