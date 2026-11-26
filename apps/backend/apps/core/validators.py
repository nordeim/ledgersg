"""
P14/M-1 — Singapore identity-number format validators.

UEN (Unique Entity Number) per the ACRA-published FORMAT set
(OECD "Information on Tax Identification Numbers: Singapore", Section II):
  * Businesses (ROB):              8 digits + 1 check letter              (9 chars)
  * Local companies (ROC):         YYYY + 5 digits + 1 check letter       (10 chars)
  * Other entities (T/S-issued):  T|S + YY + 2 entity letters + 4 digits + check letter (10 chars)

GST registration number per IRAS: EITHER the M-form OR the UEN-form
(IRAS "Invoicing customers" shows the UEN-form example "123456789A").
The M-form exists in TWO lengths, both documented:
  * OECD TIN guide:  ASGD = ANNNNNNNC  — M + 7 digits + check letter  (9 chars)
  * real-world IRAS-issued numbers on company documents are
    M + 8 digits + check letter (10 chars, e.g. M90356174N on FSM
    Global's statutory forms, M90001281J on SIA's) — both lengths are
    accepted (format-only; no invented checksum).

Honesty note (deferred, registered): FORMAT validation only. The ACRA
check-letter algorithm is not an officially published specification —
inventing one would reject valid numbers. Checksum verification is a
recorded P16 decision pending the official algorithm. The bare
all-numeric 10-digit pattern (branch registrations) is NOT a UEN and is
rejected with the others. F-form foreign-company UENs (F000NNNNNC /
FDDDNNNNNC per the OECD guide) are out of scope — registered as a P16
onboarding decision.
"""

import re

_UEN_BUSINESS = re.compile(r"^\d{8}[A-Z]$")            # 12345678A
_UEN_LOCAL_COMPANY = re.compile(r"^\d{9}[A-Z]$")       # 202612345D
_UEN_OTHER_ENTITY = re.compile(r"^[TS]\d{2}[A-Z]{2}\d{4}[A-Z]$")  # T08LL1234A

_UEN_PATTERNS = (_UEN_BUSINESS, _UEN_LOCAL_COMPANY, _UEN_OTHER_ENTITY)

# M-form GST numbers: M + 7 digits + check letter (OECD, 9 chars) OR
# M + 8 digits + check letter (real-world IRAS-issued, 10 chars).
_GST_M_FORM = re.compile(r"^M\d{7,8}[A-Z]$")           # M1234567A / M90345678K


def validate_uen(uen: str) -> bool:
    """True when `uen` matches one of the three ACRA UEN formats."""
    if not uen:
        return True  # optional field — empty is valid
    cleaned = uen.strip().upper()
    return any(p.match(cleaned) for p in _UEN_PATTERNS)


def validate_gst_reg_number(value: str) -> bool:
    """True when `value` is the IRAS M-form (either length) or a valid
    UEN-form GST number."""
    if not value:
        return True  # optional field — empty is valid
    cleaned = value.strip().upper()
    if _GST_M_FORM.match(cleaned):
        return True
    return validate_uen(cleaned)
