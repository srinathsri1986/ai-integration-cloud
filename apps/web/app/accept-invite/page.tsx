"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { BrainCircuit, CheckCircle2, XCircle } from "lucide-react";

import { Button } from "@/components/ui/button";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function AcceptInviteContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [status, setStatus] = useState<"loading" | "success" | "error" | "needs_login">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("Missing invite token.");
      return;
    }

    fetch(`${API_BASE_URL}/api/v1/tenants/accept-invite`, {
      body: JSON.stringify({ token }),
      cache: "no-store",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      method: "POST",
    })
      .then(async (res) => {
        const body = await res.json();
        if (res.status === 401) {
          setStatus("needs_login");
          setMessage("Sign in first, then open the invite link again.");
        } else if (res.ok) {
          setStatus("success");
          setMessage(body.message ?? "You've joined the workspace.");
          setTimeout(() => router.push("/cfo"), 2000);
        } else {
          setStatus("error");
          setMessage(body.detail ?? "Could not accept invite.");
        }
      })
      .catch(() => {
        setStatus("error");
        setMessage("Could not reach the server. Try again later.");
      });
  }, [token, router]);

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_15%_15%,hsl(var(--primary)/0.16),transparent_30rem),linear-gradient(135deg,#f8fafc_0%,#eef2f6_52%,#f6f7fb_100%)] px-5 py-8 flex items-center justify-center">
      <div className="w-full max-w-md">
        <div className="flex items-center gap-3 mb-8 justify-center">
          <span className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <BrainCircuit className="h-5 w-5" />
          </span>
          <span className="text-xl font-semibold text-slate-950">AI Integration Cloud</span>
        </div>

        <div className="rounded-2xl border border-white/80 bg-white/90 p-8 shadow-2xl shadow-slate-300/40 backdrop-blur text-center">
          {status === "loading" && (
            <>
              <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
              <p className="text-sm text-muted-foreground">Accepting invite…</p>
            </>
          )}
          {status === "success" && (
            <>
              <CheckCircle2 className="mx-auto mb-4 h-12 w-12 text-emerald-500" />
              <h2 className="text-xl font-semibold text-slate-950">Welcome!</h2>
              <p className="mt-2 text-sm text-muted-foreground">{message} Redirecting…</p>
            </>
          )}
          {status === "needs_login" && (
            <>
              <h2 className="text-xl font-semibold text-slate-950">Sign in first</h2>
              <p className="mt-2 text-sm text-muted-foreground">{message}</p>
              <Link className="mt-6 block" href={`/login?next=/accept-invite?token=${token}`}>
                <Button className="w-full" type="button">Sign in</Button>
              </Link>
            </>
          )}
          {status === "error" && (
            <>
              <XCircle className="mx-auto mb-4 h-12 w-12 text-red-500" />
              <h2 className="text-xl font-semibold text-slate-950">Invite failed</h2>
              <p className="mt-2 text-sm text-muted-foreground">{message}</p>
              <Link className="mt-6 block" href="/login">
                <Button className="w-full" type="button" variant="secondary">Go to login</Button>
              </Link>
            </>
          )}
        </div>
      </div>
    </main>
  );
}

export default function AcceptInvitePage() {
  return <Suspense><AcceptInviteContent /></Suspense>;
}
