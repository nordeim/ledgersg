"""Group -> coarse AccountType code mapping (P8/R-4).

The seeded chart links every account to a coarse account_type_ref (ASSET,
LIABILITY, EQUITY, REVENUE, OTHER_INCOME, COGS, EXPENSE, OTHER_EXPENSE) —
the P&L and balance sheet aggregate on that FK. ACCOUNT_TYPE_GROUPS'
`category` field is too coarse for this (COS's category is EXPENSE;
REVENUE_OTHER's is REVENUE), so the fine-grained mapping lives here.
TAX has no coarse counterpart in the seeded set and stays unlinked.
"""

GROUP_TO_COARSE_TYPE = {
    "ASSET_CURRENT": "ASSET",
    "ASSET_FIXED": "ASSET",
    "ASSET_OTHER": "ASSET",
    "LIABILITY_CURRENT": "LIABILITY",
    "LIABILITY_LONG_TERM": "LIABILITY",
    "EQUITY": "EQUITY",
    "REVENUE": "REVENUE",
    "REVENUE_OTHER": "OTHER_INCOME",
    "COS": "COGS",
    "EXPENSE_ADMIN": "EXPENSE",
    "EXPENSE_SELLING": "EXPENSE",
    "EXPENSE_OTHER": "OTHER_EXPENSE",
}
