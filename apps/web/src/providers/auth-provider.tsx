"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { api, endpoints, setAccessToken, clearAuth, ApiError } from "@/lib/api-client";
import { queryClient } from "@/lib/api-client";

// Types matching backend schema
interface User {
  id: string;
  email: string;
  full_name: string;
  phone?: string;
  is_active: boolean;
  last_login_at?: string;
}

interface Organisation {
  id: string;
  name: string;
  legal_name?: string;
  uen?: string;
  entity_type: string;
  gst_registered: boolean;
  gst_reg_number?: string;
  gst_reg_date?: string;
  gst_scheme: string;
  gst_filing_frequency: string;
  peppol_participant_id?: string;
  invoicenow_enabled: boolean;
  fy_start_month: number;
  base_currency: string;
  timezone: string;
  is_active: boolean;
}

interface UserOrganisation {
  id: string;
  org: Organisation;
  role: {
    id: string;
    name: string;
    can_manage_org: boolean;
    can_manage_users: boolean;
    can_manage_coa: boolean;
    can_create_invoices: boolean;
    can_approve_invoices: boolean;
    can_void_invoices: boolean;
    can_create_journals: boolean;
    can_manage_banking: boolean;
    can_file_gst: boolean;
    can_view_reports: boolean;
    can_export_data: boolean;
  };
  is_default: boolean;
}

interface AuthContextType {
  user: User | null;
  organisations: UserOrganisation[];
  currentOrg: Organisation | null;
  currentRole: UserOrganisation["role"] | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  /** P10/H-2: register a brand-new account. The backend returns the same
   * {user, tokens} + P4 session cookies as login; a fresh registration
   * has no organisation — the caller routes to the org-creation page. */
  register: (
    email: string,
    password: string,
    fullName: string
  ) => Promise<UserOrganisation[]>;
  logout: () => Promise<void>;
  switchOrg: (orgId: string) => void;
  /** P16/FE-H2: select an org WITHOUT reading the list state — the
   * org-creation flow's onSuccess closure holds the PRE-creation list
   * (empty for a fresh registrant), so switchOrg's lookup guard
   * silently skipped the selection. */
  selectOrgById: (orgId: string) => void;
  hasPermission: (permission: keyof UserOrganisation["role"]) => boolean;
  /** P8/S-2: re-fetch the organisation list into provider state — after a
   * settings PATCH (rename), the sidebar's org name updates without a
   * reload (the list lived in useState that react-query invalidation
   * could not reach). */
  refreshOrganisations: () => Promise<void>;
}

