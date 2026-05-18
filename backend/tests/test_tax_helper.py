from decimal import Decimal

import pytest

from app.core.tax import split_amount


@pytest.mark.parametrize(
    "amount,inclusive,exp_untaxed,exp_tax,exp_total",
    [
        # Exclusive (未稅 → 加 5%)
        ("100.00", False, "100.00", "5.00", "105.00"),
        ("1000.00", False, "1000.00", "50.00", "1050.00"),
        ("99.99", False, "99.99", "5.00", "104.99"),  # round half up
        ("0.10", False, "0.10", "0.01", "0.11"),
        # Inclusive (含稅 → 拆稅)
        ("105.00", True, "100.00", "5.00", "105.00"),
        ("1050.00", True, "1000.00", "50.00", "1050.00"),
        ("100.00", True, "95.24", "4.76", "100.00"),  # peel out 5%
        # Identity: applying inclusive(105) inverts exclusive(100)
    ],
)
def test_split_amount(amount, inclusive, exp_untaxed, exp_tax, exp_total):
    untaxed, tax, total = split_amount(Decimal(amount), inclusive=inclusive)
    assert untaxed == Decimal(exp_untaxed)
    assert tax == Decimal(exp_tax)
    assert total == Decimal(exp_total)


def test_split_amount_invariant_untaxed_plus_tax_equals_total():
    """Whatever the rounding does, untaxed + tax must always equal total."""
    for cents in [1, 7, 13, 99, 333, 1234, 99999]:
        for inclusive in [False, True]:
            amt = Decimal(cents) / Decimal("100")
            u, t, tot = split_amount(amt, inclusive=inclusive)
            assert u + t == tot, f"violated for {amt} inclusive={inclusive}"
