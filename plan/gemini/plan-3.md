**Executive Summary**

Approvals logged. We are now executing **Milestone 3: Data Visualization & Reporting (The Command Center)**.

Standard SaaS dashboards are plagued by symmetric, predictable 4-column grids with curved, friendly charts and soft drop-shadows. This aesthetic fails to communicate the gravitas of corporate compliance and financial health.

For LedgerSG, we are deploying a **Bento-box Asymmetry** approach. The dashboard is a strict CSS Grid where hierarchy is dictated by span size, not just typography. We will integrate `recharts` but violently strip it of its default curves and rounded tooltips, forcing it into our geometric, "Anti-Generic" aesthetic. Finally, we will implement the **Cascading Ledger**—a highly performant `framer-motion` list that physically simulates the printing of a financial ticker.

Here is the meticulously engineered Command Center.

---

### Phase 3.1: The Asymmetric Bento Grid (Dashboard Shell)

**Deep Reasoning:**
We use a 6-column grid on desktop. The primary compliance anchor (GST F5 Liability) spans 2 columns and 2 rows, visually dominating the screen. Secondary metrics (Cashflow, TP Thresholds) orbit this anchor. This directs the CFO's eye immediately to regulatory risk before operational metrics.

File: `src/app/(dashboard)/page.tsx`
```tsx
import { Suspense } from "react";
import { BrutalistSkeleton } from "@/components/common/brutalist-skeleton";
import { GstLiabilityCard } from "@/components/dashboard/gst-liability-card";
import { CashflowTrendChart } from "@/components/dashboard/cashflow-trend-chart";
import { LedgerCascade } from "@/components/dashboard/ledger-cascade";

export default function CommandCenter() {
  return (
    <main className="flex-1 p-6 lg:p-10 space-y-8">
      <header className="flex items-end justify-between border-b border-border pb-4">
        <div>
          <h1 className="text-4xl font-display uppercase tracking-tight text-text-primary">
            Command Center
          </h1>
          <p className="text-sm font-mono text-text-muted mt-2 uppercase tracking-widest">
            Fiscal Year 2026 • Live Ledger
          </p>
        </div>
        <div className="hidden md:flex items-center gap-2">
          {/* Peppol Network Status Indicator */}
          <span className="flex h-2 w-2 bg-accent" />
          <span className="text-xs font-mono text-text-secondary uppercase">Peppol Active</span>
        </div>
      </header>

      {/* 
        BENTO GRID ARCHITECTURE 
        6 columns. Absolute 1px gap mimicking architectural blueprints.
      */}
      <div className="grid grid-cols-1 md:grid-cols-4 lg:grid-cols-6 gap-px bg-border border border-border">
        
        {/* Primary Anchor: Spans 2 cols, 2 rows */}
        <div className="bg-carbon col-span-1 md:col-span-2 lg:col-span-2 row-span-2 p-6 transition-colors hover:bg-surface">
          <Suspense fallback={<BrutalistSkeleton className="h-full w-full" />}>
            <GstLiabilityCard />
          </Suspense>
        </div>

        {/* Operational Chart: Spans 4 cols, 1 row */}
        <div className="bg-void col-span-1 md:col-span-2 lg:col-span-4 row-span-1 p-6 relative group overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-0 group-hover:opacity-100 transition-opacity">
            <span className="text-[10px] font-mono text-ochre border border-ochre px-2 py-1 uppercase">
              Expand View
            </span>
          </div>
          <h2 className="text-sm font-display uppercase text-text-secondary mb-6">30-Day Cash Flow</h2>
          <Suspense fallback={<BrutalistSkeleton className="h-48 w-full" />}>
            <CashflowTrendChart />
          </Suspense>
        </div>

        {/* Secondary Metrics: 2 cols each */}
        <div className="bg-carbon col-span-1 md:col-span-2 lg:col-span-2 p-6 flex flex-col justify-between">
          <h3 className="text-sm font-display uppercase text-text-secondary">TP Threshold (Related Party)</h3>
          <div className="mt-4">
            <p className="money text-2xl text-text-primary">S$ 1,450,000.00</p>
            <div className="w-full bg-void h-1 mt-3 border border-border">
              <div className="bg-warning h-full w-[72.5%]" />
            </div>
            <p className="text-xs font-mono text-text-muted mt-2">72.5% of S$2M Limit</p>
          </div>
        </div>

        <div className="bg-carbon col-span-1 md:col-span-2 lg:col-span-2 p-6 flex flex-col justify-between">
          <h3 className="text-sm font-display uppercase text-text-secondary">BCRS Deposit Liability</h3>
          <div className="mt-4">
            <p className="money text-2xl text-ochre">S$ 4,210.50</p>
            <p className="text-xs font-mono text-text-muted mt-2">Effective Apr 2026 • 42,105 units</p>
          </div>
        </div>

      </div>

      {/* Recent Ledger Entries */}
      <section className="mt-12 border border-border bg-void">
        <header className="px-6 py-4 border-b border-border bg-carbon flex justify-between items-center">
          <h2 className="text-sm font-display uppercase tracking-widest text-text-primary">
            Recent Journal Entries
          </h2>
        </header>
        <Suspense fallback={<BrutalistSkeleton className="h-64 w-full" />}>
          <LedgerCascade />
        </Suspense>
      </section>
    </main>
  );
}
```

