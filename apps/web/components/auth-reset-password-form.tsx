"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowRight, BrainCircuit, Eye, EyeOff } from "lucide-react";

import { Button } from "@/components/ui/button";
import { resetPassword } from "@/lib/api";

export function AuthResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | undefined>();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(undefined);

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (!token) {
      setError("Missing reset token. Use the link from your email.");
      return;
    }

    setIsLoading(true);
    const result = await resetPassword(token, password);

    if (!result.ok) {
      setError(result.error ?? "Reset failed. The link may have expired.");
      setIsLoading(false);
      return;
    }

    router.push("/login?reset=success");
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_15%_15%,hsl(var(--primary)/0.16),transparent_30rem),linear-gradient(135deg,#f8fafc_0%,#eef2f6_52%,#f6f7fb_100%)] px-5 py-8 flex items-center justify-center">
      <div className="w-full max-w-md">
        <div className="flex items-center gap-3 mb-8 justify-center">
          <span className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <BrainCircuit className="h-5 w-5" />
          </span>
          <span className="text-xl font-semibold text-slate-950">AI Integration Cloud</span>
        </div>

        <div className="rounded-2xl border border-white/80 bg-white/90 p-8 shadow-2xl shadow-slate-300/40 backdrop-blur">
          <div className="mb-6">
            <h1 className="text-2xl font-semibold text-slate-950">Set new password</h1>
            <p className="mt-1 text-sm text-muted-foreground">Choose a strong password for your account.</p>
          </div>

          {!token ? (
            <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
              Invalid reset link. Please request a new one from the{" "}
              <Link className="underline" href="/forgot-password">forgot password</Link> page.
            </p>
          ) : (
            <form className="space-y-4" onSubmit={handleSubmit}>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1" htmlFor="password">
                  New password <span className="text-xs text-muted-foreground font-normal">(min 8 chars, 1 uppercase, 1 digit)</span>
                </label>
                <div className="relative">
                  <input
                    autoComplete="new-password"
                    className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 pr-10 text-sm text-slate-900 placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
                    id="password"
                    minLength={8}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    type={showPassword ? "text" : "password"}
                    value={password}
                  />
                  <button
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-slate-700"
                    onClick={() => setShowPassword((v) => !v)}
                    type="button"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1" htmlFor="confirm-password">Confirm new password</label>
                <input
                  autoComplete="new-password"
                  className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
                  id="confirm-password"
                  minLength={8}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  type="password"
                  value={confirmPassword}
                />
              </div>

              {error ? (
                <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900">{error}</p>
              ) : null}

              <Button className="w-full" disabled={isLoading} type="submit">
                {isLoading ? "Updating…" : "Set new password"}
                {!isLoading && <ArrowRight className="h-4 w-4" />}
              </Button>
            </form>
          )}
        </div>
      </div>
    </main>
  );
}
