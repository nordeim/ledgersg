# Executive Summary

This blueprint outlines the architecture for **"LedgerSG"**—an enterprise-grade, avant-garde accounting platform designed specifically for the Singaporean market. It addresses the critical **IRAS GST rate increase to 9% (effective Jan 1, 2024)**, the push for **Peppol e-invoicing**, and strict **PDPA compliance**.

We will reject the "boring spreadsheet" aesthetic of traditional accounting software. Instead, we will employ **"Editorial Fintech"** design principles: high-contrast typography, asymmetric data visualization, and a "glass-morphic" depth that makes complex financial data feel tangible and manageable.

Technically, this solution leverages the strict ACID compliance of **PostgreSQL 16**, the robust ORM of **Django 5.x (Python 3.13)**, and the reactive power of **Next.js 15 + React 19**.

---

# Phase 1: Deep Analysis & Regulatory Mining

Before a single line of code is written, we must codify the regulatory constraints into our system logic.

### 1.1 IRAS Regulatory Constraints (The "Truth")
*   **GST Calculation:** The system must handle the transition. Invoices dated before 2024-01-01 use 8%; on/after use 9%.
    *   *Edge Case:* "Time of Supply" rules. If an invoice is issued in Jan 2024 but payment was received in Dec 2023, the tax point might differ. Our system needs a `tax_point_date` field separate from `invoice_date`.
*   **Precision:** IRAS allows rounding to the nearest cent, but intermediate calculations must maintain higher precision to prevent "penny shaving" errors over thousands of transactions.
    *   *Decision:* Store as `NUMERIC(10, 4)` in DB. Display as `toFixed(2)`. Round only at the final invoice total level.
*   **UEN Validation:** Every entity must have a valid Unique Entity Number (UEN). We need a regex validator and potentially an API hook to ACRA (Accounting and Corporate Regulatory Authority) for real-time verification.
*   **Audit Trail:** IRAS requires records to be kept for 5 years. Data cannot be "deleted," only "voided" or "archived" with a timestamped reason.

### 1.2 Technical Constraints & Opportunities
*   **PostgreSQL 16:** We will utilize `GENERATED ALWAYS AS IDENTITY` for primary keys and native `JSONB` for flexible metadata (e.g., storing specific GST relief codes) without schema migration hell.
*   **Django 5.x:** We will use Django's `DecimalField` exclusively. Floats are banned. We will implement custom Model Managers to enforce soft-deletes for audit compliance.
*   **Next.js 15 (App Router):** We will leverage React Server Components (RSC) for the initial load of heavy financial reports to reduce client-side bundle size, ensuring instant perceived performance.
*   **Tailwind CSS 4:** We will use the new native CSS variables engine for theming, allowing for instant "Dark Mode" switching which is crucial for accountants working late.

---

# Phase 2: Architectural Blueprint & Execution Plan

## 2.1 Database Schema Strategy (PostgreSQL 16)

We prioritize data integrity over flexibility. Financial data is immutable.

### Core Tables Design
1.  **`organizations`**: Multi-tenancy root. Stores UEN, GST Registration Number, Fiscal Year Start.
2.  **`chart_of_accounts`**: Standard Singapore COA structure (Assets, Liabilities, Equity, Income, Expenses).
3.  **`journal_entries`**: The source of truth. Double-entry bookkeeping enforced at the DB level via triggers or application logic.
4.  **`invoices`**: Header information. Includes `gst_rate_snapshot` (to preserve the rate at the time of issuance).
5.  **`invoice_items`**: Line items.
6.  **`audit_logs`**: Immutable table. Every `INSERT`, `UPDATE`, `DELETE` on critical tables writes here.

### SQL Precision Logic
```sql
-- We enforce 4 decimal places for storage, 2 for display logic
CREATE TABLE invoice_items (
    id BIGSERIAL PRIMARY KEY,
    unit_price NUMERIC(10, 4) NOT NULL,
    quantity NUMERIC(10, 4) NOT NULL,
    gst_rate NUMERIC(3, 2) NOT NULL CHECK (gst_rate >= 0.00 AND gst_rate <= 1.00),
    subtotal NUMERIC(10, 4) GENERATED ALWAYS AS (unit_price * quantity) STORED,
    gst_amount NUMERIC(10, 4) GENERATED ALWAYS AS (subtotal * gst_rate) STORED
);
```

## 2.2 Backend Architecture (Django 5.x + Python 3.13)

We will structure the backend as a modular monolith, ready to be split into microservices if scale demands.

### Directory Structure
```text
backend/
├── config/             # Settings (split by env: dev, staging, prod)
├── apps/
│   ├── core/           # Auth, Tenancy, Audit Logging
│   ├── accounting/     # COA, Journal Entries, Ledger
│   ├── invoicing/      # Invoices, Quotes, Credit Notes
│   ├── compliance/     # IRAS GST Logic, UEN Validation, Peppol Prep
│   └── reporting/      # Financial Statements (P&L, Balance Sheet)
├── utils/
│   ├── money.py        # Custom Decimal wrapper to prevent float leakage
│   └── validators.py   # UEN Regex, GST Logic
```

