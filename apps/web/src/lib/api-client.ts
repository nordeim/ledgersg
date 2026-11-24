/**
 * LEDGERSG API CLIENT
 *
 * Purpose: Typed fetch wrapper with error handling, retry logic, JWT refresh
 * All API calls flow through this client for consistency
 *
 * Backend: Django 6.0 + DRF with JWT Authentication
 * - Access token: 15 min expiry, held in module memory only (never storage)
 * - Refresh token: 7 day expiry, set by the backend as an HttpOnly cookie
 *   (login/register/refresh set + rotate it; logout and password change
 *   expire it). The browser replays it via credentials:"include" — this
 *   module never handles the refresh token in JavaScript (P4/E-1).
 * - Refresh triggers on a 401 ONLY when there is evidence a session
 *   exists: an in-memory access token, or the backend's non-secret
 *   `session_hint` marker cookie (JS-readable, set at login) which
 *   carries the cold-reload case. An anonymous 401 (bad login
 *   credentials, unauthenticated visitor) propagates to the caller —
 *   attempting a refresh there floods the refresh endpoint and swallows
 *   the caller's error behind a hard redirect (P4/E-1 refinement).
 * - Org-scoped URLs: /api/v1/{org_id}/invoices/
 */

import { QueryClient, type QueryFunction } from "@tanstack/react-query";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Custom error class for API errors
export class ApiError extends Error {
  constructor(
    public status: number,
    public message: string,
    public errors?: Record<string, string[]>
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// Token management
let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function clearAuth() {
  accessToken = null;
}

// The backend's non-secret session-evidence marker, set alongside the
// HttpOnly refresh cookie at login and expired at logout. The refresh
// cookie itself is invisible to JavaScript by design; this marker is its
// readable companion (see apps/core/views/_refresh_cookie.py).
const SESSION_HINT_COOKIE = "session_hint";

/**
 * Whether the browser carries evidence that an auth session exists —
 * an in-memory access token OR the session_hint marker cookie. The
 * HttpOnly refresh token is deliberately NOT readable here.
 */
function hasSessionEvidence(): boolean {
  if (accessToken) {
    return true;
  }
  if (typeof document === "undefined") {
    return false; // SSR / non-DOM caller — no cookie evidence available
  }
  return document.cookie
    .split(";")
    .some((cookie) => cookie.trim().startsWith(`${SESSION_HINT_COOKIE}=`));
}

// Base request function: fetch + 401 refresh/retry, returns the raw Response
// (single auth path for JSON requests AND binary downloads — P3/D-2).
async function fetchWithAuth(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  const url = `${API_BASE_URL}${endpoint}`;

  // P9/B-1: a FormData body must NOT carry a JSON Content-Type — the
  // browser sets multipart/form-data with the boundary. An explicit
  // application/json header makes the backend parse the body as JSON and
  // request.FILES stays empty (the statement import could never succeed).
  const isFormData =
    typeof FormData !== "undefined" && options.body instanceof FormData;

  const headers: Record<string, string> = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    Accept: "application/json",
    ...(options.headers as Record<string, string>),
  };

  // Add auth header if token exists
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: "include", // Important for HttpOnly refresh cookie
  });

  // Handle 401 — attempt the refresh ONLY when there is evidence a session
  // exists: an in-memory access token (ordinary expiry) or the backend's
  // session_hint marker cookie (cold reload — no access token in memory,
  // the HttpOnly refresh cookie is the only credential left). An anonymous
  // 401 (bad login credentials, unauthenticated visitor) must propagate to
  // the caller: a pointless refresh POST there floods the refresh
  // endpoint's rate limit and swallows the caller's error behind a hard
  // redirect (P4/E-1 refinement, regression-tested in api-client-auth).
  // tryRefreshToken is a plain fetch (not fetchWithAuth), so there is no
  // retry loop.
  if (response.status === 401 && hasSessionEvidence()) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      // Retry the original request with new token
      headers["Authorization"] = `Bearer ${accessToken}`;
      return fetch(url, {
        ...options,
        headers,
        credentials: "include",
      });
    } else {
      // Refresh failed, clear auth
      clearAuth();
      window.location.href = "/login";
      throw new ApiError(401, "Session expired. Please log in again.");
    }
  }

  return response;
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetchWithAuth(endpoint, options);
  return handleResponse<T>(response);
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));

    // P7/F-7: surface the backend's real error messages. The backend
    // envelope (wrap_response / custom_exception_handler) is
    // {"error": {"code", "message", "details"}}; DRF serializer errors are
    // {"field": ["msg"]}. The old reader (message/detail at the top level)
    // matched neither shape, so every business-rule failure surfaced as the
    // generic "Request failed: Bad Request" — hiding messages like
    // "Void reason is required." from users.
    const envelope = (errorData as { error?: { message?: string; details?: Record<string, string[]> } })
      .error;
    const message = resolveErrorMessage(
      errorData,
      envelope?.message,
      `Request failed: ${response.statusText}`
    );

    throw new ApiError(
      response.status,
      message,
      envelope?.details ?? (errorData as { errors?: Record<string, string[]> }).errors
    );
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

