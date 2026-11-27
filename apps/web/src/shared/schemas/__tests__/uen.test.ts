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

describe("the shared schema is actually CONSUMED (P18/FE-M4)", () => {
  it("the invoice customer schema normalizes like the shared module (lowercase UENs accepted)", async () => {
    const { customerSchema } = await import("../invoice");
    const result = customerSchema.safeParse({
      id: "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
      name: "Acme Pte Ltd",
      uen: "t08ll1234a",
    });
    expect(result.success, "a lowercase UEN the backend accepts (it normalizes) must not be a client-side false rejection").toBe(true);
    expect(result.success && result.data.uen).toBe("T08LL1234A");
  });

  it("the org-creation form validates through the shared schema (one error-message source)", async () => {
    // The form module must import the shared schema (not hand-roll the
    // regex + a duplicated message) — the parity contract P17/FE-L6
    // claimed. Source-level: the module imports uenSchema.
    const formSource = (await import("node:fs")).readFileSync(
      (await import("node:path")).resolve(
        __dirname,
        "../../../../src/app/(dashboard)/settings/organisations/new/new-organisation-client.tsx"
      ),
      "utf-8"
    );
    expect(formSource).toMatch(/uenSchema/);
    expect(formSource).not.toMatch(/Invalid UEN format/);
  });

  it("the bank PayNow field reuses the shared module's normalization", async () => {
    const { bankAccountInputSchema } = await import("../bank-account");
    const result = bankAccountInputSchema.safeParse({
      account_name: "Operating",
      bank_name: "Test Bank",
      account_number: "0012345678",
      currency: "SGD",
      gl_account: "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
      paynow_type: "UEN",
      paynow_id: " t08ll1234a ",
    });
    expect(
      result.success,
      "the PayNow UEN check normalizes (trim/uppercase) exactly like the shared schema"
    ).toBe(true);
  });
});
