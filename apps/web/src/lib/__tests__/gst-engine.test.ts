/**
 * LEDGERSG GST ENGINE TEST SUITE
 *
 * Critical: 100% coverage required for IRAS compliance
 * Tests all GST calculation scenarios including edge cases
 */

import { describe, it, expect } from "vitest";
import { Decimal } from "decimal.js";
import {
  calculateLineGST,
  calculateInvoiceTotals,
  calculateFromLines,
  validateGSTCalculation,
  formatCurrency,
  getGSTRatePercentage,
  GST_FRACTION,
  type LineGSTResult,
  type InvoiceTotals,
} from "../gst-engine";
import type { InvoiceLine, TaxCode } from "@/shared/schemas/invoice";

describe("GST Engine", () => {
  describe("calculateLineGST", () => {
    describe("Standard-rated (SR) GST - 9%", () => {
      it("calculates GST correctly for basic line item", () => {
        const result = calculateLineGST("10", "100", "0", "SR");

        expect(result.line_subtotal).toBe("1000.0000");
        expect(result.gst_amount).toBe("90.0000");
        expect(result.line_total).toBe("1090.0000");
        expect(result.display_subtotal).toBe("1000.00");
        expect(result.display_gst).toBe("90.00");
        expect(result.display_total).toBe("1090.00");
        expect(result.is_bcrs_exempt).toBe(false);
      });

      it("calculates GST correctly with quantity > 1", () => {
        const result = calculateLineGST("5", "50", "0", "SR");

        expect(result.line_subtotal).toBe("250.0000");
        expect(result.gst_amount).toBe("22.5000");
        expect(result.line_total).toBe("272.5000");
      });

      it("calculates GST correctly with discount", () => {
        const result = calculateLineGST("1", "1000", "10", "SR");

        // Subtotal = 1000 * 0.9 = 900
        expect(result.line_subtotal).toBe("900.0000");
        // GST = 900 * 0.09 = 81
        expect(result.gst_amount).toBe("81.0000");
        expect(result.line_total).toBe("981.0000");
      });

      it("handles decimal quantities correctly", () => {
        const result = calculateLineGST("2.5", "100", "0", "SR");

        expect(result.line_subtotal).toBe("250.0000");
        expect(result.gst_amount).toBe("22.5000");
      });

      it("handles 100% discount (zero amount)", () => {
        const result = calculateLineGST("1", "100", "100", "SR");

        expect(result.line_subtotal).toBe("0.0000");
        expect(result.gst_amount).toBe("0.0000");
        expect(result.line_total).toBe("0.0000");
      });

      it("rounds correctly to 4 decimal places internally", () => {
        const result = calculateLineGST("1", "33.33", "0", "SR");

        // 33.33 * 0.09 = 2.9997 (4dp internal)
        expect(result.gst_amount).toBe("2.9997");
        expect(result.display_gst).toBe("3.00"); // Rounded to 2dp for display
      });
    });

    describe("BCRS Deposit Exemption", () => {
      it("excludes BCRS deposit from GST calculation", () => {
        const result = calculateLineGST("5", "0.10", "0", "SR", true);

        // 5 * 0.10 = 0.50, but no GST because BCRS
        expect(result.line_subtotal).toBe("0.5000");
        expect(result.gst_amount).toBe("0.0000");
        expect(result.line_total).toBe("0.5000");
        expect(result.is_bcrs_exempt).toBe(true);
      });

      it("excludes large BCRS deposit from GST", () => {
        const result = calculateLineGST("100", "0.10", "0", "SR", true);

        expect(result.line_subtotal).toBe("10.0000");
        expect(result.gst_amount).toBe("0.0000");
        expect(result.is_bcrs_exempt).toBe(true);
      });

      it("applies GST when BCRS flag is false", () => {
        const result = calculateLineGST("10", "0.10", "0", "SR", false);

        expect(result.line_subtotal).toBe("1.0000");
        expect(result.gst_amount).toBe("0.0900");
        expect(result.is_bcrs_exempt).toBe(false);
      });
    });

    describe("Zero-rated (ZR) Exports", () => {
      it("applies 0% GST for zero-rated exports", () => {
        const result = calculateLineGST("1", "10000", "0", "ZR");

        expect(result.line_subtotal).toBe("10000.0000");
        expect(result.gst_amount).toBe("0.0000");
        expect(result.line_total).toBe("10000.0000");
      });

      it("handles large export amounts", () => {
        const result = calculateLineGST("1000", "50", "0", "ZR");

        expect(result.line_subtotal).toBe("50000.0000");
        expect(result.gst_amount).toBe("0.0000");
      });
    });

    describe("Exempt (ES) Supplies", () => {
      it("applies 0% GST for exempt supplies", () => {
        const result = calculateLineGST("1", "5000", "0", "ES");

        expect(result.line_subtotal).toBe("5000.0000");
        expect(result.gst_amount).toBe("0.0000");
        expect(result.line_total).toBe("5000.0000");
      });
    });

    describe("Out-of-scope (OS)", () => {
      it("applies 0% GST for out-of-scope items", () => {
        const result = calculateLineGST("1", "2000", "0", "OS");

        expect(result.line_subtotal).toBe("2000.0000");
        expect(result.gst_amount).toBe("0.0000");
      });
    });

    describe("Purchase Tax Codes (TX, BL, RS)", () => {
      it("applies 9% for taxable purchases (TX)", () => {
        const result = calculateLineGST("1", "1000", "0", "TX");

        expect(result.line_subtotal).toBe("1000.0000");
        expect(result.gst_amount).toBe("90.0000");
      });

      it("applies 9% for blocked input tax (BL)", () => {
        const result = calculateLineGST("1", "500", "0", "BL");

        expect(result.line_subtotal).toBe("500.0000");
        expect(result.gst_amount).toBe("45.0000");
      });

      it("applies 9% for reverse charge (RS)", () => {
        const result = calculateLineGST("1", "2000", "0", "RS");

        expect(result.line_subtotal).toBe("2000.0000");
        expect(result.gst_amount).toBe("180.0000");
      });
    });

    describe("Edge Cases & Validation", () => {
      it("handles zero quantity", () => {
        const result = calculateLineGST("0", "100", "0", "SR");

        expect(result.line_subtotal).toBe("0.0000");
        expect(result.gst_amount).toBe("0.0000");
        expect(result.line_total).toBe("0.0000");
      });

      it("handles zero price", () => {
        const result = calculateLineGST("10", "0", "0", "SR");

        expect(result.line_subtotal).toBe("0.0000");
        expect(result.gst_amount).toBe("0.0000");
      });

      it("handles empty string inputs as zero", () => {
        const result = calculateLineGST("", "", "", "SR");

        expect(result.line_subtotal).toBe("0.0000");
        expect(result.gst_amount).toBe("0.0000");
      });

      it("handles invalid tax code as 0%", () => {
        const result = calculateLineGST("1", "100", "0", "INVALID" as TaxCode);

        expect(result.line_subtotal).toBe("100.0000");
        expect(result.gst_amount).toBe("0.0000");
      });

      it("handles negative discount gracefully", () => {
        const result = calculateLineGST("1", "100", "-10", "SR");

        // Negative discount increases amount: 100 * 1.1 = 110
        expect(result.line_subtotal).toBe("110.0000");
        expect(result.gst_amount).toBe("9.9000");
      });
    });
  });

  describe("calculateInvoiceTotals", () => {
    it("calculates totals for single line item", () => {
      const lines: LineGSTResult[] = [
        {
          line_subtotal: "1000.0000",
          gst_amount: "90.0000",
          line_total: "1090.0000",
          display_subtotal: "1000.00",
          display_gst: "90.00",
          display_total: "1090.00",
          is_bcrs_exempt: false,
        },
      ];

      const result = calculateInvoiceTotals(lines);

      expect(result.subtotal).toBe("1000.0000");
      expect(result.gst_amount).toBe("90.0000");
      expect(result.total_amount).toBe("1090.0000");
    });

    it("calculates totals for multiple line items", () => {
      const lines: LineGSTResult[] = [
        {
          line_subtotal: "1000.0000",
          gst_amount: "90.0000",
          line_total: "1090.0000",
          display_subtotal: "1000.00",
          display_gst: "90.00",
          display_total: "1090.00",
          is_bcrs_exempt: false,
        },
        {
          line_subtotal: "500.0000",
          gst_amount: "45.0000",
          line_total: "545.0000",
          display_subtotal: "500.00",
          display_gst: "45.00",
          display_total: "545.00",
          is_bcrs_exempt: false,
        },
      ];

      const result = calculateInvoiceTotals(lines);

      expect(result.subtotal).toBe("1500.0000");
      expect(result.gst_amount).toBe("135.0000");
      expect(result.total_amount).toBe("1635.0000");
      expect(result.display_subtotal).toBe("1500.00");
      expect(result.display_gst).toBe("135.00");
      expect(result.display_total).toBe("1635.00");
    });

    it("separates BCRS deposits from GST calculation", () => {
      const lines: LineGSTResult[] = [
        {
          line_subtotal: "1000.0000",
          gst_amount: "90.0000",
          line_total: "1090.0000",
          display_subtotal: "1000.00",
          display_gst: "90.00",
          display_total: "1090.00",
          is_bcrs_exempt: false,
        },
        {
          line_subtotal: "10.0000",
          gst_amount: "0.0000",
          line_total: "10.0000",
          display_subtotal: "10.00",
          display_gst: "0.00",
          display_total: "10.00",
          is_bcrs_exempt: true,
        },
      ];

      const result = calculateInvoiceTotals(lines);

      expect(result.subtotal).toBe("1000.0000");
      expect(result.gst_amount).toBe("90.0000");
      expect(result.bcrs_deposit_total).toBe("10.0000");
      expect(result.total_amount).toBe("1100.0000");
      expect(result.display_bcrs).toBe("10.00");
    });

    it("handles all BCRS deposits (no GST)", () => {
      const lines: LineGSTResult[] = [
        {
          line_subtotal: "5.0000",
          gst_amount: "0.0000",
          line_total: "5.0000",
          display_subtotal: "5.00",
          display_gst: "0.00",
          display_total: "5.00",
          is_bcrs_exempt: true,
        },
        {
          line_subtotal: "3.0000",
          gst_amount: "0.0000",
          line_total: "3.0000",
          display_subtotal: "3.00",
          display_gst: "0.00",
          display_total: "3.00",
          is_bcrs_exempt: true,
        },
      ];

      const result = calculateInvoiceTotals(lines);

      expect(result.subtotal).toBe("0.0000");
      expect(result.gst_amount).toBe("0.0000");
      expect(result.bcrs_deposit_total).toBe("8.0000");
      expect(result.total_amount).toBe("8.0000");
    });

    it("handles empty lines array", () => {
      const result = calculateInvoiceTotals([]);

      expect(result.subtotal).toBe("0.0000");
      expect(result.gst_amount).toBe("0.0000");
      expect(result.bcrs_deposit_total).toBe("0.0000");
      expect(result.total_amount).toBe("0.0000");
    });

    it("handles mixed tax codes correctly", () => {
      const lines: LineGSTResult[] = [
        // Standard rated
        { line_subtotal: "1000", gst_amount: "90", line_total: "1090", display_subtotal: "1000", display_gst: "90", display_total: "1090", is_bcrs_exempt: false },
        // Zero rated
        { line_subtotal: "500", gst_amount: "0", line_total: "500", display_subtotal: "500", display_gst: "0", display_total: "500", is_bcrs_exempt: false },
        // Exempt
        { line_subtotal: "300", gst_amount: "0", line_total: "300", display_subtotal: "300", display_gst: "0", display_total: "300", is_bcrs_exempt: false },
      ];

      const result = calculateInvoiceTotals(lines);

      expect(result.subtotal).toBe("1800.0000");
      expect(result.gst_amount).toBe("90.0000");
      expect(result.total_amount).toBe("1890.0000");
    });
  });

  describe("calculateFromLines", () => {
    it("calculates from InvoiceLine objects", () => {
      const lines: InvoiceLine[] = [
        {
          id: "1",
          description: "Test item 1",
          quantity: "10",
          unit_price: "100",
          discount_pct: "0",
          tax_code: "SR",
          is_bcrs_deposit: false,
        },
        {
          id: "2",
          description: "Test item 2",
          quantity: "5",
          unit_price: "50",
          discount_pct: "10",
          tax_code: "SR",
          is_bcrs_deposit: false,
        },
      ];

      const { lineResults, totals } = calculateFromLines(lines);

      expect(lineResults).toHaveLength(2);
      expect(totals.subtotal).toBeDefined();
      expect(totals.gst_amount).toBeDefined();
      expect(totals.total_amount).toBeDefined();
    });
  });

  describe("validateGSTCalculation", () => {
    it("returns valid when calculations match", () => {
      const clientTotals: InvoiceTotals = {
        subtotal: "1000.0000",
        gst_amount: "90.0000",
        bcrs_deposit_total: "0.0000",
        total_amount: "1090.0000",
        display_subtotal: "1000.00",
        display_gst: "90.00",
        display_bcrs: "0.00",
        display_total: "1090.00",
      };

      const serverTotals = {
        subtotal: "1000.00",
        gst_amount: "90.00",
        total_amount: "1090.00",
      };

      const result = validateGSTCalculation(clientTotals, serverTotals);

      expect(result.valid).toBe(true);
      expect(result.discrepancies).toHaveLength(0);
    });

    it("detects subtotal mismatch", () => {
      const clientTotals: InvoiceTotals = {
        subtotal: "1000.0000",
        gst_amount: "90.0000",
        bcrs_deposit_total: "0.0000",
        total_amount: "1090.0000",
        display_subtotal: "1000.00",
        display_gst: "90.00",
        display_bcrs: "0.00",
        display_total: "1090.00",
      };

      const serverTotals = {
        subtotal: "999.98", // 2 cent difference (beyond tolerance)
        gst_amount: "90.00",
        total_amount: "1090.00",
      };

      const result = validateGSTCalculation(clientTotals, serverTotals);

      expect(result.valid).toBe(false);
      expect(result.discrepancies).toHaveLength(1);
      expect(result.discrepancies[0]).toContain("Subtotal mismatch");
    });

    it("detects GST mismatch", () => {
      const clientTotals: InvoiceTotals = {
        subtotal: "1000.0000",
        gst_amount: "90.0000",
        bcrs_deposit_total: "0.0000",
        total_amount: "1090.0000",
        display_subtotal: "1000.00",
        display_gst: "90.00",
        display_bcrs: "0.00",
        display_total: "1090.00",
      };

      const serverTotals = {
        subtotal: "1000.00",
        gst_amount: "89.98", // 2 cent difference (beyond tolerance)
        total_amount: "1090.00",
      };

      const result = validateGSTCalculation(clientTotals, serverTotals);

      expect(result.valid).toBe(false);
      expect(result.discrepancies[0]).toContain("GST mismatch");
    });

    it("allows 1 cent tolerance for rounding differences", () => {
      const clientTotals: InvoiceTotals = {
        subtotal: "1000.0000",
        gst_amount: "90.0000",
        bcrs_deposit_total: "0.0000",
        total_amount: "1090.0000",
        display_subtotal: "1000.00",
        display_gst: "90.00",
        display_bcrs: "0.00",
        display_total: "1090.00",
      };

      const serverTotals = {
        subtotal: "1000.00",
        gst_amount: "90.01", // 1 cent difference (within tolerance)
        total_amount: "1090.00",
      };

      const result = validateGSTCalculation(clientTotals, serverTotals);

      expect(result.valid).toBe(true); // Within 1 cent tolerance
    });

    it("detects total mismatch", () => {
      const clientTotals: InvoiceTotals = {
        subtotal: "1000.0000",
        gst_amount: "90.0000",
        bcrs_deposit_total: "0.0000",
        total_amount: "1090.0000",
        display_subtotal: "1000.00",
        display_gst: "90.00",
        display_bcrs: "0.00",
        display_total: "1090.00",
      };

      const serverTotals = {
        subtotal: "1000.00",
        gst_amount: "90.00",
        total_amount: "1090.02", // 2 cent difference (beyond tolerance)
      };

      const result = validateGSTCalculation(clientTotals, serverTotals);

      expect(result.valid).toBe(false);
      expect(result.discrepancies[0]).toContain("Total mismatch");
    });
  });

  describe("formatCurrency", () => {
    it("formats positive amounts", () => {
      expect(formatCurrency("1000")).toBe("S$ 1000.00");
      expect(formatCurrency("1000.50")).toBe("S$ 1000.50");
    });

    it("formats zero", () => {
      expect(formatCurrency("0")).toBe("S$ 0.00");
      expect(formatCurrency(0)).toBe("S$ 0.00");
    });

    it("formats Decimal values", () => {
      expect(formatCurrency(new Decimal("500.50"))).toBe("S$ 500.50");
    });

    it("handles empty string", () => {
      expect(formatCurrency("")).toBe("S$ 0.00");
    });

    it("rounds to 2 decimal places", () => {
      expect(formatCurrency("1000.999")).toBe("S$ 1001.00");
      expect(formatCurrency("1000.001")).toBe("S$ 1000.00");
    });
  });

  describe("getGSTRatePercentage", () => {
    it("returns 9% for SR", () => {
      expect(getGSTRatePercentage("SR")).toBe("9%");
    });

    it("returns 0% for ZR", () => {
      expect(getGSTRatePercentage("ZR")).toBe("0%");
    });

    it("returns 0% for ES", () => {
      expect(getGSTRatePercentage("ES")).toBe("0%");
    });

    it("returns 0% for OS", () => {
      expect(getGSTRatePercentage("OS")).toBe("0%");
    });

    it("returns 9% for TX", () => {
      expect(getGSTRatePercentage("TX")).toBe("9%");
    });

    it("returns 9% for BL", () => {
      expect(getGSTRatePercentage("BL")).toBe("9%");
    });

    it("returns 9% for RS", () => {
      expect(getGSTRatePercentage("RS")).toBe("9%");
    });

    it("returns 0% for invalid tax code", () => {
      expect(getGSTRatePercentage("INVALID" as TaxCode)).toBe("0%");
    });
  });

  describe("GST_FRACTION constant", () => {
    it("equals 9/109 for 9% GST rate", () => {
      const expected = new Decimal("9").div(new Decimal("109"));
      expect(GST_FRACTION.toFixed(10)).toBe(expected.toFixed(10));
    });

    it("can be used for GST-inclusive calculations", () => {
      // For a GST-inclusive price of 109, extract GST: 109 * (9/109) = 9
      const inclusivePrice = new Decimal("109");
      const gstComponent = inclusivePrice.mul(GST_FRACTION);
      expect(gstComponent.toDecimalPlaces(2).toFixed(2)).toBe("9.00");
    });
  });
});