/**
 * Extract the first field error from a DRF serializer error body
 * ({"field": ["msg"], ...}) as "field: msg"; returns "" when the body is
 * not a field-error shape.
 */
function extractDrfFieldErrors(errorData: unknown): string {
  if (typeof errorData !== "object" || errorData === null) return "";
  for (const [key, value] of Object.entries(errorData as Record<string, unknown>)) {
    if (Array.isArray(value) && typeof value[0] === "string") {
      return `${key}: ${value[0]}`;
    }
  }
  return "";
}

/**
 * Shared error-message resolution (P8/G-7): the backend envelope, then the
 * legacy top-level keys, then the first DRF field error, then the
 * caller-specific fallback. Extracted so the JSON path AND the blob
 * download path surface identical messages.
 */
function resolveErrorMessage(
  errorData: unknown,
  envelopeMessage: string | undefined,
  fallback: string
): string {
  return (
    envelopeMessage ||
    (errorData as { message?: string }).message ||
    (errorData as { detail?: string }).detail ||
    extractDrfFieldErrors(errorData) ||
    fallback
  );
}

/**
 * Attempt to refresh the access token.
 *
 * The refresh credential comes from the HttpOnly refresh cookie the backend
 * set on login (and rotates on every refresh): the browser attaches it
 * automatically through credentials:"include" — no body, and the refresh
 * token is never handled in JavaScript (zero-JWT-exposure mandate).
 *
 * The backend returns (and rotates) the token pair:
 *   { tokens: { access: "...", refresh: "..." } }
 * Both nested and flat structures are supported for backward
 * compatibility with API clients that used the body flow.
 *
 * @returns {Promise<boolean>} True if token was refreshed successfully
 */
