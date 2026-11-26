/**
 * Shared UEN schema contract (P17/FE-L6).
 *
 * One source of truth for the three ACRA forms across every client
 * surface: invoice customers, PayNow-UEN bank accounts, organisation
 * creation. Before P17 the full regex lived only in the invoice schema
 * — the org form had no client validation and PayNow accepted anything
 * <= 10 chars.
 */
import { describe, expect, it } from "vitest";

import { uenSchema, optionalUenSchema, uenRegex } from "../uen";

describe("uenSchema (P17/FE-L6)", () => {
  it.each([
    ["53356778D", true], // business: 8 digits + letter
    ["201812345D", true], // local company: 9 digits + letter
    ["T08LL1234A", true], // LLP (the form P16/FE-H3 restored)
    ["S68FC2879B", true], // society/other entities
  ])("%s validates", (value, expected) => {
    const result = uenSchema.safeParse(value);
    expect(result.success).toBe(expected);
  });

  it.each([
    "12345678", // no check letter
    "not-a-uen", // garbage
    "12345678901", // 11 chars — beyond every ACRA form
    "T08LL1234", // other-form missing the final letter
  ])("%s is rejected", (value) => {
    const result = uenSchema.safeParse(value);
    expect(result.success).toBe(false);
  });

  it("normalizes: trims and uppercases before validating", () => {
    const result = uenSchema.safeParse("  t08ll1234a ");
    expect(result.success).toBe(true);
    expect(result.success && result.data).toBe("T08LL1234A");
  });

  it("optionalUenSchema accepts empty/null, validates the rest", () => {
    expect(optionalUenSchema.safeParse("").success).toBe(true);
    expect(optionalUenSchema.safeParse(null).success).toBe(true);
    expect(optionalUenSchema.safeParse("garbage!!").success).toBe(false);
  });

  it("the exported regex matches the invoice schema's P16 contract", () => {
    // The exact pattern the P16 fix shipped in invoice.ts — the shared
    // module must not drift from it.
    expect(uenRegex.source).toBe(
      "^(?:\\d{8}[A-Z]|\\d{9}[A-Z]|[TS]\\d{2}[A-Z]{2}\\d{4}[A-Z])$"
    );
  });
});
