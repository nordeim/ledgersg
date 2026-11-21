"use client";

import * as React from "react";
import { useFormContext } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { MoneyInput } from "@/components/ui/money-input";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Trash2, GripVertical } from "lucide-react";
import {
  TAX_CODES,
  TAX_CODE_DESCRIPTIONS,
  type InvoiceLine,
} from "@/shared/schemas/invoice";
import { calculateLineGST } from "@/lib/gst-engine";
import type { ResolvedTaxCode } from "@/hooks/use-tax-codes";
import { cn } from "@/lib/utils";

/** Lightweight account option for the per-line revenue account select. */
export interface LineAccountOption {
  id: string;
  code: string;
  name: string;
}

interface InvoiceLineRowProps {
  index: number;
  isGSTRegistered: boolean;
  onRemove: () => void;
  /** Org accounts the line can post to (backend add_line requires one). */
  accounts: LineAccountOption[];
  /**
   * Server-resolved tax codes in force on the document date (P3/D-3).
   * Undefined -> static TAX_CODES fallback (backend-less default e2e).
   */
  taxCodes?: ResolvedTaxCode[];
}

function formatRatePercent(rate: string): string {
  // "0.0800" -> "8%", "0.0000" -> "0%", "0.09" -> "9%"
  const pct = Number(rate) * 100;
  return `${Number.isInteger(pct) ? pct : pct.toFixed(2)}%`;
}

