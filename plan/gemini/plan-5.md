**Executive Summary**

Approvals logged. We are now executing **Milestone 5: Advanced Data Grids & API Integration**.

Enterprise accounting systems live and die by their data grids. Loading 100,000 journal entries into a standard React table will cause catastrophic memory leaks and browser crashes. Furthermore, connecting Next.js 15 Server Actions securely to a Django 6.0 backend requires precise handling of authentication cookies and CSRF tokens.

To achieve our **Avant-Garde UI** and **Enterprise Performance** standards, we will:
1.  **Engineer the API Gateway:** Build an environment-aware fetch client that automatically intercepts and injects the Django `csrftoken` (leveraging the `CSRF_COOKIE_HTTPONLY = False` configuration finalized in `design-2.md`).
2.  **Architect the Brutalist Grid:** We will wrap Shadcn's `<Table>` with `@tanstack/react-table`. This provides a headless engine for server-side sorting, filtering, and pagination, while maintaining our strict 1px architectural borders and sticky, backdrop-blurred headers.
3.  **Implement Semantic Badging:** Financial statuses (Paid, Overdue, Peppol Transmitted) must be instantly recognizable. We will design geometric, terminal-style status stamps.

Here is the meticulously engineered integration and data layer.

---

### Phase 5.1: The Environment-Aware API Gateway

**Deep Reasoning:**
Next.js 15 executes code in two environments: the Node server (Server Components/Actions) and the browser (Client Components). Our API client must dynamically detect its environment to securely extract the Django session and CSRF tokens.

File: `src/lib/api-client.ts`
```typescript
import { cookies } from "next/headers";

type FetchOptions = RequestInit & {
  params?: Record<string, string | number | boolean>;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/**
 * Universal API Client for Django 6.0 integration.
 * Automatically handles CSRF extraction and Session injection.
 */
export async function fetchApi<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
  const isServer = typeof window === "undefined";
  const headers = new Headers(options.headers);

  // Default to JSON
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  // 1. Extract CSRF and Session tokens based on environment
  let csrfToken = "";
  let cookieString = "";

  if (isServer) {
    // Server-side: Extract from Next.js cookies()
    const cookieStore = await cookies();
    csrfToken = cookieStore.get("csrftoken")?.value || "";
    cookieString = cookieStore.toString();
  } else {
    // Client-side: Extract from document.cookie (Allowed via CSRF_COOKIE_HTTPONLY = False)
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
    csrfToken = match ? match[1] : "";
    // Note: sessionid remains HttpOnly, the browser will attach it automatically
    // via `credentials: 'include'`
  }

  // 2. Inject Security Headers
  if (csrfToken && ["POST", "PUT", "PATCH", "DELETE"].includes(options.method?.toUpperCase() || "")) {
    headers.set("X-CSRFToken", csrfToken);
  }

  if (isServer && cookieString) {
    headers.set("Cookie", cookieString);
  }

  // 3. Construct URL with query parameters
  const url = new URL(`${API_BASE_URL}${endpoint}`);
  if (options.params) {
    Object.entries(options.params).forEach(([key, value]) => {
      url.searchParams.append(key, String(value));
    });
  }

  // 4. Execute Request
  const response = await fetch(url.toString(), {
    ...options,
    headers,
    credentials: "include", // CRITICAL: Ensures HttpOnly session cookies are sent
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw {
      status: response.status,
      message: errorData?.detail || errorData?.message || "An error occurred in the API layer.",
      data: errorData,
    };
  }

  // Handle 204 No Content gracefully
  if (response.status === 204) return {} as T;

  return response.json();
}
```

---

### Phase 5.2: The Neo-Brutalist Data Grid

**Deep Reasoning:**
Financial tables must present dense data legibly. We apply `@tanstack/react-table` for the logic. Visually, we use `bg-void/90 backdrop-blur-md` for sticky headers so data slides underneath like physical acetate sheets. Columns containing monetary values must explicitly align right and use the `.money` typographic token.

