#!/usr/bin/env python3
"""Runtime-role RLS smoke (P14/H-7) — the production-role proof.

The documented test/dev stack runs as the SUPERUSER `ledgersg`, which
bypasses RLS entirely — "green suite" says nothing about the runtime DB
role (the 2026-11-24 audit, H-7; C-1 was invisible for exactly this
reason). This script walks the full onboarding-to-F5 business flow
against a live backend that is ALREADY RUNNING with DB_USER=ledgersg_app
(the documented production runtime role, DEPLOYMENT.md §12.3):

    DB_USER=ledgersg_app DB_PASSWORD=<secret> \
        python manage.py runserver 127.0.0.1:8001 --noreload --settings=config.settings.development

then:

    python scripts/rls_smoke.py --base http://127.0.0.1:8001

Assertions: register → create org (C-1: 201, not 500) → contact →
invoice → approve → payment receive/allocate → F5 compute — every step
2xx under RLS. Exits non-zero on the first contract break.

Deterministic idempotency: each run mints a unique email/uen, so the
script can run repeatedly against the same stack.
"""

import argparse
import json
import sys
import uuid
from datetime import date
from decimal import Decimal

import requests

STEPS = []


def step(name, ok, detail=""):
    STEPS.append((name, ok, detail))
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8001")
    args = ap.parse_args()
    base = args.base.rstrip("/")
    api = f"{base}/api/v1"
    s = requests.Session()
    run = uuid.uuid4().hex[:8]

    # 0. health
    r = s.get(f"{api}/health/", timeout=10)
    if not step("health", r.status_code == 200, f"status={r.status_code}"):
        return 1

    # 1. register (public route, NULL tenant context)
    email = f"rls_smoke_{run}@example.com"
    r = s.post(
        f"{api}/auth/register/",
        json={"full_name": "RLS Smoke", "email": email, "password": f"smoke-{run}-pass12"},
        timeout=15,
    )
    body = r.json() if r.status_code < 500 else {}
    tok = (body.get("tokens") or {}).get("access") or body.get("access")
    if not step("register", r.status_code in (200, 201) and tok, f"status={r.status_code}"):
        return 1
    h = {"Authorization": f"Bearer {tok}"}

    # 2. create organisation — THE C-1 regression (500 pre-P14 under
    #    ledgersg_app: the CoA seed violated the RLS WITH CHECK)
    # Session-30 fixes (the session-29 findings): the M-1 gate now validates
    # formats — a real other-entities UEN (T + YY + 2 letters + 4 digits +
    # check letter) and a real M-form GST number (M + 8 digits + letter).
    yy = date.today().strftime("%y")
    digits = str(uuid.uuid4().int)
    uen = f"T{yy}LL{digits[-4:]}X"
    gst_no = f"M{digits[3:11]}K"
    r = s.post(
        f"{api}/organisations/",
        json={
            "name": f"RLS Smoke Org {run}",
            "uen": uen,
            "entity_type": "PRIVATE_LIMITED",
            "gst_registered": True,
            "gst_reg_number": gst_no,
            "gst_reg_date": date.today().isoformat(),
            "fy_start_month": 1,
            "base_currency": "SGD",
        },
        headers=h,
        timeout=30,
    )
    if not step("create organisation (C-1)", r.status_code == 201, f"status={r.status_code} {r.text[:120] if r.status_code != 201 else ''}"):
        return 1

    # 3. the org list must include it (NULL-context read — the §17 policy)
    r = s.get(f"{api}/organisations/", headers=h, timeout=15)
    orgs = r.json().get("data") or r.json().get("results") or []
    org = next((o for o in orgs if o.get("uen") == uen), None)
    if not step("org list includes new org", org is not None, f"status={r.status_code}"):
        return 1
    org_id = org["id"]

    # 4. contact
    r = s.post(
        f"{api}/{org_id}/invoicing/contacts/",
        json={
            "name": f"RLS Smoke Customer {run}",
            "contact_type": "CUSTOMER",
            "is_customer": True,
            "email": f"customer_{run}@example.com",
        },
        headers=h,
        timeout=15,
    )
    contact = r.json().get("id") or (r.json().get("data") or {}).get("id")
    if not step("create contact", r.status_code == 201 and contact, f"status={r.status_code}"):
        return 1

    # 5. accounts + tax codes (the CoA/GST seeds must exist — C-1's proof)
    # Session-30 fix (the session-29 lesson): the bank GL is 1100 — an
    # is_bank CHILD of the 1000 header — so it needs the is_bank filter
    # (the list defaults to top-level only; 1200 is Accounts RECEIVABLE,
    # not a bank account).
    r = s.get(f"{api}/{org_id}/accounts/?is_active=true", headers=h, timeout=15)
    accounts = (r.json().get("results") or [])
    revenue = next((a for a in accounts if a.get("code") == "4100"), None)
    r = s.get(f"{api}/{org_id}/accounts/?is_bank=true", headers=h, timeout=15)
    bank_accounts = (r.json().get("results") or [])
    bank_gl = next((a for a in bank_accounts if a.get("code") == "1100"), None) or (
        bank_accounts[0] if bank_accounts else None
    )
    if not step("seeded CoA exists (4100 + bank GL)", revenue and bank_gl, f"count={len(accounts)}, bank={len(bank_accounts)}"):
        return 1

    r = s.get(f"{api}/{org_id}/gst/tax-codes/?is_active=true", headers=h, timeout=15)
    codes = (r.json().get("results") or [])
    sr = next((c for c in codes if c.get("code") == "SR"), None)
    if not step("seeded tax codes exist (SR)", sr is not None, f"count={len(codes)}"):
        return 1

    # 6. invoice
    r = s.post(
        f"{api}/{org_id}/invoicing/documents/",
        json={
            "document_type": "SALES_INVOICE",
            "contact_id": contact,
            "issue_date": date.today().isoformat(),
            "reference": f"RLS-SMOKE-{run}",
            "lines": [
                {
                    "account_id": revenue["id"],
                    "description": "rls smoke line",
                    "quantity": "1.0000",
                    "unit_price": "100.00",
                    "tax_code_id": sr["id"],
                }
            ],
        },
        headers=h,
        timeout=30,
    )
    doc = r.json().get("id") or (r.json().get("data") or {}).get("id")
    if not step("create invoice", r.status_code == 201 and doc, f"status={r.status_code} {r.text[:150] if r.status_code != 201 else ''}"):
        return 1

    # 7. approve (posts the journal — RLS-covered writes)
    # Session-30 fix: the canonical approve path is the dedicated endpoint
    # (DRAFT -> APPROVED — the same path the e2e suite drives).
    r = s.post(f"{api}/{org_id}/invoicing/documents/{doc}/approve/", json={}, headers=h, timeout=30)
    if not step("approve invoice (journal posts under RLS)", r.status_code == 200, f"status={r.status_code} {r.text[:150] if r.status_code >= 400 else ''}"):
        return 1

    # 8. bank account + payment (allocate exactly the outstanding — H-1 cap)
    r = s.post(
        f"{api}/{org_id}/banking/accounts/",
        json={
            "account_name": f"RLS Smoke Bank {run}",
            "bank_name": "Test Bank",
            "account_number": f"00{uuid.uuid4().hex[:8]}",
            "currency": "SGD",
            "gl_account": bank_gl["id"],
            "paynow_type": None,
            "paynow_id": None,
        },
        headers=h,
        timeout=15,
    )
    bank = r.json().get("id") or (r.json().get("data") or {}).get("id")
    if not step("create bank account", r.status_code == 201 and bank, f"status={r.status_code} {r.text[:150] if r.status_code != 201 else ''}"):
        return 1

    doc_total = Decimal("109.00")
    r = s.post(
        f"{api}/{org_id}/banking/payments/receive/",
        json={
            "contact_id": contact,
            "bank_account_id": bank,
            "payment_date": date.today().isoformat(),
            "amount": "109.00",
            "currency": "SGD",
            "payment_method": "BANK_TRANSFER",
            "allocations": [{"document_id": doc, "allocated_amount": "109.00"}],
        },
        headers=h,
        timeout=30,
    )
    if not step("receive + allocate payment", r.status_code == 201, f"status={r.status_code} {r.text[:200] if r.status_code != 201 else ''}"):
        return 1

    # 9. F5 return + compute
    month_start = date.today().replace(day=1).isoformat()
    r = s.post(
        f"{api}/{org_id}/gst/returns/",
        json={"filing_frequency": "MONTHLY", "start_date": month_start, "periods": 1},
        headers=h,
        timeout=30,
    )
    r = s.get(f"{api}/{org_id}/gst/returns/", headers=h, timeout=15)
    returns = r.json().get("results") or []
    ret = next((x for x in returns if x.get("period_start") == month_start), None)
    if not step("F5 return created", ret is not None, f"status={r.status_code}"):
        return 1
    r = s.post(f"{api}/{org_id}/gst/returns/{ret['id']}/?force=true", json={}, headers=h, timeout=30)
    if not step("F5 compute (ledger reads under RLS)", r.status_code == 200, f"status={r.status_code} {r.text[:150] if r.status_code >= 400 else ''}"):
        return 1

    print(f"\n{sum(1 for _, ok, _ in STEPS if ok)}/{len(STEPS)} steps green as ledgersg_app")
    return 0 if all(ok for _, ok, _ in STEPS) else 1


if __name__ == "__main__":
    sys.exit(main())
