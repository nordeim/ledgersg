import { z } from "zod";

/**
 * Shared ACRA UEN contract (P17/FE-L6).
 *
 * The three ACRA forms, mirroring the backend's
 * apps/core/validators.py (P16/FE-H3): business (8 digits + letter),
 * local company (9 digits + letter), and other entities
 * (T/S + YY + 2 letters + 4 digits + letter — LLP/society forms).
 *
 * Before this module the full 3-form regex lived only in the invoice
 * customer schema: the org-creation form had no client validation and
 * the PayNow UEN check accepted anything <= 10 chars.
 */
export const uenRegex = /^(?:\d{8}[A-Z]|\d{9}[A-Z]|[TS]\d{2}[A-Z]{2}\d{4}[A-Z])$/;

export const uenSchema = z
  .string()
  .trim()
  .toUpperCase()
  .regex(uenRegex, {
    message:
      "UEN must match an ACRA format: 8 digits + letter (business), " +
      "9 digits + letter (local company), or T/S + YY + 2 letters + " +
      "4 digits + letter (other entities)",
  });

/** Optional UEN: empty/absent is valid (the field is optional everywhere). */
export const optionalUenSchema = z.union([z.literal(""), uenSchema, z.null()]);
