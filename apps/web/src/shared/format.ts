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
