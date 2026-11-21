"use client";

import * as React from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
  type ColumnFiltersState,
} from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ChevronUp, ChevronDown, ChevronsUpDown, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import type { LedgerLine } from "@/hooks/use-ledger";

/**
 * Real general-ledger table (P6/C-5 — replaced the mockData fixture).
 * Props-driven: rows come from the backend ledger endpoint via useLedger
 * in the page client; one row per journal line.
 */

function formatMoney(value: string) {
  const n = Number(value);
  if (Number.isNaN(n)) return value;
  return n.toLocaleString("en-SG", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

interface LedgerTableProps {
  data: LedgerLine[];
}

export function LedgerTable({ data }: LedgerTableProps) {
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = React.useState("");

  const columns: ColumnDef<LedgerLine>[] = [
    {
      accessorKey: "entry_number",
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          className="h-8 px-2 font-display text-xs text-text-secondary hover:text-text-primary rounded-sm"
        >
          Entry #
          {column.getIsSorted() === "asc" ? (
            <ChevronUp className="ml-1 h-3 w-3" />
          ) : column.getIsSorted() === "desc" ? (
            <ChevronDown className="ml-1 h-3 w-3" />
          ) : (
            <ChevronsUpDown className="ml-1 h-3 w-3" />
          )}
        </Button>
      ),
      cell: ({ row }) => (
        <span className="font-mono text-sm text-text-primary">
          JE-{String(row.getValue("entry_number")).padStart(5, "0")}
        </span>
      ),
    },
    {
      accessorKey: "entry_date",
      header: "Date",
      cell: ({ row }) => (
        <span className="font-mono text-sm text-text-secondary">
          {row.getValue("entry_date")}
        </span>
      ),
    },
    {
      accessorKey: "account_code",
      header: "Account",
      cell: ({ row }) => (
        <span className="font-mono text-sm text-text-primary">
          {row.getValue("account_code")}
        </span>
      ),
    },
    {
      accessorKey: "account_name",
      header: "Name",
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {row.getValue("account_name")}
        </span>
      ),
    },
    {
      accessorKey: "description",
      header: "Description",
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary max-w-[200px] truncate block">
          {row.getValue("description")}
        </span>
      ),
    },
    {
      accessorKey: "debit",
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          className="h-8 px-2 font-display text-xs text-text-secondary hover:text-text-primary rounded-sm"
        >
          Debit
          {column.getIsSorted() === "asc" ? (
            <ChevronUp className="ml-1 h-3 w-3" />
          ) : column.getIsSorted() === "desc" ? (
            <ChevronDown className="ml-1 h-3 w-3" />
          ) : (
            <ChevronsUpDown className="ml-1 h-3 w-3" />
          )}
        </Button>
      ),
      cell: ({ row }) => {
        const value = row.getValue("debit") as string;
        const isZero = Number(value) === 0;
        return (
          <span
            className={cn(
              "font-mono text-sm text-right tabular-nums slashed-zero block",
              !isZero ? "text-text-primary" : "text-text-muted"
            )}
          >
            {!isZero ? formatMoney(value) : "-"}
          </span>
        );
      },
    },
    {
      accessorKey: "credit",
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          className="h-8 px-2 font-display text-xs text-text-secondary hover:text-text-primary rounded-sm"
        >
          Credit
          {column.getIsSorted() === "asc" ? (
            <ChevronUp className="ml-1 h-3 w-3" />
          ) : column.getIsSorted() === "desc" ? (
            <ChevronDown className="ml-1 h-3 w-3" />
          ) : (
            <ChevronsUpDown className="ml-1 h-3 w-3" />
          )}
        </Button>
      ),
      cell: ({ row }) => {
        const value = row.getValue("credit") as string;
        const isZero = Number(value) === 0;
        return (
          <span
            className={cn(
              "font-mono text-sm text-right tabular-nums slashed-zero block",
              !isZero ? "text-text-primary" : "text-text-muted"
            )}
          >
            {!isZero ? formatMoney(value) : "-"}
          </span>
        );
      },
    },
    {
      accessorKey: "reference",
      header: "Reference",
      cell: ({ row }) => (
        <span className="font-mono text-sm text-text-secondary">
          {row.getValue("reference")}
        </span>
      ),
    },
  ];

  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
      columnFilters,
      globalFilter,
    },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  return (
    <div className="space-y-4">
      {/* Search */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
          <Input
            placeholder="Search entries..."
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            className="pl-9 rounded-sm border-border bg-surface"
            aria-label="Search journal entries"
          />
        </div>
      </div>

      {/* Table */}
      <div className="border border-border rounded-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-surface border-b border-border">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase"
                  >
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y divide-border">
            {table.getRowModel().rows.map((row) => (
              <tr
                key={row.id}
                className="hover:bg-surface/50 transition-colors"
              >
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-4 py-3">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination Info */}
      <div className="flex items-center justify-between text-sm text-text-secondary">
        <span>
          Showing {table.getRowModel().rows.length} of {data.length} entries
        </span>
      </div>
    </div>
  );
}
