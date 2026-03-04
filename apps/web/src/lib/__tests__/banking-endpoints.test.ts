/**
 * Banking API Endpoints Tests (TDD)
 *
 * Tests validate:
 * - Endpoint paths match backend URL patterns
 * - All banking endpoints are covered
 * - URL parameter substitution works correctly
 *
 * Backend Reference: apps/backend/apps/banking/urls.py
 */

import { describe, it, expect } from "vitest";
import { endpoints } from "../api-client";

describe("Banking API Endpoints", () => {
  const orgId = "test-org-123";
  const accountId = "account-456";
  const paymentId = "payment-789";
  const transactionId = "txn-012";

  describe("Bank Accounts", () => {
    it("should return correct accounts list endpoint", () => {
      const result = endpoints.banking(orgId);
      expect(result.accounts).toBe(`/api/v1/${orgId}/banking/bank-accounts/`);
    });

    it("should return correct account detail endpoint", () => {
      const result = endpoints.banking(orgId);
      expect(result.accountDetail(accountId)).toBe(
        `/api/v1/${orgId}/banking/bank-accounts/${accountId}/`
      );
    });
  });

  describe("Payments", () => {
    it("should return correct payments list endpoint", () => {
      const result = endpoints.banking(orgId);
      expect(result.payments).toBe(`/api/v1/${orgId}/banking/payments/`);
    });

    it("should return correct payment detail endpoint", () => {
      const result = endpoints.banking(orgId);
      expect(result.paymentDetail(paymentId)).toBe(
        `/api/v1/${orgId}/banking/payments/${paymentId}/`
      );
    });

    it("should return correct receive payment endpoint", () => {
      const result = endpoints.banking(orgId);
      expect(result.receivePayment).toBe(`/api/v1/${orgId}/banking/payments/receive/`);
    });

    it("should return correct make payment endpoint", () => {
      const result = endpoints.banking(orgId);
      expect(result.makePayment).toBe(`/api/v1/${orgId}/banking/payments/make/`);
    });

    it("should return correct allocate payment endpoint", () => {
      const result = endpoints.banking(orgId);
      expect(result.allocatePayment(paymentId)).toBe(
        `/api/v1/${orgId}/banking/payments/${paymentId}/allocate/`
      );
    });

    it("should return correct void payment endpoint", () => {
      const result = endpoints.banking(orgId);
      expect(result.voidPayment(paymentId)).toBe(
        `/api/v1/${orgId}/banking/payments/${paymentId}/void/`
      );
    });
  });

  describe("Bank Transactions", () => {
    it("should return correct transactions list endpoint", () => {
      const result = endpoints.banking(orgId);
      expect(result.transactions).toBe(`/api/v1/${orgId}/banking/bank-transactions/`);
    });

    it("should return correct transaction import endpoint", () => {
      const result = endpoints.banking(orgId);
      expect(result.transactionImport).toBe(
        `/api/v1/${orgId}/banking/bank-transactions/import/`
      );
    });

    it("should return correct reconcile transaction endpoint", () => {
      const result = endpoints.banking(orgId);
      expect(result.transactionReconcile(transactionId)).toBe(
        `/api/v1/${orgId}/banking/bank-transactions/${transactionId}/reconcile/`
      );
    });

    it("should return correct unreconcile transaction endpoint", () => {
      const result = endpoints.banking(orgId);
      expect(result.transactionUnreconcile(transactionId)).toBe(
        `/api/v1/${orgId}/banking/bank-transactions/${transactionId}/unreconcile/`
      );
    });

    it("should return correct suggest matches endpoint", () => {
      const result = endpoints.banking(orgId);
      expect(result.transactionSuggestMatches(transactionId)).toBe(
        `/api/v1/${orgId}/banking/bank-transactions/${transactionId}/suggest-matches/`
      );
    });
  });

  describe("Endpoint Parameter Substitution", () => {
    it("should handle different org IDs", () => {
      const org1 = "org-abc-123";
      const org2 = "org-xyz-789";

      const result1 = endpoints.banking(org1);
      const result2 = endpoints.banking(org2);

      expect(result1.accounts).toContain(org1);
      expect(result2.accounts).toContain(org2);
      expect(result1.accounts).not.toBe(result2.accounts);
    });

    it("should handle different account IDs", () => {
      const account1 = "acc-001";
      const account2 = "acc-002";

      const result = endpoints.banking(orgId);

      expect(result.accountDetail(account1)).toContain(account1);
      expect(result.accountDetail(account2)).toContain(account2);
      expect(result.accountDetail(account1)).not.toBe(result.accountDetail(account2));
    });

    it("should handle different payment IDs", () => {
      const payment1 = "pay-001";
      const payment2 = "pay-002";

      const result = endpoints.banking(orgId);

      expect(result.paymentDetail(payment1)).toContain(payment1);
      expect(result.paymentDetail(payment2)).toContain(payment2);
      expect(result.paymentDetail(payment1)).not.toBe(result.paymentDetail(payment2));
    });

    it("should handle different transaction IDs", () => {
      const txn1 = "txn-001";
      const txn2 = "txn-002";

      const result = endpoints.banking(orgId);

      expect(result.transactionReconcile(txn1)).toContain(txn1);
      expect(result.transactionReconcile(txn2)).toContain(txn2);
      expect(result.transactionReconcile(txn1)).not.toBe(result.transactionReconcile(txn2));
    });
  });

  describe("Trailing Slash Consistency", () => {
    it("should have trailing slash on all endpoints", () => {
      const result = endpoints.banking(orgId);

      expect(result.accounts).toMatch(/\/$/);
      expect(result.accountDetail(accountId)).toMatch(/\/$/);
      expect(result.payments).toMatch(/\/$/);
      expect(result.paymentDetail(paymentId)).toMatch(/\/$/);
      expect(result.receivePayment).toMatch(/\/$/);
      expect(result.makePayment).toMatch(/\/$/);
      expect(result.allocatePayment(paymentId)).toMatch(/\/$/);
      expect(result.voidPayment(paymentId)).toMatch(/\/$/);
      expect(result.transactions).toMatch(/\/$/);
      expect(result.transactionImport).toMatch(/\/$/);
      expect(result.transactionReconcile(transactionId)).toMatch(/\/$/);
      expect(result.transactionUnreconcile(transactionId)).toMatch(/\/$/);
      expect(result.transactionSuggestMatches(transactionId)).toMatch(/\/$/);
    });
  });
});
