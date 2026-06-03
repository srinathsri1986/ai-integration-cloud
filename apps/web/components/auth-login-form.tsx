"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, BrainCircuit, Eye, EyeOff } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { loginUser } from "@/lib/api";
import { LOCAL_AUTH_EMAIL_KEY, LOCAL_AUTH_ROLE_KEY } from "@/lib/api";
import { defaultPathForRole } from "@/lib/navigation";

export function AuthLoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | undefined>();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setIsLoading(true);
    setError(undefined);

    const result = await loginUser({ email, password });

    if (!result.ok) {
      setError(result.error ?? "Login failed. Check your email and password.");
      setIsLoading(false);
      return;
    }

    const role = result.data.user.role;
    if (typeof window !== "undefined") {
      window.localStorage.setItem(LOCAL_AUTH_ROLE_KEY, role);
      window.localStorage.setItem(LOCAL_AUTH_EMAIL_KEY, result.data.user.email);
    }
    router.push(defaultPathForRole(role));
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
            <h1 className="text-2xl font-semibold text-slate-950">Sign in</h1>
            <p className="mt-1 text-sm text-muted-foreground">Enter your credentials to access your workspace.</p>
          </div>

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1" htmlFor="email">
                Email
              </label>
              <input
                autoComplete="email"
                className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
                id="email"
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                required
                type="email"
                value={email}
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-sm font-medium text-slate-700" htmlFor="password">
                  Password
                </label>
                <Link className="text-xs text-primary hover:underline" href="/forgot-password">
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <input
                  autoComplete="current-password"
                  className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 pr-10 text-sm text-slate-900 placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
                  id="password"
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

            {error ? (
              <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900">{error}</p>
            ) : null}

            <Button className="w-full" disabled={isLoading} type="submit">
              {isLoading ? "Signing in…" : "Sign in"}
              {!isLoading && <ArrowRight className="h-4 w-4" />}
            </Button>
          </form>

          <div className="mt-6 text-center text-sm text-muted-foreground">
            Don&apos;t have an account?{" "}
            <Link className="text-primary font-medium hover:underline" href="/signup">
              Create one
            </Link>
          </div>

          <div className="mt-4 border-t border-slate-100 pt-4 text-center">
            <Link className="text-xs text-muted-foreground hover:text-slate-700" href="/login/dev">
              Local dev / persona picker
            </Link>
          </div>
        </div>

        <p className="mt-6 text-center text-xs text-muted-foreground">
          <Badge className="border-slate-200 bg-white/80 text-slate-600">Governed iPaaS</Badge>
        </p>
      </div>
    </main>
  );
}