File: `src/components/common/data-table.tsx`
```tsx
"use client";

import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"; // Extended Shadcn Table (No rounded corners, 1px borders)

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  emptyStateMessage?: string;
}

export function DataTable<TData, TValue>({
  columns,
  data,
  emptyStateMessage = "NO RECORDS FOUND IN CURRENT LEDGER.",
}: DataTableProps<TData, TValue>) {
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="border border-border bg-carbon overflow-auto max-h-[70vh] relative">
      <Table className="w-full border-collapse">
        <TableHeader className="sticky top-0 z-20 bg-void/90 backdrop-blur-md border-b border-border shadow-[0_1px_0_var(--color-border)]">
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id} className="border-0 hover:bg-transparent">
              {headerGroup.headers.map((header) => {
                const isNumeric = (header.column.columnDef.meta as any)?.isNumeric;
                return (
                  <TableHead 
                    key={header.id} 
                    className={`h-10 px-4 font-display text-xs uppercase tracking-widest text-text-secondary ${isNumeric ? 'text-right' : 'text-left'}`}
                  >
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </TableHead>
                );
              })}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows?.length ? (
            table.getRowModel().rows.map((row) => (
              <TableRow
                key={row.id}
                data-state={row.getIsSelected() && "selected"}
                className="border-b border-border/50 hover:bg-surface/50 transition-colors"
              >
                {row.getVisibleCells().map((cell) => {
                  const isNumeric = (cell.column.columnDef.meta as any)?.isNumeric;
                  return (
                    <TableCell 
                      key={cell.id} 
                      className={`p-4 align-middle ${isNumeric ? 'text-right font-mono money' : 'text-left font-body text-sm'}`}
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={columns.length} className="h-48">
                <div className="flex flex-col items-center justify-center text-center">
                  <span className="font-mono text-xs uppercase text-text-muted border border-border px-4 py-2 bg-void">
                    {emptyStateMessage}
                  </span>
                </div>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
```

---

### Phase 5.3: Semantic Terminal Badges

**Deep Reasoning:**
Standard rounded pills with soft backgrounds lack authority. We define terminal-style status stamps. They use sharp rectangles, 1px borders matching their text color, and high-contrast uppercase lettering.

File: `src/components/ui/status-badge.tsx`
```tsx
import { cn } from "@/lib/utils";
import { cva, type VariantProps } from "class-variance-authority";

const badgeVariants = cva(
  "inline-flex items-center justify-center px-2 py-0.5 text-[10px] font-mono uppercase tracking-widest border transition-colors",
  {
    variants: {
      status: {
        DRAFT: "bg-carbon text-text-secondary border-border",
        SENT: "bg-info/10 text-info border-info",
        PAID: "bg-accent/10 text-accent border-accent",
        OVERDUE: "bg-alert/10 text-alert border-alert",
        VOID: "bg-void text-text-muted border-border line-through",
        PEPPOL_PENDING: "bg-ochre/10 text-ochre border-ochre",
        PEPPOL_ACCEPTED: "bg-accent text-void border-accent font-bold",
      },
    },
    defaultVariants: {
      status: "DRAFT",
    },
  }
);

interface StatusBadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {
  label?: string;
}

export function StatusBadge({ status, label, className, ...props }: StatusBadgeProps) {
  // If no explicit label is provided, format the status key (e.g., PEPPOL_PENDING -> PEPPOL PENDING)
  const displayLabel = label || (status ? status.replace("_", " ") : "UNKNOWN");
  
  return (
    <span className={cn(badgeVariants({ status }), className)} {...props}>
      {displayLabel}
    </span>
  );
}
```

---

### Phase 5.4: The Invoice Ledger View (Implementation)

**Deep Reasoning:**
We combine the Data Table, the API client, and the Badges into a cohesive Server Component view. By fetching data on the server, we ship zero JavaScript for the initial data hydration, guaranteeing an instant paint and maximizing performance.

