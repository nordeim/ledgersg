# Database Schema Patch Plan v1.0.1

## Source Document
- **Patch Review**: `database_schema_patch_opus.md`
- **Target Schema**: `database_schema.sql`
- **Current Version**: 1.0.0
- **Target Version**: 1.0.1

---

## Fixes to Apply (8 Total)

### CRITICAL (Fix First)

#### FIX 1: GST Function Volatility (CRITICAL BUG)
**Issue**: `gst.calculate()` and `gst.calculate_line()` marked `IMMUTABLE` but query `gst.tax_code` table
**Impact**: PostgreSQL may cache stale results after rate changes, causing wrong GST calculations
**Solution**: Change `IMMUTABLE` → `STABLE`

```sql
-- Line ~1323: Change IMMUTABLE to STABLE
CREATE OR REPLACE FUNCTION gst.calculate(...) ... STABLE PARALLEL SAFE

-- Line ~1394: Change IMMUTABLE to STABLE  
CREATE OR REPLACE FUNCTION gst.calculate_line(...) ... STABLE PARALLEL SAFE
```

---

#### FIX 2: BCRS Deposit Flag (CRITICAL - Regulatory)
**Issue**: Missing `is_bcrs_deposit` on `invoicing.document_line`
**Impact**: Cannot handle Beverage Container Recycling Scheme deposits (effective Apr 2026)
**Solution**: Add column after `base_total_amount`

```sql
-- After line ~1046 in document_line table
ALTER TABLE invoicing.document_line
    ADD COLUMN is_bcrs_deposit BOOLEAN NOT NULL DEFAULT FALSE;
```

---

#### FIX 3: Journal Balance Trigger (CRITICAL)
**Issue**: `journal.validate_balance()` exists but never attached as trigger
**Impact**: Journal entries could be posted unbalanced
**Solution**: Add deferred constraint trigger on `journal.line`

```sql
-- Add after line ~1508 (after validate_balance function)
CREATE OR REPLACE FUNCTION journal.validate_entry_balance_on_line()
RETURNS TRIGGER ...

CREATE CONSTRAINT TRIGGER trg_journal_line_balance_check
    AFTER INSERT ON journal.line
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW
    EXECUTE FUNCTION journal.validate_entry_balance_on_line();
```

---

### HIGH Priority

#### FIX 4: GST F5 Return — BCRS Exclusion + Boxes 9-15
**Issue**: 
1. `gst.compute_f5_return()` doesn't exclude BCRS deposits
2. Boxes 9-12 and 15 not computed

**Solution**: 
1. Add `AND dl.is_bcrs_deposit = FALSE` to all queries
2. Add variable declarations and computation for boxes 9-12, 15
3. Update INSERT statement to include all 15 boxes

**Location**: Replace function at line ~1514

---

#### FIX 5: amount_due Generated Column
**Issue**: `chk_amount_due` CHECK constraint requires atomic updates
**Impact**: Fragile — payment recording could fail if `amount_due` not updated simultaneously
**Solution**: Convert to `GENERATED ALWAYS AS` column

```sql
-- In invoicing.document table (lines ~936-946)
-- Remove: amount_due column definition and chk_amount_due constraint
-- Replace with:
amount_due NUMERIC(10,4) GENERATED ALWAYS AS (total_amount - amount_paid) STORED
```

---

### MEDIUM Priority

#### FIX 6: Audit Org-Scoped View
**Issue**: `audit.event_log` has no RLS, no org-scoped access pattern
**Solution**: Create view for normal users

```sql
-- Add after line ~1298 (after audit indexes)
CREATE OR REPLACE VIEW audit.org_event_log AS
    SELECT * FROM audit.event_log
    WHERE org_id = core.current_org_id();

GRANT SELECT ON audit.org_event_log TO ledgersg_app;
```

---

#### FIX 7: Peppol Transmission Log Table
**Issue**: No table to track InvoiceNow retry attempts
**Solution**: Create `gst.peppol_transmission_log` table with RLS

```sql
-- Add new table in §5 GST Schema (after gst.return)
CREATE TABLE gst.peppol_transmission_log (...);
-- + indexes, RLS policies, grants
```

---

### LOW Priority

#### FIX 8: Fiscal Period Locking Audit Trail
**Issue**: No record of who locked/closed fiscal periods
**Solution**: Add columns to `core.fiscal_period`

```sql
-- In core.fiscal_period table (lines ~353-368)
-- Add after is_adjustment:
locked_at    TIMESTAMPTZ,
locked_by    UUID REFERENCES core.app_user(id),
closed_at    TIMESTAMPTZ,
closed_by    UUID REFERENCES core.app_user(id)
```

---

## Execution Order

```
1. FIX 1: GST function volatility (STABLE)
2. FIX 5: amount_due generated column (before data)
3. FIX 2: BCRS column (adds column)
4. FIX 8: Fiscal period audit columns
5. FIX 7: Peppol transmission log (new table)
6. FIX 4: Update gst.compute_f5_return (uses BCRS column)
7. FIX 3: Journal balance trigger
8. FIX 6: Audit org_event_log view
```

---

## Verification Checklist

After patch application, verify:

- [ ] `SELECT provolatile FROM pg_proc WHERE proname = 'calculate';` returns 's'
- [ ] `is_bcrs_deposit` column exists on `invoicing.document_line`
- [ ] `trg_journal_line_balance_check` trigger exists
- [ ] `amount_due` is_generated = 'ALWAYS' in information_schema
- [ ] `audit.org_event_log` view exists
- [ ] `gst.peppol_transmission_log` table exists
- [ ] `locked_at`, `locked_by` columns exist on `core.fiscal_period`

---

## SQL Patch Script Structure

```sql
-- ╔══════════════════════════════════════════════════════════════════════════════╗
-- ║  LEDGERSG SCHEMA PATCH v1.0.1 — Post-Validation Remediation               ║
-- ╚══════════════════════════════════════════════════════════════════════════════╝

BEGIN;

-- FIX 1: GST Function Volatility
-- FIX 2: BCRS Deposit Flag
-- FIX 3: Journal Balance Trigger
-- FIX 4: GST F5 Return Update
-- FIX 5: amount_due Generated Column
-- FIX 6: Audit Org-Scoped View
-- FIX 7: Peppol Transmission Log
-- FIX 8: Fiscal Period Audit Trail

-- VERIFICATION BLOCK

COMMIT;
```