const AuthContext = React.createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<User | null>(null);
  const [organisations, setOrganisations] = React.useState<UserOrganisation[]>([]);
  const [currentOrgId, setCurrentOrgId] = React.useState<string | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const router = useRouter();

  // Derived state
  const currentOrg = React.useMemo(() => {
    if (!currentOrgId) return null;
    const userOrg = organisations.find((uo) => uo.org.id === currentOrgId);
    return userOrg?.org || null;
  }, [currentOrgId, organisations]);

  const currentRole = React.useMemo(() => {
    if (!currentOrgId) return null;
    const userOrg = organisations.find((uo) => uo.org.id === currentOrgId);
    return userOrg?.role || null;
  }, [currentOrgId, organisations]);

  const isAuthenticated = !!user;

  // Check for existing session on mount
  React.useEffect(() => {
    async function checkSession() {
      try {
        // Try to get current user - this will fail if no valid refresh token
        const userData = await api.get<User>(endpoints.auth.me);
        setUser(userData);
        
      // Fetch user's organisations (returns array directly from auth/organisations/)
      const orgsData = await api.get<UserOrganisation[]>(
        endpoints.organisations.list
      );
      setOrganisations(orgsData);

      // Set default org
      const defaultOrg = orgsData.find((uo) => uo.is_default);
      if (defaultOrg) {
        setCurrentOrgId(defaultOrg.org.id);
      } else if (orgsData.length > 0) {
        setCurrentOrgId(orgsData[0].org.id);
      }
    } catch (error) {
      // P9/S-2: only AUTH failures clear the session — a transport fault
      // (network down, 5xx) keeps the in-memory session so a transient
      // outage does not bounce a logged-in user to /login (the same split
      // refreshOrganisations got in P8).
      const isAuthExpiry =
        error instanceof ApiError && (error.status === 401 || error.status === 403);
      if (!isAuthExpiry) {
        console.warn('[Auth] Session check failed (non-auth error); keeping session state.');
        return;
      }
      // No valid session - redirect to login
      clearAuth();
      // Only redirect from protected pages (prevent redirect loops AND
      // keep public surfaces public: an anonymous visitor on /register
      // gets a plain 401 here — bouncing them to /login raced the
      // registration form and closed the self-serve loop (P10/H-2)).
      if (typeof window !== 'undefined') {
        const currentPath = window.location.pathname;
        const onPublicAuthPage =
          currentPath.includes('/login') || currentPath.includes('/register');
        if (!onPublicAuthPage) {
          const returnUrl = currentPath !== '/' ? `?redirect=${encodeURIComponent(currentPath)}` : '';
          router.push(`/login${returnUrl}`);
        }
      }
    } finally {
      setIsLoading(false);
    }
    }

    checkSession();
    // P19/FE-L7: router is stable in the App Router — declared so the
    // exhaustive-deps gate stays honest (checkSession closes over it).
  }, [router]);

  // P8/S-2: the organisation list is provider state (not a react-query
  // cache), so mutations that change org data must explicitly refresh it.
  const refreshOrganisations = async () => {
    try {
      const orgsData = await api.get<UserOrganisation[]>(
        endpoints.organisations.list
      );
      setOrganisations(orgsData);
    } catch {
      // Transport failures keep the last known list; the session path
      // handles auth expiry.
    }
  };

  const login = async (email: string, password: string) => {
    // Backend returns: { user, tokens: { access, refresh, access_expires } }
    const response = await api.post<{
      user: User;
      tokens: {
        access: string;
        refresh: string;
        access_expires: string;
      };
    }>(endpoints.auth.login, { email, password });

    // Store access token in memory
    setAccessToken(response.tokens.access);
    setUser(response.user);

    // Fetch organisations separately
    const orgsData = await api.get<UserOrganisation[]>(
      endpoints.organisations.list
    );
    setOrganisations(orgsData);

    // Set default org
    const defaultOrg = orgsData.find((uo) => uo.is_default);
    if (defaultOrg) {
      setCurrentOrgId(defaultOrg.org.id);
    } else if (orgsData.length > 0) {
      setCurrentOrgId(orgsData[0].org.id);
    }

    // Invalidate any cached queries
    queryClient.invalidateQueries();
  };

  const register = async (
    email: string,
    password: string,
    fullName: string
  ): Promise<UserOrganisation[]> => {
    // Backend returns: { user, tokens: { access, refresh, access_expires } }
    // and sets the P4 session cookies — same shape as login.
    const response = await api.post<{
      user: User;
      tokens: {
        access: string;
        refresh: string;
        access_expires: string;
      };
    }>(endpoints.auth.register, {
      email,
      password,
      full_name: fullName,
    });

    setAccessToken(response.tokens.access);
    setUser(response.user);

    // A fresh registration is org-less (orgs are user-created by design);
    // fetch whatever exists so the caller can route on the real state.
    const orgsData = await api.get<UserOrganisation[]>(
      endpoints.organisations.list
    );
    setOrganisations(orgsData);
    setCurrentOrgId(
      orgsData.find((uo) => uo.is_default)?.org.id ??
        (orgsData.length > 0 ? orgsData[0].org.id : null)
    );
    queryClient.invalidateQueries();
    return orgsData;
  };

  const logout = async () => {
    try {
      await api.post(endpoints.auth.logout);
    } catch {
      // Ignore logout errors
    } finally {
      clearAuth();
      setUser(null);
      setOrganisations([]);
      setCurrentOrgId(null);
      queryClient.clear();
      router.push("/login");
    }
  };

  // P16/FE-H2: select an org WITHOUT reading the list state. The
  // org-CREATION flow calls this right after creating the org — the
  // caller's closure holds the PRE-creation `organisations` list (empty
  // for a fresh registrant), so a list-lookup guard silently skipped the
  // selection, the invalidation and the persist, dead-ending onboarding
  // on the "No Organisation Selected" screen until a manual reload.
  const selectOrgById = (orgId: string) => {
    setCurrentOrgId(orgId);
    // Invalidate org-scoped queries
    queryClient.invalidateQueries({ queryKey: [orgId] });
    // P10/M-3: persist the choice — POST /auth/set-default-org/ existed
    // with zero callers, so a multi-org user's selection reset to the
    // default on every page refresh. Fire-and-forget: the local switch
    // is immediate; a failed persist (offline) keeps the session.
    api
      .post(endpoints.auth.setDefault, { org_id: orgId })
      .catch((error) => {
        console.warn(
          "[Auth] Failed to persist the default organisation:",
          error instanceof Error ? error.message : error
        );
      });
  };

  const switchOrg = (orgId: string) => {
    const org = organisations.find((uo) => uo.org.id === orgId);
    if (org) {
      selectOrgById(orgId);
    }
  };

  const hasPermission = (permission: keyof UserOrganisation["role"]): boolean => {
    if (!currentRole) return false;
    return currentRole[permission] === true;
  };

  const value: AuthContextType = {
    user,
    organisations,
    currentOrg,
    currentRole,
    isLoading,
    isAuthenticated,
    login,
    register,
    logout,
    switchOrg,
      selectOrgById,
    hasPermission,
    refreshOrganisations,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = React.useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

