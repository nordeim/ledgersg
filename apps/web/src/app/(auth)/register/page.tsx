"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle, Lock, Mail, User } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/providers/auth-provider";
import { ApiError } from "@/lib/api-client";

/**
 * P10/H-2 — the registration page. The login page's "Create account" link
 * was a dead `href="#"` while `POST /api/v1/auth/register/` existed with
 * zero frontend consumers: a brand-new self-serve user could not enter the
 * product (P9's organisation-creation page was unreachable without curl).
 *
 * The backend's password floor is 12 characters (AUTH_PASSWORD_VALIDATORS
 * `min_length: 12`); a fresh registration is org-less by design, so a
 * successful registration routes to the organisation-creation page.
 */
export default function RegisterPage() {
  const [error, setError] = React.useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const router = useRouter();
  const { register } = useAuth();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);

    const formData = new FormData(e.currentTarget);
    const fullName = (formData.get("fullName") as string).trim();
    const email = formData.get("email") as string;
    const password = formData.get("password") as string;
    const confirmPassword = formData.get("confirmPassword") as string;

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    try {
      const orgs = await register(email, password, fullName);
      if (orgs.length === 0) {
        // The self-serve loop: a fresh account has no organisation — the
        // P9 org-creation page is the next step.
        router.push("/settings/organisations/new");
      } else {
        router.push("/dashboard");
      }
    } catch (err) {
      if (err instanceof ApiError) {
        switch (err.status) {
          case 429:
            setError(
              "Too many registration attempts. Please wait and try again later."
            );
            break;
          default:
            setError(
              err.message || "Registration failed. Please try again."
            );
        }
      } else {
        setError("Unable to connect to server. Please check your connection.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen flex items-center justify-center bg-void p-4">
      <Card className="w-full max-w-md border-border bg-carbon rounded-sm">
        <CardHeader className="space-y-1 text-center">
          <div className="flex items-center justify-center gap-2 mb-4">
            <div className="w-10 h-10 bg-accent-primary flex items-center justify-center rounded-sm">
              <span className="font-mono font-bold text-void text-xl">L</span>
            </div>
            <h1 className="font-display text-2xl text-text-primary">
              LEDGER<span className="text-accent-primary">SG</span>
            </h1>
          </div>
          <CardDescription className="text-text-secondary">
            Create your account
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <Alert
                variant="destructive"
                className="rounded-sm border-alert bg-alert/10"
              >
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <label
                className="text-sm font-medium text-text-secondary"
                htmlFor="fullName"
              >
                Full Name
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                <Input
                  id="fullName"
                  type="text"
                  name="fullName"
                  required
                  maxLength={255}
                  className={cn(
                    "pl-10 rounded-sm border-border bg-surface",
                    "focus-visible:ring-accent-primary/50"
                  )}
                  placeholder="Tan Ah Kow"
                  disabled={isSubmitting}
                />
              </div>
            </div>

            <div className="space-y-2">
              <label
                className="text-sm font-medium text-text-secondary"
                htmlFor="email"
              >
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                <Input
                  id="email"
                  type="email"
                  name="email"
                  required
                  className={cn(
                    "pl-10 rounded-sm border-border bg-surface",
                    "focus-visible:ring-accent-primary/50"
                  )}
                  placeholder="you@company.sg"
                  disabled={isSubmitting}
                />
              </div>
            </div>

            <div className="space-y-2">
              <label
                className="text-sm font-medium text-text-secondary"
                htmlFor="password"
              >
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                <Input
                  id="password"
                  type="password"
                  name="password"
                  required
                  minLength={12}
                  className={cn(
                    "pl-10 rounded-sm border-border bg-surface",
                    "focus-visible:ring-accent-primary/50"
                  )}
                  placeholder="At least 12 characters"
                  disabled={isSubmitting}
                />
              </div>
            </div>

            <div className="space-y-2">
              <label
                className="text-sm font-medium text-text-secondary"
                htmlFor="confirmPassword"
              >
                Confirm Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                <Input
                  id="confirmPassword"
                  type="password"
                  name="confirmPassword"
                  required
                  minLength={12}
                  className={cn(
                    "pl-10 rounded-sm border-border bg-surface",
                    "focus-visible:ring-accent-primary/50"
                  )}
                  placeholder="Re-enter your password"
                  disabled={isSubmitting}
                />
              </div>
            </div>

            <Button
              type="submit"
              className="w-full rounded-sm bg-accent-primary text-void hover:bg-accent-primary-dim"
              disabled={isSubmitting}
              aria-busy={isSubmitting}
            >
              {isSubmitting ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-void/30 border-t-void rounded-full animate-spin" />
                  Creating account...
                </span>
              ) : (
                "Create Account"
              )}
            </Button>

            <p className="text-center text-sm text-text-secondary">
              Already have an account?{" "}
              <Link
                href="/login"
                className="text-accent-primary hover:text-accent-primary-dim underline-offset-4 hover:underline"
              >
                Sign in
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
