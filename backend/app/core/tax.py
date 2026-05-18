"""Taiwan VAT (營業稅) helpers — fixed at 5% for the MVP."""
from decimal import ROUND_HALF_UP, Decimal

TAX_RATE = Decimal("0.05")
ONE_PLUS_RATE = Decimal("1.05")
TWO_DP = Decimal("0.01")


def split_amount(amount: Decimal, *, inclusive: bool) -> tuple[Decimal, Decimal, Decimal]:
    """Split an order amount into (untaxed, tax, total).

    ``inclusive=True``  → input ``amount`` is already 含稅 (total). Peel the tax out.
    ``inclusive=False`` → input ``amount`` is 未稅 (untaxed). Add the tax on top.

    All results are 2-decimal-place Decimals; tax is rounded half-up.
    """
    amount = Decimal(amount)
    if inclusive:
        amount_total = amount.quantize(TWO_DP, rounding=ROUND_HALF_UP)
        amount_untaxed = (amount / ONE_PLUS_RATE).quantize(TWO_DP, rounding=ROUND_HALF_UP)
        tax_amount = amount_total - amount_untaxed
    else:
        amount_untaxed = amount.quantize(TWO_DP, rounding=ROUND_HALF_UP)
        tax_amount = (amount_untaxed * TAX_RATE).quantize(TWO_DP, rounding=ROUND_HALF_UP)
        amount_total = amount_untaxed + tax_amount
    return amount_untaxed, tax_amount, amount_total