export function InvoiceLineRow({
  index,
  isGSTRegistered,
  onRemove,
  accounts,
  taxCodes,
}: InvoiceLineRowProps) {
  const { register, watch, setValue } = useFormContext();

  // Watch line values for real-time calculation
  const line = watch(`lines.${index}`) as InvoiceLine;

  // Resolve the effective rate for the selected tax code from the server
  // rows (fallback: undefined -> static GST_RATES map inside the engine).
  const selectedTaxCode = line?.tax_code as InvoiceLine["tax_code"] | undefined;
  const serverRate = taxCodes?.find((tc) => tc.code === selectedTaxCode)?.rate;

  // Calculate GST in real-time (memoized; field-level deps — the watched
  // line object has unstable identity, memoizing on it would recompute
  // every render and thrash the setValue effect below)
  const computed = React.useMemo(() => {
    if (!line) {
      return {
        display_total: "0.00",
        line_subtotal: "0.0000",
        gst_amount: "0.0000",
        line_total: "0.0000",
      };
    }
    return calculateLineGST(
      line.quantity,
      line.unit_price,
      line.discount_pct,
      line.tax_code,
      line.is_bcrs_deposit,
      serverRate
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps -- field-level deps by design (see above)
  }, [
    line?.quantity,
    line?.unit_price,
    line?.discount_pct,
    line?.tax_code,
    line?.is_bcrs_deposit,
    serverRate,
  ]);

  // Update computed values in form (for submission)
  React.useEffect(() => {
    setValue(`lines.${index}.line_subtotal`, computed.line_subtotal);
    setValue(`lines.${index}.gst_amount`, computed.gst_amount);
    setValue(`lines.${index}.line_total`, computed.line_total);
  }, [computed, index, setValue]);

  if (!line) return null;

  const taxOptions: ResolvedTaxCode[] =
    taxCodes && taxCodes.length > 0
      ? taxCodes
      : TAX_CODES.map((code) => ({
          id: code,
          code,
          name: TAX_CODE_DESCRIPTIONS[code] ?? code,
          rate: "0", // static fallback has no per-date rate; engine map applies
        }));

  return (
    <div
      className={cn(
        "grid gap-2 items-start py-3 border-b border-border last:border-0",
        "grid-cols-12"
      )}
      role="row"
      aria-label={`Invoice line ${index + 1}`}
    >
      {/* Drag Handle */}
      <div className="col-span-1 flex items-center justify-center pt-2">
        <GripVertical className="w-4 h-4 text-text-muted cursor-grab" />
      </div>

      {/* Description */}
      <div className="col-span-3">
        <Input
          {...register(`lines.${index}.description`)}
          placeholder="Item description"
          className={cn(
            "h-10 text-sm border-border bg-surface",
            "focus-visible:ring-accent-primary/50 rounded-sm"
          )}
          aria-label="Line description"
        />
      </div>

      {/* Quantity */}
      <div className="col-span-1">
        <Input
          type="text"
          inputMode="decimal"
          {...register(`lines.${index}.quantity`)}
          className={cn(
            "h-10 text-sm text-right font-mono border-border bg-surface",
            "focus-visible:ring-accent-primary/50 rounded-sm tabular-nums slashed-zero"
          )}
          aria-label="Quantity"
        />
      </div>

      {/* Unit Price */}
      <div className="col-span-2">
        <MoneyInput
          value={line.unit_price}
          onChange={(val) => setValue(`lines.${index}.unit_price`, val)}
          currencySymbol=""
          ariaLabel="Unit price"
          className={cn("h-10 font-mono rounded-sm", "focus-visible:ring-accent-primary/50")}
          decimalScale={4}
        />
      </div>

      {/* Discount % */}
      <div className="col-span-1">
        <Input
          type="text"
          inputMode="decimal"
          {...register(`lines.${index}.discount_pct`)}
          className={cn(
            "h-10 text-sm text-right font-mono border-border bg-surface",
            "focus-visible:ring-accent-primary/50 rounded-sm tabular-nums"
          )}
          aria-label="Discount percentage"
          placeholder="0"
        />
      </div>

      {/* Account (backend add_line requires a posting account) */}
      <div className="col-span-1">
        <Select
          value={line.account_id ?? ""}
          onValueChange={(val) => setValue(`lines.${index}.account_id`, val)}
        >
          <SelectTrigger
            className={cn(
              "h-10 text-xs border-border bg-surface rounded-sm",
              "focus-visible:ring-accent-primary/50"
            )}
            aria-label="Account"
          >
            <SelectValue placeholder="Account" />
          </SelectTrigger>
          <SelectContent>
            {accounts.length === 0 ? (
              <div className="px-3 py-2 text-xs text-text-muted">
                No accounts available
              </div>
            ) : (
              accounts.map((account) => (
                <SelectItem
                  key={account.id}
                  value={account.id}
                  className="text-xs font-mono"
                >
                  {account.code} · {account.name}
                </SelectItem>
              ))
            )}
          </SelectContent>
        </Select>
      </div>

      {/* Tax Code */}
      <div className="col-span-1">
        <Select
          value={line.tax_code}
          onValueChange={(val) =>
            setValue(`lines.${index}.tax_code`, val as typeof TAX_CODES[number])
          }
          disabled={!isGSTRegistered}
        >
          <SelectTrigger
            className={cn(
              "h-10 text-xs border-border bg-surface rounded-sm",
              "focus-visible:ring-accent-primary/50"
            )}
            aria-label="Tax code"
          >
            <SelectValue placeholder="Tax" />
          </SelectTrigger>
          <SelectContent>
            {taxOptions.map((tc) => (
              <SelectItem key={tc.id} value={tc.code} className="text-xs font-mono">
                {serverRate !== undefined || (taxCodes && taxCodes.length > 0)
                  ? `${tc.code} · ${formatRatePercent(tc.rate)}`
                  : tc.code}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Line Total (Read-only, computed) */}
      <div
        className={cn(
          "col-span-1 text-right text-sm font-mono font-medium pt-2",
          "tabular-nums slashed-zero text-text-primary"
        )}
        aria-label="Line total"
        aria-live="polite"
      >
        {computed.display_total}
      </div>

      {/* Remove Button */}
      <div className="col-span-1 flex justify-end pt-1">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={onRemove}
          className={cn(
            "h-8 w-8 text-text-muted hover:text-alert",
            "transition-colors rounded-sm"
          )}
          aria-label={`Remove line ${index + 1}`}
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}
