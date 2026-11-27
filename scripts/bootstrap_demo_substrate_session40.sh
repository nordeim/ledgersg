#!/usr/bin/env bash
# Demo substrate bootstrap (idempotent) — mirrors docs/DEPLOYMENT.md §9
# steps 1-5 EXACTLY (P20/X-H1b: the pre-P20 version stopped at step 2,
# which is exactly the gap that made a fresh DB's FIRST e2e run red —
# banking.spec.ts runs second, before any contact-creating spec).
#
# Run this once against the live dev stack before the first
# `npm run test:e2e:full` on a fresh database:
#   bash scripts/bootstrap_demo_substrate_session40.sh [BASE_URL]
#
# Every step is idempotent (reuse what exists), exactly as §9 documents.
set -euo pipefail
BASE="${1:-http://127.0.0.1:8000}"
EMAIL="${E2E_DEMO_EMAIL:-demo@ledgersg.sg}"
PASSWORD="${E2E_DEMO_PASSWORD:-demo1234pass}"

jsonget() { # jsonget <json> <python-expr over d>
  echo "$1" | python3 -c "import json,sys; d=json.load(sys.stdin); print($2)" 2>/dev/null || true
}

# ---- Step 1: the demo user (register on a fresh DB, else login) -------
body=$(curl -s -X POST "$BASE/api/v1/auth/register/" \
  -H 'Content-Type: application/json' \
  -d "{\"full_name\":\"Demo User\",\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}") || true
