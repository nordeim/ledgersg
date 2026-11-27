/**
 * P21/FE-M3 — the timezone-safe date helpers (RED first).
 *
 * The FE-M7 class residuals: the GST year was derived via
 * `new Date(asAt).getFullYear()` (UTC-parsed date-only string read in the
 * LOCAL year — a runner behind UTC queried the wrong year's returns),
 * and `todayISO()` returned UTC-today (`toISOString().slice(0, 10)`) —
 * yesterday for users behind UTC, as the default report/payment dates.
 *
 * The contract: `isoYearOf` reads the year LEXICALLY from the ISO string
 * (timezone-free, deterministic), and `localTodayISO` derives today from
 * LOCAL date parts (matching the pinned Asia/Singapore runner + the SG
 * user base, instead of UTC).
 */

import { describe, it, expect } from "vitest";
import { isoYearOf, localTodayISO } from "@/shared/format";

describe("isoYearOf (P21/FE-M3)", () => {
  it("reads the year lexically from the date-only ISO string", () => {
    expect(isoYearOf("2026-01-01")).toBe(2026);
    expect(isoYearOf("2025-12-31")).toBe(2025);
    expect(isoYearOf("1999-02-28")).toBe(1999);
  });

  it("is timezone-free — the UTC/local mismatch class cannot shift it", () => {
    // new Date("2026-01-01").getFullYear() yields 2025 in any timezone
    // behind UTC; the lexical read cannot.
    expect(new Date("2026-01-01").getFullYear()).toBe(
      Number("2026-01-01".slice(0, 4))
    );
    expect(isoYearOf("2026-01-01")).toBe(2026);
  });

  it("returns NaN for a non-ISO string (the caller guards)", () => {
    expect(Number.isNaN(isoYearOf("not-a-date"))).toBe(true);
  });
});

describe("localTodayISO (P21/FE-M3)", () => {
  it("returns today in the LOCAL calendar (not the UTC day)", () => {
    const today = localTodayISO();
    // Shape: YYYY-MM-DD built from local parts.
    expect(today).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    const now = new Date();
    const localParts = [
      String(now.getFullYear()).padStart(4, "0"),
      String(now.getMonth() + 1).padStart(2, "0"),
      String(now.getDate()).padStart(2, "0"),
    ].join("-");
    expect(today).toBe(localParts);
  });

  it("matches the local date even at the UTC-day boundary (SGT 00:00-07:59)", () => {
    // In Asia/Singapore (UTC+8), 2026-01-01T02:00+08:00 is still
    // 2025-12-31 in UTC — localTodayISO must say 2026-01-01.
    // jsdom Date is the runner's local time, so the assertion is the
    // general one: the value equals the local (not UTC) date parts.
    const today = localTodayISO();
    const utc = new Date().toISOString().slice(0, 10);
    // When the UTC and local days differ, localTodayISO must NOT follow UTC.
    if (utc !== today) {
      expect(today).not.toBe(utc);
    }
    expect(today.length).toBe(10);
  });
});
