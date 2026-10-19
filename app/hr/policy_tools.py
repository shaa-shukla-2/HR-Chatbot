"""Leave-balance and incentive calculations based on the sample HR policies.

Rules come from:
  HR-POL-01 (Leave Policy)   - casual 8, sick 10, earned 1.5/month capped at 30
  HR-POL-04 (Payroll Policy) - incentive 0.5% residential, 0.75% commercial, cap INR 1,50,000

All money uses Decimal, and the numbers come from code, never from the language model.
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

CASUAL_LEAVE_DAYS = Decimal("8")
SICK_LEAVE_DAYS = Decimal("10")
EARNED_LEAVE_PER_MONTH = Decimal("1.5")
EARNED_LEAVE_MAX = Decimal("30")

INCENTIVE_RATES = {"residential": Decimal("0.005"), "commercial": Decimal("0.0075")}
INCENTIVE_CAP = Decimal("150000")

_UNITS = {"": 1, "rupees": 1, "thousand": 1_000, "lakh": 100_000, "lakhs": 100_000, "crore": 10_000_000, "crores": 10_000_000}
_CENT = Decimal("0.01")


# ---------------------------------------------------------------- formatting
def format_inr(amount) -> str:
    """Format a rupee amount with Indian digit grouping, e.g. 150000 -> ₹1,50,000."""
    value = Decimal(str(amount)).quantize(_CENT, rounding=ROUND_HALF_UP)
    sign = "-" if value < 0 else ""
    value = abs(value)
    whole = int(value)
    paise = int((value - whole) * 100)
    digits = str(whole)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups + [tail])
    return f"{sign}₹{digits}" + (f".{paise:02d}" if paise else "")


def _days(value: Decimal) -> str:
    """Show 24 not 24.0, but keep 4.5."""
    return format(value.normalize(), "f")


def to_rupees(amount, unit: str = "") -> Decimal:
    """Convert e.g. (90, 'lakh') or (1.5, 'crore') to rupees."""
    key = (unit or "").strip().lower()
    if key not in _UNITS:
        raise ValueError(f"Unknown unit '{unit}'. Use rupees, thousand, lakh or crore.")
    return Decimal(str(amount)) * _UNITS[key]


# ---------------------------------------------------------------- incentive
@dataclass(frozen=True)
class IncentiveResult:
    agreement_value: Decimal
    deal_type: str
    rate: Decimal
    uncapped: Decimal
    amount: Decimal
    capped: bool

    def as_text(self) -> str:
        pct = (self.rate * 100).normalize()
        lines = [
            f"Deal type: {self.deal_type}; agreement value {format_inr(self.agreement_value)}.",
            f"Rate: {format(pct, 'f')}% of agreement value = {format_inr(self.uncapped)} "
            f"(HR-POL-04, Section 3.2).",
        ]
        if self.capped:
            lines.append(
                f"This exceeds the per-deal cap, so the incentive is capped at "
                f"{format_inr(INCENTIVE_CAP)} (HR-POL-04, Section 3.2)."
            )
        lines.append(f"Incentive: {format_inr(self.amount)}.")
        lines.append(
            "It is payable only once the deal is closed, meaning the agreement is registered and "
            "the Company has received the brokerage payment (HR-POL-04, Section 3.3). "
            "It is paid in the next month's salary cycle (HR-POL-04, Section 3.4)."
        )
        return "\n".join(lines)


def calculate_incentive(agreement_value, deal_type: str) -> IncentiveResult:
    """Incentive for one closed deal. `agreement_value` is in rupees."""
    kind = (deal_type or "").strip().lower()
    if kind not in INCENTIVE_RATES:
        raise ValueError("deal_type must be 'residential' or 'commercial'")
    value = Decimal(str(agreement_value))
    if value <= 0:
        raise ValueError("agreement_value must be greater than zero")
    rate = INCENTIVE_RATES[kind]
    uncapped = (value * rate).quantize(_CENT, rounding=ROUND_HALF_UP)
    amount = min(uncapped, INCENTIVE_CAP)
    return IncentiveResult(value, kind, rate, uncapped, amount, capped=uncapped > INCENTIVE_CAP)


# ---------------------------------------------------------------- leave balance
@dataclass(frozen=True)
class LeaveBalance:
    as_of: date
    cl_left: Decimal
    sl_left: Decimal
    el_accrued: Decimal
    el_left: Decimal
    el_usable: bool


def completed_months(joined_on: date, as_of: date) -> int:
    months = (as_of.year - joined_on.year) * 12 + (as_of.month - joined_on.month)
    if as_of.day < joined_on.day:
        months -= 1
    return max(months, 0)


def leave_balance(
    *, joined_on: date, status: str, cl_used, sl_used, el_used, as_of: date | None = None
) -> LeaveBalance:
    """Remaining leave. Earned Leave is only usable after confirmation (HR-POL-01, 8.2).

    Assumptions kept deliberately simple for the demo: full yearly entitlements with no
    pro-rating for mid-year joiners (the policy does not mention any), and `el_used`
    is the total Earned Leave taken across all years.
    """
    as_of = as_of or date.today()
    months = completed_months(joined_on, as_of)
    accrued = min(EARNED_LEAVE_MAX, EARNED_LEAVE_PER_MONTH * months)
    return LeaveBalance(
        as_of=as_of,
        cl_left=max(Decimal("0"), CASUAL_LEAVE_DAYS - Decimal(str(cl_used))),
        sl_left=max(Decimal("0"), SICK_LEAVE_DAYS - Decimal(str(sl_used))),
        el_accrued=accrued,
        el_left=max(Decimal("0"), accrued - Decimal(str(el_used))),
        el_usable=(status == "confirmed"),
    )


def format_leave_balance(name: str, employee_id: str, balance: LeaveBalance) -> str:
    """Plain-text summary with policy citations, for the Responder to phrase."""
    lines = [
        f"Leave balance for {name} ({employee_id}) as of {balance.as_of.strftime('%d %b %Y')}:",
        f"- Casual Leave: {_days(balance.cl_left)} of {_days(CASUAL_LEAVE_DAYS)} days left "
        f"this year (HR-POL-01, Section 2.1).",
        f"- Sick Leave: {_days(balance.sl_left)} of {_days(SICK_LEAVE_DAYS)} days left "
        f"this year (HR-POL-01, Section 3.1).",
    ]
    if balance.el_usable:
        lines.append(
            f"- Earned Leave: {_days(balance.el_left)} days left "
            f"({_days(balance.el_accrued)} accrued so far, maximum "
            f"{_days(EARNED_LEAVE_MAX)}) (HR-POL-01, Sections 4.1-4.2)."
        )
    else:
        lines.append(
            f"- Earned Leave: {_days(balance.el_accrued)} days accrued so far, but it can be "
            f"used only after confirmation; during probation only Casual and Sick Leave can be "
            f"used (HR-POL-01, Sections 8.1-8.2)."
        )
    return "\n".join(lines)
