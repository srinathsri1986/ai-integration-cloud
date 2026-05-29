"use client";

import { useState } from "react";
import { ShieldCheck, UserRoundCog } from "lucide-react";
import type { UserRole } from "@netsuite-cfo/shared";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { loginWithRole } from "@/lib/api";

const roles: UserRole[] = [
  "Integration Admin",
  "CFO",
  "Finance Controller",
  "Viewer",
  "Developer"
];

export function AccessControlPanel() {
  const [role, setRole] = useState<UserRole>("Integration Admin");
  const [message, setMessage] = useState("Local placeholder session defaults to Integration Admin.");
  const [isSaving, setIsSaving] = useState(false);

  async function applyRole() {
    setIsSaving(true);
    const response = await loginWithRole(role);
    setMessage(
      response.ok
        ? `${response.data.user.role} placeholder token is active for browser actions.`
        : response.error ?? "Unable to create placeholder token."
    );
    setIsSaving(false);
  }

  return (
    <section className="mx-auto max-w-7xl px-6 pt-6">
      <Card className="flex flex-col gap-4 border-sky-200 bg-sky-50/80 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <ShieldCheck className="mt-1 h-5 w-5 text-primary" />
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-semibold">Local access control</p>
              <Badge className="border-sky-300 bg-white text-sky-900">Placeholder JWT</Badge>
            </div>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">{message}</p>
          </div>
        </div>

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <label className="sr-only" htmlFor="local-role">
            Local role
          </label>
          <select
            id="local-role"
            className="h-10 rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
            onChange={(event) => setRole(event.target.value as UserRole)}
            value={role}
          >
            {roles.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
          <Button disabled={isSaving} onClick={applyRole} type="button" variant="secondary">
            <UserRoundCog className="h-4 w-4" />
            {isSaving ? "Applying" : "Apply role"}
          </Button>
        </div>
      </Card>
    </section>
  );
}