### Critical Logic: The GST Engine
We will create a dedicated service class to handle tax logic, isolating it from business logic.

```python
# apps/compliance/services/gst_engine.py
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone

class SGSTEngine:
    CURRENT_GST_RATE = Decimal('0.09') # 9%
    LEGACY_GST_RATE = Decimal('0.08')  # 8%
    GST_CHANGE_DATE = timezone.datetime(2024, 1, 1, tzinfo=timezone.utc)

    @classmethod
    def get_applicable_rate(cls, transaction_date):
        """
        Determines GST rate based on IRAS 'Time of Supply' rules.
        """
        if transaction_date >= cls.GST_CHANGE_DATE:
            return cls.CURRENT_GST_RATE
        return cls.LEGACY_GST_RATE

    @classmethod
    def calculate_line_item(cls, amount, rate):
        """
        Returns tuple: (subtotal, gst, total)
        Ensures 4 decimal precision internally, rounds to 2 for final output.
        """
        gst = (amount * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total = amount + gst
        return amount, gst, total
```

## 2.3 Frontend Architecture (Next.js 15 + React 19)

### Design System: "Monolith & Glass"
*   **Typography:** `Geist Mono` for numbers (tabular figures ensure columns align perfectly). `Inter` for UI text.
*   **Color Palette:**
    *   Background: `#0A0A0A` (Deep Charcoal)
    *   Surface: `#141414` (Lighter Charcoal with 1px border `#222`)
    *   Accent: `#00FF94` (Cyber Green for Positive Cashflow) / `#FF3333` (Alert Red for Tax Due)
    *   Text: `#EDEDED` (Off-white for reduced eye strain)
*   **Components (Shadcn-UI + Tailwind 4):**
    *   We will extend Shadcn's `Table` component to support virtualization (for 10k+ rows).
    *   We will create a custom `MoneyInput` component that auto-formats as the user types (e.g., typing `1000` becomes `1,000.00`).

### Key Pages & UX Flows
1.  **The "Command Center" (Dashboard):**
    *   Not a grid of cards. A single, scrollable timeline of cash flow.
    *   "GST Liability" widget prominently displayed at the top right, updating in real-time as invoices are created.
2.  **Invoice Builder:**
    *   Distraction-free mode.
    *   Auto-complete for Singapore entities (using UEN).
    *   Real-time GST calculation visualization (showing the 9% breakdown clearly).
3.  **IRAS Submission Prep:**
    *   One-click export to CSV/Excel formatted exactly for IRAS GST F5 return.

---

# Phase 3: Validation & Risk Mitigation

## 3.1 Risk Assessment
| Risk | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Rounding Errors** | Critical | Use Python `decimal` module exclusively. Never use `float`. DB uses `NUMERIC`. |
| **Regulatory Change** | High | Abstract tax rates into a `TaxConfiguration` model. Do not hardcode 9% in logic, only as a default. |
| **Data Privacy (PDPA)** | High | Encrypt PII (Customer Names, NRIC/FIN) at rest using PostgreSQL `pgcrypto`. |
| **Performance** | Medium | Implement database indexing on `transaction_date` and `organization_id`. Use Redis for caching dashboard aggregates. |

## 3.2 Validation Checkpoints
1.  **Unit Tests:** 100% coverage on the `SGSTEngine`. Test dates exactly on the boundary of 2023-12-31 and 2024-01-01.
2.  **Integration Tests:** Verify that creating an invoice automatically creates the corresponding Journal Entries.
3.  **Visual Regression:** Use Playwright to ensure the UI doesn't break on mobile (SMB owners often check invoices on phones).

---

# Phase 4: Implementation Roadmap (The "How")

## Step 1: Environment & Foundation
*   Initialize Next.js 15 with Tailwind 4.
*   Setup Django project with PostgreSQL 16 connection pooling (PgBouncer).
*   Configure ESLint + Prettier + Husky for strict code quality.

## Step 2: Core Domain Modeling
*   Implement `Organization` and `User` models with Row-Level Security (RLS) concepts in Django.
*   Build the `ChartOfAccounts` seed data for Singapore (Class 1-6).

## Step 3: The Invoice Engine
*   Develop the API endpoints for Invoice CRUD.
*   Implement the frontend Invoice Builder with React Hook Form + Zod validation.
*   Integrate the `SGSTEngine` to calculate totals dynamically on the client before submission.

## Step 4: Reporting & Compliance
*   Build the General Ledger view.
*   Create the "GST Report" view that sums up Output Tax vs Input Tax.
*   Implement the "Export for IRAS" functionality.

## Step 5: Polish & Avant-Garde UI
*   Apply the "Monolith & Glass" theme.
*   Add micro-interactions (e.g., subtle glow when an invoice is "Paid").
*   Optimize LCP (Largest Contentful Paint) using Next.js Image Optimization.

---

# Technical Deliverable: Project Structure & Key Configs

