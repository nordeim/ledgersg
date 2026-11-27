/**
 * Format money amount with proper locale
 * 
 * @param amount - Amount string (e.g., "5000.0000")
 * @param decimals - Number of decimal places (default: 2)
 * @returns Formatted string (e.g., "5,000.00")
 */
export function formatMoney(amount: string, decimals: number = 2): string {
  const num = parseFloat(amount);
  return num.toLocaleString("en-SG", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/**
 * Format money amount with currency symbol
 * 
 * @param amount - Amount string (e.g., "5000.0000")
 * @param currency - Currency code (e.g., "SGD", "USD")
 * @param decimals - Number of decimal places (default: 2)
 * @returns Formatted string with currency (e.g., "S$ 5,000.00" or "$ 1,000.00")
 */
export function formatMoneyWithCurrency(
  amount: string,
  currency: string = "SGD",
  decimals: number = 2
): string {
  const num = parseFloat(amount);
  const formatted = num.toLocaleString("en-SG", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  
  // Map currency codes to symbols
  const symbols: Record<string, string> = {
    SGD: "S$",
    USD: "$",
    EUR: "€",
    GBP: "£",
    JPY: "¥",
    MYR: "RM",
    CNY: "¥",
    INR: "₹",
    THB: "฿",
    IDR: "Rp",
    PHP: "₱",
  };
  
  const symbol = symbols[currency] || currency;
  return `${symbol} ${formatted}`;
}

/**
 * Parse money string to number
 * 
 * @param value - Money string (e.g., "5,000.00")
 * @returns Number value
 */
export function parseMoney(value: string): number {
  // Remove all non-numeric characters except decimal point
  const cleaned = value.replace(/[^\d.-]/g, "");
  return parseFloat(cleaned);
}

/**
 * Format a date-only string (e.g. "2024-01-31") for display — timezone-safe.
 *
 * P20/FE-M7: `new Date("YYYY-MM-DD")` parses as UTC midnight, and
 * `toLocaleDateString` then renders in the RUNNER's timezone — one day
 * early for every timezone behind UTC (the Americas). Pinning
 * `timeZone: "UTC"` renders the string's own lexical date everywhere.
 *
 * @param value - date-only string ("YYYY-MM-DD"); other shapes fall back
 *   to best-effort parsing, garbage falls back to the raw string.
 * @returns e.g. "31 Jan 2024"
 */
export function formatDateOnly(value: string): string {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("en-SG", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

/**
 * P21/FE-M3: the year of a date-only ISO string, read LEXICALLY.
 *
 * `new Date("2026-01-01").getFullYear()` reads the year in the RUNNER'S
 * timezone — 2025 for every timezone behind UTC — while the string's own
 * year is unambiguous. Compliance-facing year selection (the GST F5 tab)
 * must not shift with the runner's timezone.
 *
 * @param value - date-only string ("YYYY-MM-DD")
 * @returns the lexical year (NaN for a non-ISO string — callers guard).
 */
export function isoYearOf(value: string): number {
  return Number(value.slice(0, 4));
}

/**
 * P21/FE-M3: today as a date-only ISO string, from LOCAL calendar parts.
 *
 * `new Date().toISOString().slice(0, 10)` returns the UTC day — yesterday
 * for users behind UTC — as the default report/payment dates. The product
 * is Singapore-first (UTC+8, ahead of UTC), so the local calendar is the
 * honest "today" (and matches the pinned Asia/Singapore Playwright runner).
 */
export function localTodayISO(): string {
  const now = new Date();
  return [
    String(now.getFullYear()).padStart(4, "0"),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
  ].join("-");
}