/**
 * IRAS COMPLIANCE TEST SCENARIOS
 *
 * These tests verify calculations match IRAS examples and regulations
 */
describe("IRAS Compliance Scenarios", () => {
  it("IRAS Example: Standard-rated supply", () => {
    // Typical sale with 9% GST
    const result = calculateLineGST("1", "1000", "0", "SR");

    expect(result.display_subtotal).toBe("1000.00");
    expect(result.display_gst).toBe("90.00");
    expect(result.display_total).toBe("1090.00");
  });

  it("IRAS Example: Zero-rated export to overseas customer", () => {
    const result = calculateLineGST("1", "5000", "0", "ZR");

    expect(result.display_subtotal).toBe("5000.00");
    expect(result.display_gst).toBe("0.00");
    expect(result.display_total).toBe("5000.00");
  });

  it("IRAS Example: Exempt supply (residential property rental)", () => {
    const result = calculateLineGST("1", "3000", "0", "ES");

    expect(result.display_subtotal).toBe("3000.00");
    expect(result.display_gst).toBe("0.00");
  });

  it("BCRS Scenario: Deposit on pre-packaged beverage", () => {
    // $0.10 deposit per container, 100 containers
    const result = calculateLineGST("100", "0.10", "0", "SR", true);

    expect(result.display_subtotal).toBe("10.00");
    expect(result.display_gst).toBe("0.00");
    expect(result.is_bcrs_exempt).toBe(true);
  });

  it("Mixed scenario: Beverage sale with BCRS deposit", () => {
    // Invoice with beverage ($1.50 + GST) + BCRS deposit ($0.10, no GST)
    const lines: InvoiceLine[] = [
      { id: "1", description: "Beverage", quantity: "1", unit_price: "1.50", discount_pct: "0", tax_code: "SR", is_bcrs_deposit: false },
      { id: "2", description: "BCRS Deposit", quantity: "1", unit_price: "0.10", discount_pct: "0", tax_code: "SR", is_bcrs_deposit: true },
    ];

    const { totals } = calculateFromLines(lines);

    expect(totals.display_subtotal).toBe("1.50"); // Only beverage subject to GST
    expect(totals.display_gst).toBe("0.14"); // 1.50 * 0.09 = 0.135, rounded to 0.14
    expect(totals.display_bcrs).toBe("0.10");
    expect(totals.display_total).toBe("1.74"); // 1.50 + 0.14 + 0.10
  });

  it("Precision test: IRAS requires 4dp internal, 2dp display", () => {
    const result = calculateLineGST("1", "33.33", "0", "SR");

    // Internal: 4 decimal places
    expect(result.line_subtotal).toBe("33.3300");
    expect(result.gst_amount).toMatch(/^\d+\.\d{4}$/); // 4 decimal places

    // Display: 2 decimal places
    expect(result.display_subtotal).toMatch(/^\d+\.\d{2}$/); // 2 decimal places
    expect(result.display_gst).toMatch(/^\d+\.\d{2}$/);
  });
});
