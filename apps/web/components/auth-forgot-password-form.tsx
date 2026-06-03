"use client";

import { useState } from "react";
import Link from "next/link";
import { BrainCircuit } from "lucide-react";

import { Button } from "@/components/ui/button";
import { forgotPassword } from "@/lib/api";

export function AuthForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | undefined>();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setIsLoading(true);
    setError(undefined);
    await forgotPassword(email);
    setIsLoading(false);
    setSent(true);
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
          {sent ? (
            <>
              <h2 className="text-xl font-semibold text-slate-950">Check your inbox</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                If <strong>{email}</strong> is registered and verified, a reset link has been sent. It expires in 1 hour.
              </p>
              <Link className="mt-6 block" href="/login">
                <Button className="w-full" type="button" variant="secondary">Back to sign in</Button>
              </Link>
            </>
          ) : (
            <>
              <div className="mb-6">
                <h1 className="text-2xl font-semibold text-slate-950">Reset password</h1>
                <p className="mt-1 text-sm text-muted-foreground">We&apos;ll send a reset link to your email.</p>
              </div>
              <form className="space-y-4" onSubmit={handleSubmit}>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1" htmlFor="email">Email</label>
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
                {error ? (
                  <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900">{error}</p>
                ) : null}
                <Button className="w-full" disabled={isLoading} type="submit">
                  {isLoading ? "Sending…" : "Send reset link"}
                </Button>
              </form>
              <div className="mt-6 text-center">
                <Link className="text-sm text-primary hover:underline" href="/login">Back to sign in</Link>
              </div>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