async function tryRefreshToken(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh/`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      console.error(`[Auth] Token refresh failed with status ${response.status}`);
      return false;
    }

    const data = await response.json();

    // Extract access token from response
    // Backend returns: {tokens: {access: "...", refresh: "..."}}
    // Fallback to flat structure: {access: "...", refresh: "..."} for backward compatibility
    const accessToken = data.tokens?.access || data.access;

    if (!accessToken || typeof accessToken !== "string") {
      console.error(
        "[Auth] Invalid or missing access token in refresh response. Expected data.tokens.access or data.access",
        data
      );
      return false;
    }

    setAccessToken(accessToken);
    console.debug("[Auth] Access token refreshed successfully");
    return true;
  } catch (error) {
    console.error("[Auth] Token refresh error:", error);
    return false;
  }
}

// HTTP method helpers
export const api = {
  get: <T>(endpoint: string) => request<T>(endpoint, { method: "GET" }),
  post: <T>(endpoint: string, data?: unknown) =>
    request<T>(endpoint, {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    }),
  /**
   * Multipart POST (P9/B-1): the FormData goes out as the raw body — the
   * browser sets the Content-Type with boundary. Never JSON.stringify a
   * FormData ("{}" with a JSON content-type = the backend's request.FILES
   * is empty).
   */
  postForm: <T>(endpoint: string, data: FormData) =>
    request<T>(endpoint, {
      method: "POST",
      body: data,
    }),
  put: <T>(endpoint: string, data: unknown) =>
    request<T>(endpoint, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  patch: <T>(endpoint: string, data: unknown) =>
    request<T>(endpoint, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  delete: <T>(endpoint: string) => request<T>(endpoint, { method: "DELETE" }),
  /**
   * Authorized binary download (PDF, CSV, …) — same in-memory token and
   * 401-refresh path as the JSON helpers. Never reads tokens from
   * localStorage (zero-JWT-exposure mandate — P3/D-2).
   */
  blob: async (endpoint: string): Promise<Blob> => {
    const response = await fetchWithAuth(endpoint, { method: "GET" });
    if (!response.ok) {
      // P8/G-7: downloads surface the same envelope messages as JSON
      // requests (the pre-P8 reader only looked at top-level keys, so a
      // 404 envelope became "Download failed: Not Found").
      const errorData = await response.json().catch(() => ({}));
      const envelope = (errorData as { error?: { message?: string } }).error;
      throw new ApiError(
        response.status,
        resolveErrorMessage(
          errorData,
          envelope?.message,
          `Download failed: ${response.statusText}`
        )
      );
    }
    return response.blob();
  },
};

// API Endpoints
export const endpoints = {
  // Authentication
  auth: {
    login: "/api/v1/auth/login/",
    // P10/H-2: registration is backend-real (rate-limited, returns tokens +
    // the P4 session cookies) — the login page's dead "Create account" link
    // now routes to the register page that consumes it.
    register: "/api/v1/auth/register/",
    logout: "/api/v1/auth/logout/",
    refresh: "/api/v1/auth/refresh/",
    me: "/api/v1/auth/me/",
    changePassword: "/api/v1/auth/change-password/",
    // P10/M-3: the org switcher persists the chosen org (the backend flips
    // is_default) so the choice survives reloads and devices.
    setDefault: "/api/v1/auth/set-default-org/",
  },

  // Organisations
  organisations: {
    list: "/api/v1/auth/organisations/",
    // P9/O-1: the create endpoint (OrganisationListCreateView) — the
    // onboarding dead-end closer. Distinct from the auth-scoped list.
    create: "/api/v1/organisations/",
    detail: (id: string) => `/api/v1/${id}/`,
    settings: (id: string) => `/api/v1/${id}/settings/`,
    gst: (id: string) => `/api/v1/${id}/gst/`,
  },

  // Invoices (org-scoped) - Aligned with backend: /invoicing/documents/
  invoices: (orgId: string) => ({
    list: `/api/v1/${orgId}/invoicing/documents/`,
    detail: (id: string) => `/api/v1/${orgId}/invoicing/documents/${id}/`,
    // Phase 2: These endpoints will be implemented in the backend
    approve: (id: string) => `/api/v1/${orgId}/invoicing/documents/${id}/approve/`,
    void: (id: string) => `/api/v1/${orgId}/invoicing/documents/${id}/void/`,
    pdf: (id: string) => `/api/v1/${orgId}/invoicing/documents/${id}/pdf/`,
    send: (id: string) => `/api/v1/${orgId}/invoicing/documents/${id}/send/`,
    sendInvoiceNow: (id: string) => `/api/v1/${orgId}/invoicing/documents/${id}/send-invoicenow/`,
    invoiceNowStatus: (id: string) => `/api/v1/${orgId}/invoicing/documents/${id}/invoicenow-status/`,
  }),

  // Contacts (org-scoped) - Aligned with backend: /invoicing/contacts/
  contacts: (orgId: string) => ({
    list: `/api/v1/${orgId}/invoicing/contacts/`,
    detail: (id: string) => `/api/v1/${orgId}/invoicing/contacts/${id}/`,
  }),

  // Journal (org-scoped) - P6/C-5: flat line-level ledger rows
  journal: (orgId: string) => ({
    ledger: `/api/v1/${orgId}/journal-entries/ledger/`,
  }),

  // Dashboard (org-scoped) - FIXED: Added /reports/ prefix to match backend
  dashboard: (orgId: string) => ({
    metrics: `/api/v1/${orgId}/reports/dashboard/metrics/`,
    alerts: `/api/v1/${orgId}/reports/dashboard/alerts/`,
  }),

  // Banking (org-scoped) - All endpoints matching backend
  banking: (orgId: string) => ({
    // Bank Accounts
    accounts: `/api/v1/${orgId}/banking/bank-accounts/`,
    accountDetail: (id: string) => `/api/v1/${orgId}/banking/bank-accounts/${id}/`,
    // Payments
    payments: `/api/v1/${orgId}/banking/payments/`,
    paymentDetail: (id: string) => `/api/v1/${orgId}/banking/payments/${id}/`,
    receivePayment: `/api/v1/${orgId}/banking/payments/receive/`,
    makePayment: `/api/v1/${orgId}/banking/payments/make/`,
    allocatePayment: (id: string) => `/api/v1/${orgId}/banking/payments/${id}/allocate/`,
    voidPayment: (id: string) => `/api/v1/${orgId}/banking/payments/${id}/void/`,
    // Bank Transactions (Reconciliation)
    transactions: `/api/v1/${orgId}/banking/bank-transactions/`,
    transactionImport: `/api/v1/${orgId}/banking/bank-transactions/import/`,
    transactionReconcile: (id: string) => `/api/v1/${orgId}/banking/bank-transactions/${id}/reconcile/`,
    transactionUnreconcile: (id: string) => `/api/v1/${orgId}/banking/bank-transactions/${id}/unreconcile/`,
    transactionSuggestMatches: (id: string) => `/api/v1/${orgId}/banking/bank-transactions/${id}/suggest-matches/`,
  }),

  // Chart of Accounts (org-scoped)
  accounts: (orgId: string) => ({
    list: `/api/v1/${orgId}/accounts/`,
    detail: (id: string) => `/api/v1/${orgId}/accounts/${id}/`,
    types: `/api/v1/${orgId}/accounts/types/`,
  }),

  // GST (org-scoped) — tax codes support ?effective_on=YYYY-MM-DD (P2) to
  // return the rate rows in force on a document date (P3/D-3 wiring).
  // P8/R-7: the full F5 return lifecycle (list / detail / generate /
  // file) joins the client.
  gst: (orgId: string) => ({
    taxCodes: `/api/v1/${orgId}/gst/tax-codes/`,
    calculate: `/api/v1/${orgId}/gst/calculate/`,
    returns: `/api/v1/${orgId}/gst/returns/`,
    returnDetail: (id: string) => `/api/v1/${orgId}/gst/returns/${id}/`,
    returnFile: (id: string) => `/api/v1/${orgId}/gst/returns/${id}/file/`,
    // P10/H-3: the full F5 lifecycle — review (the previously-unrouted
    // edge), amend (reason required), and the deadlines banner.
    returnReview: (id: string) => `/api/v1/${orgId}/gst/returns/${id}/review/`,
    returnAmend: (id: string) => `/api/v1/${orgId}/gst/returns/${id}/amend/`,
    returnDeadlines: `/api/v1/${orgId}/gst/returns/deadlines/`,
  }),

  // Reports (org-scoped) — P8: financial statements (P&L / balance sheet /
  // trial balance) and aged receivables/payables.
  reports: (orgId: string) => ({
    financial: `/api/v1/${orgId}/reports/financial/`,
    aged: `/api/v1/${orgId}/reports/aged/`,
  }),

  // Quotes (org-scoped) — P8/Q-4: quotes are SALES_QUOTE documents on the
  // same documents endpoint (filtered with ?type=) plus the convert route.
  quotes: (orgId: string) => ({
    list: `/api/v1/${orgId}/invoicing/documents/?type=SALES_QUOTE`,
    convert: `/api/v1/${orgId}/invoicing/quotes/convert/`,
  }),

  // Fiscal (org-scoped)
  fiscal: (orgId: string) => ({
    years: `/api/v1/${orgId}/fiscal-years/`,
    periods: `/api/v1/${orgId}/fiscal-periods/`,
    closeYear: (id: string) => `/api/v1/${orgId}/fiscal-years/${id}/close/`,
    closePeriod: (id: string) => `/api/v1/${orgId}/fiscal-periods/${id}/close/`,
    // P10/M-8: the symmetric open act — the approval error named it.
    openPeriod: (id: string) => `/api/v1/${orgId}/fiscal-periods/${id}/open/`,
  }),

  // Peppol
  peppol: (orgId: string) => ({
    transmissionLog: `/api/v1/${orgId}/peppol/transmission-log/`,
    settings: `/api/v1/${orgId}/peppol/settings/`,
  }),
};

// TanStack Query Client Configuration
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        // Don't retry on 401/403
        if (error instanceof ApiError) {
          if (error.status === 401 || error.status === 403) {
            return false;
          }
        }
        return failureCount < 2;
      },
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
    },
    mutations: {
      // P13/M-3: NO retries on mutations — a re-fired non-idempotent POST
      // (payment receive/make/allocate) after a network timeout would
      // double-submit money. React Query's mutation default (0) is the
      // correct policy for a financial client; idempotency keys belong
      // on the backend if retry-on-mutation is ever needed.
      retry: 0,
      onError: (error: unknown) => {
        // Global error handling
        if (error instanceof ApiError) {
          console.error("API Error:", error.message);
        }
      },
    },
  },
});

// Type-safe query hooks factory
export function createQueryHooks<T>(
  key: string,
  fetcher: QueryFunction<T>
) {
  return {
    key: [key],
    fetcher,
  };
}