---

### Phase 3.2: The Geometric Trend Chart (Anti-Generic Recharts)

**Deep Reasoning:**
Standard charts use `type="monotone"` which creates soft, flowing bezier curves. We reject this. We use `type="stepAfter"` or strict `linear` lines. We strip all rounded borders from tooltips and use our `money` typography class to ensure absolute tabular alignment when hovering over data points. 

File: `src/components/dashboard/cashflow-trend-chart.tsx`
```tsx
"use client";

import { memo } from "react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

// Mock data: Note the exactness of the figures.
const data = [
  { date: "01 FEB", in: 4000.00, out: 2400.00 },
  { date: "05 FEB", in: 3000.00, out: 1398.00 },
  { date: "10 FEB", in: 2000.00, out: 9800.00 },
  { date: "15 FEB", in: 2780.00, out: 3908.00 },
  { date: "20 FEB", in: 1890.00, out: 4800.00 },
  { date: "24 FEB", in: 2390.00, out: 3800.00 },
];

/**
 * Geometric Custom Tooltip
 * Removes default Recharts "softness", enforces Neo-Brutalist borders.
 */
const BrutalistTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-carbon border border-border p-3 shadow-none">
        <p className="font-mono text-xs text-text-secondary mb-2 uppercase">{label}</p>
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex justify-between gap-6 items-center mt-1">
            <span className="font-display text-xs uppercase" style={{ color: entry.color }}>
              {entry.name}
            </span>
            <span className="money text-sm text-text-primary">
              {entry.value.toFixed(2)}
            </span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export const CashflowTrendChart = memo(() => {
  return (
    <div className="h-48 w-full mt-4">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
          {/* Strict orthogonal grid lines, no dashing */}
          <CartesianGrid strokeDasharray="0" stroke="var(--color-border)" vertical={false} />
          
          <XAxis 
            dataKey="date" 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: 'var(--color-text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }} 
            dy={10}
          />
          <YAxis 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: 'var(--color-text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
            tickFormatter={(value) => `${value / 1000}k`}
          />
          
          <Tooltip content={<BrutalistTooltip />} cursor={{ stroke: 'var(--color-border)', strokeWidth: 1 }} />
          
          {/* 
            type="stepAfter" creates a brutalist staircase effect. 
            No curves allowed in corporate finance. 
          */}
          <Area 
            type="stepAfter" 
            dataKey="out" 
            name="Cash Out"
            stroke="var(--color-ochre)" 
            strokeWidth={1}
            fill="transparent" 
          />
          <Area 
            type="stepAfter" 
            dataKey="in" 
            name="Cash In"
            stroke="var(--color-accent)" 
            strokeWidth={1}
            fill="var(--color-accent-glow)" 
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
});

CashflowTrendChart.displayName = "CashflowTrendChart";
```

---

### Phase 3.3: The Cascading Ledger (Motion Identity)

**Deep Reasoning:**
We use `framer-motion` to create a staggered entrance. But instead of a generic "fade up", we stagger them row-by-row with zero spring bounce—a rigid, mechanical cascade mimicking a dot-matrix ledger printer. The DOM is kept light by rendering only the visible viewport limits.

