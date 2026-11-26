/**
 * P16/FE-H3 — the ACRA "other entities" UEN format must validate.
 *
 * The pre-P16 regex (/^[0-9]{8,9}[A-Z]$/) accepted only the business
 * (8-digit) and local-company (9-digit) forms — an LLP's T08LL1234A
 * (a format the BACKEND validator accepts and the repo's own e2e
 * writes) failed invoice-form validation with "Invalid UEN format".
 */
import { describe, expect, it } from "vitest";

import { customerSchema } from "../invoice";

function withUen(uen?: string) {
  return {
    id: "11111111-1111-4111-8111-111111111111",
    name: "Probe Customer",
    ...(uen !== undefined ? { uen } : {}),
  };
}

describe("customer UEN validation (P16/FE-H3)", () => {
  it("accepts the ACRA business form (8 digits + letter)", () => {
    expect(customerSchema.safeParse(withUen("53012345A")).success).toBe(true);
  });

  it("accepts the ACRA local-company form (9 digits + letter)", () => {
    expect(customerSchema.safeParse(withUen("201512345K")).success).toBe(true);
  });

  it("accepts the ACRA other-entities form (LLP: T + YY + LL + 4 digits + letter)", () => {
    const result = customerSchema.safeParse(withUen("T08LL1234A"));
    expect(result.success).toBe(true);
    if (!result.success) {
      console.error(result.error.issues);
    }
  });

  it("accepts the S-prefixed other-entities form (societies)", () => {
    expect(customerSchema.safeParse(withUen("S66FC0789Z")).success).toBe(true);
  });

  it("still rejects the branch-registration 10-digit form and garbage", () => {
    expect(customerSchema.safeParse(withUen("1234567890")).success).toBe(false);
    expect(customerSchema.safeParse(withUen("garbage!!")).success).toBe(false);
  });

  it("uen remains optional (B2C customers)", () => {
    expect(customerSchema.safeParse(withUen()).success).toBe(true);
  });
});
