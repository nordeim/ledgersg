"""
Shared ISO-4217 currency-code truth (P34/BE-P34-M1).

Pre-P34 every currency input surface validated only string length — a
typo like "XYZ"/"SGE" (or a 2-char "US" on the org-create path) reached
the database and propagated into the P33 currency-truth surfaces: the
financial-reports denomination, the Peppol DocumentCurrencyCode + every
amount currencyID, and the invoice PDF.

This module is the single vocabulary every currency input shares. The
allowlist is the set of ACTIVE ISO-4217 currency codes relevant to a
business accounting platform: the national currencies, excluding the
codes that carry no business meaning here — the placeholders XXX ("no
currency") and XTS ("testing") and the supranational/precious-metal
units (XDR, XAU, XAG, XPD, XPT). Withdrawn codes (HRK, ANG, ZWL, SLL,
VED-era VEF, ...) are deliberately absent. Codes are matched
case-insensitively and normalised to upper case on the way in.
"""

ISO_4217_ACTIVE_CODES: frozenset[str] = frozenset({
    # — Major trading currencies first (the LedgerSG defaults + region) —
    "SGD", "USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CHF", "CAD",
    "HKD", "MYR", "IDR", "THB", "INR", "CNY", "KRW", "TWD", "PHP", "VND",
    # — Rest of the active ISO-4217 national currencies (alphabetical) —
    "AED", "AFN", "ALL", "AMD", "AOA", "ARS", "AWG", "AZN",
    "BAM", "BBD", "BDT", "BGN", "BHD", "BIF", "BMD", "BND", "BOB", "BRL",
    "BSD", "BTN", "BWP", "BYN", "BZD",
    "CDF", "CLP", "COP", "CRC", "CUP", "CZK",
    "DJF", "DKK", "DOP", "DZD",
    "EGP", "ERN", "ETB",
    "FJD", "FKP",
    "GEL", "GHS", "GIP", "GMD", "GNF", "GTQ", "GYD",
    "HNL", "HTG", "HUF",
    "ILS", "IQD", "IRR", "ISK",
    "JMD", "JOD",
    "KES", "KGS", "KHR", "KMF", "KPW", "KWD", "KYD", "KZT",
    "LAK", "LBP", "LKR", "LRD", "LSL", "LYD",
    "MAD", "MDL", "MGA", "MKD", "MMK", "MNT", "MOP", "MRU", "MUR", "MVR",
    "MWK", "MZN",
    "NAD", "NGN", "NIO", "NOK", "NPR",
    "OMR",
    "PAB", "PEN", "PGK", "PKR", "PLN", "PYG",
    "QAR",
    "RON", "RSD", "RUB", "RWF",
    "SAR", "SBD", "SCR", "SDG", "SEK", "SHP", "SLE", "SOS", "SRD", "SSP",
    "STN", "SVC", "SYP", "SZL",
    "TJS", "TMT", "TND", "TOP", "TRY", "TTD", "TZS",
    "UAH", "UGX", "UYU", "UZS",
    "VES", "VUV",
    "WST",
    "XAF", "XCD", "XCG", "XOF", "XPF",
    "YER",
    "ZAR", "ZMW", "ZWG",
})

#: The codes deliberately excluded from the allowlist (documented
#: decision): XXX = "no currency" and XTS = "testing" (valid ISO-4217
#: table codes with no business meaning for a platform whose every
#: monetary surface assumes a real denomination), plus the
#: supranational/precious-metal units (XDR, XAU, XAG, XPD, XPT) that an
#: SMB accounting platform does not denominate documents in.
_EXCLUDED_PLACEHOLDER_CODES: frozenset[str] = frozenset({
    "XXX", "XTS", "XDR", "XAU", "XAG", "XPD", "XPT",
})


def normalize_currency_code(code: str | None) -> str | None:
    """
    Normalise and vocabulary-check a currency input.

    Args:
        code: the raw input (any case, possibly padded)

    Returns:
        The upper-cased code when it is an ACTIVE ISO-4217 currency,
        otherwise None. Empty input returns None (callers with optional
        currency fields keep their own default handling before calling).
    """
    if not code:
        return None
    normalized = code.strip().upper()
    if normalized in ISO_4217_ACTIVE_CODES:
        return normalized
    return None