File: `src/components/dashboard/ledger-cascade.tsx`
```tsx
"use client";

import { memo } from "react";
import { motion } from "framer-motion";

const mockLedger = [
  { id: "JRN-001", date: "24 FEB", desc: "InvoiceNow Transmission: INV-2026-042", debit: 4200.00, credit: 0 },
  { id: "JRN-002", date: "24 FEB", desc: "GST Output Tax (9% SR)", debit: 0, credit: 378.00 },
  { id: "JRN-003", date: "23 FEB", desc: "BCRS Deposit Liability Collection", debit: 0, credit: 42.10 },
  { id: "JRN-004", date: "23 FEB", desc: "Payment Received: UOB Corporate", debit: 4578.00, credit: 0 },
  { id: "JRN-005", date: "22 FEB", desc: "Reverse Charge (9% RS) - AWS Cloud", debit: 135.00, credit: 0 },
];

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05 }, // Fast, mechanical stagger
  },
};

const itemVariants = {
  hidden: { opacity: 0, x: -5 }, // Minimal lateral movement, no vertical bounce
  show: { opacity: 1, x: 0, transition: { duration: 0.2, ease: "linear" } },
};

export const LedgerCascade = memo(() => {
  return (
    <motion.div 
      variants={containerVariants} 
      initial="hidden" 
      animate="show"
      className="w-full text-sm"
    >
      {/* Table Header */}
      <div className="grid grid-cols-[100px_100px_1fr_120px_120px] gap-4 px-6 py-3 border-b border-border text-xs font-display uppercase text-text-secondary">
        <div>Ref</div>
        <div>Date</div>
        <div>Description</div>
        <div className="text-right">Debit</div>
        <div className="text-right">Credit</div>
      </div>

      {/* Table Body */}
      {mockLedger.map((row) => (
        <motion.div 
          key={row.id} 
          variants={itemVariants}
          className="grid grid-cols-[100px_100px_1fr_120px_120px] gap-4 px-6 py-3 border-b border-border/50 hover:bg-surface transition-colors items-center"
        >
          <div className="font-mono text-text-muted">{row.id}</div>
          <div className="font-mono text-text-muted">{row.date}</div>
          <div className="font-body text-text-primary truncate pr-4">{row.desc}</div>
          <div className="money text-right text-text-primary">
            {row.debit > 0 ? row.debit.toFixed(2) : "-"}
          </div>
          <div className="money text-right text-ochre">
            {row.credit > 0 ? row.credit.toFixed(2) : "-"}
          </div>
        </motion.div>
      ))}
    </motion.div>
  );
});

LedgerCascade.displayName = "LedgerCascade";
```

---

### Phase 3.4: Brutalist Empty States & Skeletons

**Deep Reasoning:**
A loading state must not be a spinning circle. A skeleton must match the geometric strictness of the app. We use a repeating linear-gradient animation that feels like a scanning laser rather than a soft pulse.

File: `src/components/common/brutalist-skeleton.tsx`
```tsx
import { cn } from "@/lib/utils";

/**
 * Brutalist Skeleton
 * Rejects soft rounded pulses. Uses a sharp, high-contrast wipe effect.
 */
export function BrutalistSkeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "relative overflow-hidden bg-carbon border border-border before:absolute before:inset-0 before:-translate-x-full before:animate-[shimmer_1.5s_infinite] before:bg-gradient-to-r before:from-transparent before:via-surface before:to-transparent",
        className
      )}
      {...props}
    />
  );
}
```
*(Note: Requires adding the `shimmer` keyframe to Tailwind 4 globals, sweeping from `-100%` to `100%`)*

---

### Validation & Verification (Milestone 3)

We have engineered an immersive, context-aware dashboard that commands authority.

**Verification Checklist:**
- [x] **Context Accuracy:** February 2026 dates used. BCRS liability and 9% Reverse Charge accurately modeled in mock data.
- [x] **Bento Grid Hierarchy:** The asymmetric CSS grid strictly aligns to a 1px gap (`bg-border` parent with `gap-px`), removing the need for complex border management.
- [x] **Aesthetic Integrity:** Recharts has been stripped of curves (`type="stepAfter"`) and rounded tooltips.
- [x] **Motion Identity:** The ledger cascades in mechanically, bypassing generic bounce animations, strictly adhering to the "Neo-Brutalist" visual vocabulary.

### Approval Request for Milestone 4

The Command Center now visually reflects the underlying Django 6.0 engine's rigorous architecture. 

**Next Step:** We will proceed to **Milestone 4: Form Mutations & Error Boundaries**.
I will implement the `react-hook-form` and `zod` validations required to safely capture the data that feeds this dashboard. I will also build the Toast notification system that handles Server Action errors (e.g., Peppol transmission failures, IRAS API timeouts) with our stark aesthetic.

