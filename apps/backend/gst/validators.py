"""
P14/M-1 — Singapore identity-number format validators.

UEN (Unique Entity Number) per the ACRA-published FORMAT set:
  * Businesses (ROB):          8 digits + 1 check letter            (9 chars)
  * Local companies:           9 digits + 1 check letter           (10 chars)
  * Other entities (T/S-issued): T|S + YY + 2 entity letters + 4 digits + check letter (10 chars)

GST registration number per IRAS: EITHER the M-form (M + 8 digits +
check letter) OR the UEN-form (a valid UEN). IRAS states a GST number
may be either form; the pre-P14 startswith("M") check rejected valid
UEN-form GST numbers.

Honesty note (deferred, registered): FORMAT validation only. The ACRA
check-letter algorithm is not an officially published specification —
inventing one would reject valid numbers. Checksum verification is a
recorded P15 decision pending the official algorithm. The bare
all-numeric 10-digit pattern (branch registrations) is NOT a UEN and is
rejected with the others.
"""

import re

_UEN_BUSINESS = re.compile(r"^\d{8}[A-Z]$")            # 12345678A
_UEN_LOCAL_COMPANY = re.compile(r"^\d{9}[A-Z]$")       # 202612345D
_UEN_OTHER_ENTITY = re.compile(r"^[TS]\d{2}[A-Z]{2}\d{4}[A-Z]$")  # T08LL1234A

_UEN_PATTERNS = (_UEN_BUSINESS, _UEN_LOCAL_COMPANY, _UEN_OTHER_ENTITY)

_GST_M_FORM = re.compile(r"^M\d{8}[A-Z]$")             # M90345678K


def validate_uen(uen: str) -> bool:
    """True when `uen` matches one of the three ACRA UEN formats."""
    if not uen:
        return True  # optional field — empty is valid
    cleaned = uen.strip().upper()
    return any(p.match(cleaned) for p in _UEN_PATTERNS)


def validate_gst_reg_number(value: str) -> bool:
    """True when `value` is the IRAS M-form or a valid UEN-form GST number."""
    if not value:
        return True  # optional field — empty is valid
    cleaned = value.strip().upper()
    if _GST_M_FORM.match(cleaned):
        return True
    return validate_uen(cleaned)