To demonstrate the "Meticulous Approach," here is the foundational setup code.

### 1. `backend/apps/compliance/models.py` (The Source of Truth)
```python
from django.db import models
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator

class TaxConfiguration(models.Model):
    """
    Centralized management of Singapore Tax Rates.
    Allows for historical tracking without code changes.
    """
    name = models.CharField(max_length=50) # e.g., "Standard GST 2024"
    rate = models.DecimalField(
        max_digits=5, 
        decimal_places=4, 
        validators=[MinValueValidator(Decimal('0.0000')), MaxValueValidator(Decimal('1.0000'))]
    )
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-effective_from']

    def __str__(self):
        return f"{self.name} ({self.rate * 100}%)"
```

### 2. `frontend/components/ui/money-input.tsx` (Avant-Garde UX)
```tsx
"use client";

import { Input } from "@/components/ui/input";
import { useImperativeHandle, useRef } from "react";

interface MoneyInputProps {
  value: string;
  onChange: (val: string) => void;
  className?: string;
}

/**
 * Avant-Garde Money Input
 * - Enforces numeric input
 * - Auto-formats to SGD standard (1,234.56)
 * - Visual cue for currency
 */
export function MoneyInput({ value, onChange, className }: MoneyInputProps) {
  const formatMoney = (val: string) => {
    // Remove non-numeric chars except decimal
    const numericVal = val.replace(/[^0-9.]/g, "");
    const parts = numericVal.split(".");
    
    // Limit to 2 decimal places for display, logic handles 4 internally
    if (parts.length > 2) return parts[0] + "." + parts[1]; 
    
    // Add commas for thousands
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    
    return parts.join(".");
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value;
    const formatted = formatMoney(raw);
    onChange(formatted);
  };

  return (
    <div className={`relative group ${className}`}>
      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground font-mono text-sm">
        S$
      </span>
      <Input
        type="text"
        inputMode="decimal"
        value={value}
        onChange={handleChange}
        className="pl-8 font-mono tracking-tight tabular-nums focus-visible:ring-emerald-500/50 transition-all duration-300"
        placeholder="0.00"
      />
      {/* Subtle glow effect on focus via Tailwind 4 utilities */}
      <div className="absolute inset-0 rounded-md ring-1 ring-inset ring-white/5 group-focus-within:ring-emerald-500/20 pointer-events-none" />
    </div>
  );
}
```

### 3. `backend/apps/invoicing/services/invoice_creator.py` (Transaction Safety)
```python
from django.db import transaction
from decimal import Decimal
from apps.compliance.services.gst_engine import SGSTEngine
from apps.accounting.models import JournalEntry, Account

@transaction.atomic
def create_invoice_with_ledger(organization, invoice_data):
    """
    Creates an invoice AND the corresponding double-entry ledger posts.
    Ensures financial integrity.
    """
    # 1. Create Invoice Header
    invoice = Invoice.objects.create(
        organization=organization,
        date=invoice_data['date'],
        # ... other fields
    )

    total_gst = Decimal('0.00')
    total_net = Decimal('0.00')

    # 2. Process Line Items
    for item in invoice_data['items']:
        rate = SGSTEngine.get_applicable_rate(invoice.date)
        net, gst, line_total = SGSTEngine.calculate_line_item(item['amount'], rate)
        
        InvoiceItem.objects.create(
            invoice=invoice,
            description=item['description'],
            amount=net,
            gst_amount=gst,
            gst_rate=rate
        )
        total_gst += gst
        total_net += net

    # 3. Create Journal Entries (Double Entry)
    # Debit: Accounts Receivable
    JournalEntry.objects.create(
        organization=organization,
        account=Account.objects.get(code='1200'), # AR
        debit=total_net + total_gst,
        credit=Decimal('0.00'),
        reference=f"INV-{invoice.id}"
    )
    
    # Credit: Sales Income
    JournalEntry.objects.create(
        organization=organization,
        account=Account.objects.get(code='4000'), # Sales
        debit=Decimal('0.00'),
        credit=total_net,
        reference=f"INV-{invoice.id}"
    )

    # Credit: GST Output Tax (Liability)
    JournalEntry.objects.create(
        organization=organization,
        account=Account.objects.get(code='2100'), # GST Payable
        debit=Decimal('0.00'),
        credit=total_gst,
        reference=f"INV-{invoice.id}"
    )

    return invoice
```

# Next Steps & Validation Request

This blueprint provides the regulatory backbone and the avant-garde aesthetic direction required.

**Before I proceed to generate the full repository structure and specific component code:**
1.  Do you approve of the **"Monolith & Glass"** aesthetic direction (Dark mode default, high contrast, mono fonts for data)?
2.  Is the **PostgreSQL `NUMERIC(10,4)`** strategy aligned with your precision requirements, or do you require higher precision for specific manufacturing contexts?
3.  Shall we prioritize the **Peppol e-invoicing** integration in Phase 1, or defer it to Phase 2 to focus on core GST logic first?

Awaiting your validation to commence the **Implementation Phase**.
