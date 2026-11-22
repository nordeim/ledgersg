"use client";

import { useState } from "react";
import { KeyRound, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/providers/auth-provider";
import { api, endpoints, ApiError } from "@/lib/api-client";

/**
 * P10/M-9: the change-password card. The backend endpoint is real (it
 * revokes every refresh token and deletes the session cookies) but had
 * zero UI, while the profile card claimed profile editing lived in "your
 * account settings" — a surface that did not exist. The 12-char floor
 * mirrors the backend (AUTH_PASSWORD_VALIDATORS min_length: 12, the same
 * correction the register page carries).
 */

export function ChangePasswordCard() {
  const { logout } = useAuth();

  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFieldError(null);
    setServerError(null);

    if (!oldPassword) {
      setFieldError("Current password is required.");
      return;
    }
    if (newPassword.length < 12) {
      setFieldError("New password must be at least 12 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setFieldError("Passwords do not match.");
      return;
    }

    setSaving(true);
    try {
      await api.post(endpoints.auth.changePassword, {
        old_password: oldPassword,
        new_password: newPassword,
      });
      // The backend revoked every refresh token and deleted the session
      // cookies — this session is dead; clear client state and land on
      // the login page (the provider's logout seam).
      await logout();
    } catch (err) {
      if (err instanceof ApiError) {
        setServerError(err.message);
      } else if (err instanceof Error) {
        setServerError(err.message);
      } else {
        setServerError("Failed to change password. Please try again.");
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card className="border-border bg-carbon rounded-sm">
      <CardHeader>
        <div className="flex items-center gap-2">
          <KeyRound className="h-5 w-5 text-accent-primary" aria-hidden />
          <CardTitle className="font-display text-lg text-text-primary">
            Change Password
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div className="grid gap-4 md:grid-cols-3">
            <Input
              label="Current password"
              type="password"
              autoComplete="current-password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              disabled={saving}
            />
            <Input
              label="New password"
              type="password"
              autoComplete="new-password"
              minLength={12}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              disabled={saving}
            />
            <Input
              label="Confirm new password"
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              disabled={saving}
            />
          </div>
          {fieldError && (
            <p className="text-sm text-alert" role="alert">
              {fieldError}
            </p>
          )}
          {serverError && (
            <p className="text-sm text-alert" role="alert">
              {serverError}
            </p>
          )}
          <p className="text-xs text-text-muted">
            Changing your password signs you out everywhere (all sessions
            are revoked).
          </p>
          <Button
            type="submit"
            className="rounded-sm bg-accent-primary text-void hover:bg-accent-primary-dim"
            disabled={saving}
          >
            {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Change password
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
