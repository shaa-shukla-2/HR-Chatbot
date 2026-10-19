from datetime import date
from decimal import Decimal

import pytest

from app.hr.policy_tools import (
    calculate_incentive,
    completed_months,
    format_inr,
    format_leave_balance,
    leave_balance,
    to_rupees,
)


# ---- formatting ---------------------------------------------------------
@pytest.mark.parametrize(
    "amount, expected",
    [
        (999, "₹999"),
        (45000, "₹45,000"),
        (150000, "₹1,50,000"),
        (9000000, "₹90,00,000"),
        (1234.5, "₹1,234.50"),
        (0, "₹0"),
    ],
)
def test_format_inr(amount, expected):
    assert format_inr(amount) == expected


def test_to_rupees():
    assert to_rupees(90, "lakh") == Decimal("9000000")
    assert to_rupees(1.5, "crore") == Decimal("15000000")
    assert to_rupees(250000) == Decimal("250000")
    with pytest.raises(ValueError):
        to_rupees(5, "million")


# ---- incentive ----------------------------------------------------------
def test_residential_90_lakh_is_not_capped():
    r = calculate_incentive(to_rupees(90, "lakh"), "residential")
    assert r.amount == Decimal("45000.00")
    assert r.capped is False


def test_residential_cap_starts_above_3_crore():
    exactly = calculate_incentive(to_rupees(3, "crore"), "residential")
    assert exactly.amount == Decimal("150000.00") and exactly.capped is False
    above = calculate_incentive(to_rupees(3.5, "crore"), "residential")
    assert above.uncapped == Decimal("175000.00")
    assert above.amount == Decimal("150000") and above.capped is True


def test_commercial_rate_and_cap():
    assert calculate_incentive(to_rupees(1, "crore"), "commercial").amount == Decimal("75000.00")
    capped = calculate_incentive(to_rupees(3, "crore"), "commercial")
    assert capped.uncapped == Decimal("225000.00")
    assert capped.amount == Decimal("150000") and capped.capped is True


def test_incentive_accepts_mixed_case_type():
    assert calculate_incentive(1000000, " Residential ").amount == Decimal("5000.00")


@pytest.mark.parametrize("bad_type", ["", "plots", None])
def test_incentive_rejects_bad_type(bad_type):
    with pytest.raises(ValueError):
        calculate_incentive(1000000, bad_type)


@pytest.mark.parametrize("bad_value", [0, -5])
def test_incentive_rejects_non_positive_value(bad_value):
    with pytest.raises(ValueError):
        calculate_incentive(bad_value, "residential")


def test_incentive_text_cites_policy_and_mentions_closing_rule():
    text = calculate_incentive(to_rupees(90, "lakh"), "residential").as_text()
    assert "₹45,000" in text
    assert "HR-POL-04, Section 3.2" in text
    assert "HR-POL-04, Section 3.3" in text
    assert "capped" not in text


def test_incentive_text_mentions_cap_when_capped():
    text = calculate_incentive(to_rupees(5, "crore"), "residential").as_text()
    assert "capped at ₹1,50,000" in text


# ---- leave --------------------------------------------------------------
def test_completed_months():
    joined = date(2024, 1, 15)
    # 15 Jan 2024 -> 15 Oct 2026 is 2 years 9 months = 33 full months
    assert completed_months(joined, date(2026, 10, 16)) == 33
    assert completed_months(joined, date(2026, 10, 15)) == 33
    assert completed_months(joined, date(2026, 10, 14)) == 32  # one day short of the 33rd month
    assert completed_months(joined, date(2023, 1, 1)) == 0


def test_confirmed_employee_balance():
    # Rahul: 33 months -> 49.5 days would accrue, capped at 30; 6 used -> 24 left
    b = leave_balance(
        joined_on=date(2024, 1, 15), status="confirmed",
        cl_used=5, sl_used=2, el_used=6, as_of=date(2026, 10, 16),
    )
    assert (b.cl_left, b.sl_left) == (Decimal("3"), Decimal("8"))
    assert b.el_accrued == Decimal("30")
    assert b.el_left == Decimal("24")
    assert b.el_usable is True


def test_probation_employee_cannot_use_earned_leave():
    # Priya: 3 months -> 4.5 days accrued but not usable yet
    b = leave_balance(
        joined_on=date(2026, 7, 1), status="probation",
        cl_used=2, sl_used=1, el_used=0, as_of=date(2026, 10, 16),
    )
    assert b.cl_left == Decimal("6") and b.sl_left == Decimal("9")
    assert b.el_accrued == Decimal("4.5")
    assert b.el_usable is False


def test_balance_never_goes_negative():
    b = leave_balance(
        joined_on=date(2024, 1, 15), status="confirmed",
        cl_used=12, sl_used=15, el_used=99, as_of=date(2026, 10, 16),
    )
    assert b.cl_left == b.sl_left == b.el_left == Decimal("0")


def test_leave_text_confirmed_and_probation():
    conf = leave_balance(
        joined_on=date(2024, 1, 15), status="confirmed",
        cl_used=5, sl_used=2, el_used=6, as_of=date(2026, 10, 16),
    )
    text = format_leave_balance("Rahul Sharma", "E1001", conf)
    assert "3 of 8 days left" in text and "8 of 10 days left" in text
    assert "24 days left" in text and "HR-POL-01, Section 2.1" in text

    prob = leave_balance(
        joined_on=date(2026, 7, 1), status="probation",
        cl_used=2, sl_used=1, el_used=0, as_of=date(2026, 10, 16),
    )
    text = format_leave_balance("Priya Nair", "E1002", prob)
    assert "4.5 days accrued" in text and "only after confirmation" in text