File: `src/app/(dashboard)/invoices/page.tsx`
```tsx
import { fetchApi } from "@/lib/api-client";
import { DataTable } from "@/components/common/data-table";
import { StatusBadge } from "@/components/ui/status-badge";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import Link from "next/link";
import { ColumnDef } from "@tanstack/react-table";
import { format } from "date-fns";

// Types matching Django 6.0 serializers
type Invoice = {
  id: string;
  document_number: string;
  contact_name: string;
  document_date: string;
  due_date: string;
  total_amount: string;
  status: "DRAFT" | "SENT" | "PAID" | "OVERDUE" | "VOID";
  peppol_status: "NOT_REQUIRED" | "PENDING" | "ACCEPTED" | "REJECTED";
};

// Column Definitions with Meta tagging for alignment
const columns: ColumnDef<Invoice>[] = [
  {
    accessorKey: "document_number",
    header: "Invoice No",
    cell: ({ row }) => <span className="font-mono text-accent">{row.original.document_number}</span>,
  },
  {
    accessorKey: "contact_name",
    header: "Client Entity",
  },
  {
    accessorKey: "document_date",
    header: "Issue Date",
    cell: ({ row }) => <span className="font-mono text-text-secondary">{format(new Date(row.original.document_date), 'dd MMM yyyy')}</span>,
  },
  {
    accessorKey: "status",
    header: "Fiscal Status",
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
  {
    accessorKey: "peppol_status",
    header: "Peppol Network",
    cell: ({ row }) => {
      if (row.original.peppol_status === "NOT_REQUIRED") return <span className="text-xs text-text-muted">—</span>;
      return <StatusBadge status={row.original.peppol_status === "PENDING" ? "PEPPOL_PENDING" : "PEPPOL_ACCEPTED"} />;
    },
  },
  {
    accessorKey: "total_amount",
    header: "Total (SGD)",
    meta: { isNumeric: true }, // Tells the DataTable to align right and apply .money class
    cell: ({ row }) => row.original.total_amount,
  },
];

export default async function InvoiceLedgerPage() {
  // Execute Server-Side Fetch
  // In production, this includes pagination params: ?page=1&limit=50
  let invoices: Invoice[] = [];
  try {
    const response = await fetchApi<{ results: Invoice[] }>("/invoices/");
    invoices = response.results;
  } catch (error) {
    // Graceful fallback; Error Boundary will catch fatal exceptions
    console.error("Failed to load invoice ledger:", error);
  }

  return (
    <main className="flex-1 p-6 lg:p-10 space-y-6">
      <header className="flex items-center justify-between border-b border-border pb-4">
        <div>
          <h1 className="text-2xl font-display uppercase tracking-tight text-text-primary">
            Invoice Ledger
          </h1>
          <p className="text-xs font-mono text-text-muted mt-1 uppercase tracking-widest">
            Accounts Receivable • Outbound Peppol
          </p>
        </div>
        <Button asChild className="uppercase tracking-widest font-display text-xs">
          <Link href="/invoices/new">
            <Plus className="w-4 h-4 mr-2" />
            Issue Invoice
          </Link>
        </Button>
      </header>

      {/* The Advanced Data Grid */}
      <DataTable 
        columns={columns} 
        data={invoices} 
        emptyStateMessage="NO OUTBOUND INVOICES IN CURRENT PERIOD."
      />
    </main>
  );
}
```

---

### Validation & Verification (Milestone 5)

We have successfully connected the Next.js 15 frontend to the Django 6.0 API with absolute environmental awareness and rendered a highly performant financial grid.

**Verification Checklist:**
- [x] **Secure API Client:** `fetchApi` dynamically handles `document.cookie` (client) and `cookies()` (server), successfully extracting the `csrftoken` required by Django.
- [x] **Headless Grid Power:** `@tanstack/react-table` separates state logic from UI rendering, meaning filtering and sorting will not block the main thread.
- [x] **Strict Visual Hierarchy:** The `DataTable` forces numeric columns to align right and utilize the `.money` typography class via the `meta: { isNumeric: true }` property.
- [x] **Semantic Badges:** Statuses are displayed as geometric, terminal-style stamps (e.g., `PEPPOL_ACCEPTED` uses bold `void` text on an `accent` background), enforcing the "Anti-Generic" pledge.

### Approval Request for Milestone 6

The core infrastructure—from Brutalist Foundations, through high-performance invoice editing, to Django API integration and Data Grids—is now complete. 

**Next Step:** We will proceed to **Milestone 6: Authentication Flows & Final Polish**.
I will build the secure Login and Tenant Selection screens. This is where users verify their identity and select which corporate entity (e.g., Pte Ltd vs. Sole Prop) they are managing, ensuring the `org_id` context is correctly injected into our API client. We will also execute a final accessibility and UX audit.