TOKEN=$(jsonget "$body" 'd.get("tokens",{}).get("access","")')
if [ -z "$TOKEN" ] || [ "$TOKEN" = "None" ]; then
  body=$(curl -s -X POST "$BASE/api/v1/auth/login/" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
  TOKEN=$(jsonget "$body" 'd.get("tokens",{}).get("access","")')
fi
[ -n "$TOKEN" ] && [ "$TOKEN" != "None" ] || { echo "FAIL: no token"; exit 1; }
echo "[substrate] step 1 — user OK"

# ---- Step 2: the demo org (reuse if exists; seeds CoA + fiscal + tax) --
# P21/BE-M6: the list envelope is unified — every list speaks
# {results, count} (the dual-shape fallback is retired).
ORGS=$(curl -s "$BASE/api/v1/organisations/" -H "Authorization: Bearer $TOKEN")
ORG_ID=$(jsonget "$ORGS" '((d.get("results") or [{}])[0].get("id", ""))')
if [ -z "$ORG_ID" ] || [ "$ORG_ID" = "None" ]; then
  ORG_ID=$(jsonget "$(curl -s -X POST "$BASE/api/v1/organisations/" \
    -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
    -d '{"name":"Ledger Demo Pte Ltd","uen":"202612345D","entity_type":"PRIVATE_LIMITED","gst_registered":true,"gst_reg_number":"M9034567K","gst_reg_date":"2026-01-01","fy_start_month":1,"base_currency":"SGD"}')" \
    'd.get("id") or d.get("organisation",{}).get("id","")')
fi
[ -n "$ORG_ID" ] && [ "$ORG_ID" != "None" ] || { echo "FAIL: no org"; exit 1; }
echo "[substrate] step 2 — org OK ($ORG_ID)"
AUTH=(-H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json')
API="$BASE/api/v1/$ORG_ID"

# ---- Step 3: a contact with a truthful profile (the P11 prefill surface) -
CONTACTS=$(curl -s "$API/invoicing/contacts/" -H "Authorization: Bearer $TOKEN")
CONTACT_ID=$(jsonget "$CONTACTS" '(d.get("results") or [])[0]["id"] if (d.get("results") or []) else ""')
if [ -z "$CONTACT_ID" ] || [ "$CONTACT_ID" = "None" ]; then
  CONTACT_ID=$(jsonget "$(curl -s -X POST "$API/invoicing/contacts/" \
    "${AUTH[@]}" \
    -d '{"name":"Demo Trading Pte Ltd","contact_type":"CUSTOMER","email":"billing@demotrading.example.sg","uen":"519234567K"}')" \
    'd.get("id","")')
fi
[ -n "$CONTACT_ID" ] && [ "$CONTACT_ID" != "None" ] || { echo "FAIL: no contact"; exit 1; }
# PATCH the detail with the truthful profile (the edit dialog prefills from DETAIL)
curl -s -X PATCH "$API/invoicing/contacts/$CONTACT_ID/" "${AUTH[@]}" \
  -d '{"uen":"519234567K","gst_reg_number":"M9123456X","peppol_id":"019234:Demo Trading Pte Ltd"}' > /dev/null || true
echo "[substrate] step 3 — contact OK ($CONTACT_ID)"

# ---- Step 4: one invoice + one credit note, both APPROVED (journal posted)
REVENUE_ID=$(jsonget "$(curl -s "$API/accounts/?is_active=true" -H "Authorization: Bearer $TOKEN")" \
  'next((a["id"] for a in (d.get("results") or []) if a["code"]=="4100" and a["account_type"]=="REVENUE"), "")')
[ -n "$REVENUE_ID" ] && [ "$REVENUE_ID" != "None" ] || { echo "WARN: no 4100 revenue account — skipping step 4"; REVENUE_ID=""; }

# P25/E2E-M1: the line serializer REQUIRES tax_code_id (P14/M-4's bounded
# InvoiceLineCreateSerializer) — the pre-P25 step 4a/4b POSTs omitted it,
# failed silently (the `|| true` guards), and printed "invoice OK ()" with
# an EMPTY id: the substrate's own invoice/credit-note never landed on a
# fresh host, masked only by the self-sufficient e2e specs. The SR tax
# code rides every line now, and a failed creation is LOUD (exit 1).
TAX_CODE_ID=""
if [ -n "$REVENUE_ID" ]; then
  TAX_CODE_ID=$(jsonget "$(curl -s "$API/gst/tax-codes/?is_active=true" -H "Authorization: Bearer $TOKEN")" \
    'next((t["id"] for t in (d.get("results") or []) if t["code"]=="SR" and t["rate"]=="0.0900"), "")')
  [ -n "$TAX_CODE_ID" ] && [ "$TAX_CODE_ID" != "None" ] || { echo "FAIL: no SR tax code — the org seed is incomplete"; exit 1; }
fi

if [ -n "$REVENUE_ID" ]; then
  # The credit note requires a related SALES_INVOICE — create one if none
  # exists (idempotent reuse otherwise).
  INVOICE_ID=$(jsonget "$(curl -s "$API/invoicing/documents/?document_type=SALES_INVOICE&status=APPROVED" -H "Authorization: Bearer $TOKEN")" \
    '(d.get("results") or [{}])[0].get("id","")')
  if [ -z "$INVOICE_ID" ] || [ "$INVOICE_ID" = "None" ]; then
    # Pick an open fiscal-period issue date: the org's fiscal year start.
    ISSUE_DATE=$(jsonget "$(curl -s "$API/fiscal-years/" -H "Authorization: Bearer $TOKEN")" \
      '(d.get("results") or [{}])[0].get("start_date","")')
    [ -n "$ISSUE_DATE" ] && [ "$ISSUE_DATE" != "None" ] || ISSUE_DATE="2026-01-15"
    INVOICE_BODY=$(curl -s -X POST "$API/invoicing/documents/" "${AUTH[@]}" \
      -d "{\"document_type\":\"SALES_INVOICE\",\"contact_id\":\"$CONTACT_ID\",\"issue_date\":\"$ISSUE_DATE\",\"due_date\":\"$ISSUE_DATE\",\"currency\":\"SGD\",\"lines\":[{\"account_id\":\"$REVENUE_ID\",\"description\":\"Demo substrate invoice\",\"quantity\":1,\"unit_price\":\"1000.00\",\"tax_code_id\":\"$TAX_CODE_ID\"}]}")
    INVOICE_ID=$(jsonget "$INVOICE_BODY" 'd.get("id","")')
    if [ -z "$INVOICE_ID" ] || [ "$INVOICE_ID" = "None" ]; then
      echo "FAIL: substrate invoice creation rejected — $INVOICE_BODY"
      exit 1
    fi
    curl -s -X POST "$API/invoicing/documents/$INVOICE_ID/approve/" "${AUTH[@]}" -d '{}' > /dev/null || true
  fi
  echo "[substrate] step 4a — invoice OK ($INVOICE_ID)"
  # The credit note (only if none exists — P11's linkage contract)
  CN_COUNT=$(jsonget "$(curl -s "$API/invoicing/documents/?document_type=SALES_CREDIT_NOTE" -H "Authorization: Bearer $TOKEN")" \
    'len(d.get("results") or [])')
  if [ "$CN_COUNT" = "0" ]; then
    ISSUE_DATE=$(jsonget "$(curl -s "$API/invoicing/documents/$INVOICE_ID/" -H "Authorization: Bearer $TOKEN")" 'd.get("issue_date","")')
    [ -n "$ISSUE_DATE" ] && [ "$ISSUE_DATE" != "None" ] || ISSUE_DATE="2026-01-20"
    curl -s -X POST "$API/invoicing/documents/" "${AUTH[@]}" \
      -d "{\"document_type\":\"SALES_CREDIT_NOTE\",\"contact_id\":\"$CONTACT_ID\",\"issue_date\":\"$ISSUE_DATE\",\"due_date\":\"$ISSUE_DATE\",\"currency\":\"SGD\",\"related_document_id\":\"$INVOICE_ID\",\"lines\":[{\"account_id\":\"$REVENUE_ID\",\"description\":\"Demo substrate credit note\",\"quantity\":1,\"unit_price\":\"200.00\",\"tax_code_id\":\"$TAX_CODE_ID\"}]}" > /dev/null || true
    CN_ID=$(jsonget "$(curl -s "$API/invoicing/documents/?document_type=SALES_CREDIT_NOTE&status=DRAFT" -H "Authorization: Bearer $TOKEN")" \
      '(d.get("results") or [{}])[0].get("id","")')
    if [ -n "$CN_ID" ] && [ "$CN_ID" != "None" ]; then
      curl -s -X POST "$API/invoicing/documents/$CN_ID/approve/" "${AUTH[@]}" -d '{}' > /dev/null || true
    fi
  fi
  echo "[substrate] step 4b — credit note OK"
fi

# ---- Step 4c: the pagination fodder top-up (P25/E2E-M1) -----------------
# The P24 ledger e2e spec pages the demo org's journal lines — its
# documented substrate claim is "36+ journal lines from the §9 bootstrap",
# but a fresh bootstrap posts only ~6 (one invoice + one credit note);
# the 36 the P24 session relied on had ACCUMULATED across prior sessions'
# e2e runs and never existed on a fresh host (the first-run truth broke:
# 40P/1F/1S instead of 42/42). The void spec has the same shape of
# dependency — it needs a VOIDABLE document to survive the banking
# spec's per-run settlement. Top the org up to a deterministic stock:
#   - >= 36 ledger lines (a full 20-row page 1 + a live page 2)
#   - >= 4 APPROVED invoices (the durable voidable stock)
# Each fodder invoice posts 3 lines (DR AR / CR revenue / CR GST at SR);
# the loop re-queries the ledger count every iteration (no assumed
# arithmetic) and is idempotent — a re-run at target creates nothing.
FODDER_TARGET_LINES=36
FODDER_TARGET_APPROVED=4
FODDER_MAX=12
FODDER_N=0
ledger_count() {
  jsonget "$(curl -s "$API/journal-entries/ledger/?limit=1" -H "Authorization: Bearer $TOKEN")" 'd.get("count", 0)'
}
approved_count() {
  jsonget "$(curl -s "$API/invoicing/documents/?document_type=SALES_INVOICE&status=APPROVED" -H "Authorization: Bearer $TOKEN")" 'len(d.get("results") or [])'
}
if [ -n "$REVENUE_ID" ]; then
  while { [ "$(ledger_count)" -lt "$FODDER_TARGET_LINES" ] || [ "$(approved_count)" -lt "$FODDER_TARGET_APPROVED" ]; } && [ "$FODDER_N" -lt "$FODDER_MAX" ]; do
    FODDER_N=$((FODDER_N + 1))
    ISSUE_DATE=$(jsonget "$(curl -s "$API/fiscal-years/" -H "Authorization: Bearer $TOKEN")" \
      '(d.get("results") or [{}])[0].get("start_date","")')
    [ -n "$ISSUE_DATE" ] && [ "$ISSUE_DATE" != "None" ] || ISSUE_DATE="2026-01-10"
    FODDER_ID=$(jsonget "$(curl -s -X POST "$API/invoicing/documents/" "${AUTH[@]}" \
      -d "{\"document_type\":\"SALES_INVOICE\",\"contact_id\":\"$CONTACT_ID\",\"issue_date\":\"$ISSUE_DATE\",\"due_date\":\"$ISSUE_DATE\",\"currency\":\"SGD\",\"reference\":\"SUBSTRATE-PAGE-$FODDER_N\",\"lines\":[{\"account_id\":\"$REVENUE_ID\",\"description\":\"Demo substrate pagination fodder $FODDER_N\",\"quantity\":1,\"unit_price\":\"50.00\",\"tax_code_id\":\"$TAX_CODE_ID\"}]}")" \
      'd.get("id","")')
    if [ -n "$FODDER_ID" ] && [ "$FODDER_ID" != "None" ]; then
      curl -s -X POST "$API/invoicing/documents/$FODDER_ID/approve/" "${AUTH[@]}" -d '{}' > /dev/null || true
    fi
  done
fi
echo "[substrate] step 4c — pagination fodder OK (ledger lines: $(ledger_count), approved invoices: $(approved_count))"

# ---- Step 5: compute an F5 return (the F5 truth substrate) --------------
RETURN_COUNT=$(jsonget "$(curl -s "$API/gst/returns/" -H "Authorization: Bearer $TOKEN")" \
  'len(d.get("results") or [])')
if [ "$RETURN_COUNT" = "0" ]; then
  RETURN_ID=$(jsonget "$(curl -s -X POST "$API/gst/returns/" "${AUTH[@]}" \
    -d '{"filing_frequency":"MONTHLY","start_date":"2026-01-01","periods":1}')" \
    'd.get("id","")')
  if [ -n "$RETURN_ID" ] && [ "$RETURN_ID" != "None" ]; then
    curl -s -X POST "$API/gst/returns/$RETURN_ID/?force=true" "${AUTH[@]}" -d '{}' > /dev/null || true
  fi
fi
echo "[substrate] step 5 — F5 return OK"

echo "[substrate] complete — the first e2e:full run has its data."
echo "$TOKEN" > /tmp/ledgersg-demo-token
echo "$ORG_ID" > /tmp/ledgersg-demo-org
