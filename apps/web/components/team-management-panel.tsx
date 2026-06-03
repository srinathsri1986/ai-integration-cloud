"use client";

import { useEffect, useState } from "react";
import { Mail, Trash2, UserPlus } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  getPendingInvites,
  getTenantMembers,
  inviteMember,
  removeMember,
  type PendingInvite,
  type TenantMember
} from "@/lib/api";

const ROLES = ["Integration Admin", "Developer", "CFO", "Finance Controller", "Viewer"] as const;

const roleBadgeClass: Record<string, string> = {
  "CFO": "border-violet-200 bg-violet-50 text-violet-900",
  "Finance Controller": "border-sky-200 bg-sky-50 text-sky-900",
  "Integration Admin": "border-emerald-200 bg-emerald-50 text-emerald-900",
  "Developer": "border-amber-200 bg-amber-50 text-amber-900",
  "Viewer": "border-slate-200 bg-slate-50 text-slate-700",
};

export function TeamManagementPanel() {
  const [members, setMembers] = useState<TenantMember[]>([]);
  const [invites, setInvites] = useState<PendingInvite[]>([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<string>("Developer");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | undefined>();
  const [success, setSuccess] = useState<string | undefined>();

  async function load() {
    const [membersResult, invitesResult] = await Promise.all([getTenantMembers(), getPendingInvites()]);
    if (membersResult.ok) setMembers(membersResult.data);
    if (invitesResult.ok) setInvites(invitesResult.data);
  }

  useEffect(() => { load(); }, []);

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault();
    setError(undefined);
    setSuccess(undefined);
    setIsLoading(true);
    const result = await inviteMember(inviteEmail, inviteRole);
    if (!result.ok) {
      setError(result.error ?? "Invite failed.");
    } else {
      setSuccess(`Invite sent to ${inviteEmail}.`);
      setInviteEmail("");
      load();
    }
    setIsLoading(false);
  }

  async function handleRemove(userId: number, email: string) {
    if (!window.confirm(`Remove ${email} from the workspace?`)) return;
    setError(undefined);
    const result = await removeMember(userId);
    if (!result.ok) {
      setError(result.error ?? "Remove failed.");
    } else {
      load();
    }
  }

  return (
    <div className="space-y-6">
      {/* Invite form */}
      <Card className="bg-white/90">
        <div className="flex items-center gap-2 mb-4">
          <UserPlus className="h-4 w-4 text-primary" />
          <h2 className="text-lg font-semibold text-slate-950">Invite a team member</h2>
        </div>
        <form className="flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={handleInvite}>
          <div className="flex-1">
            <label className="block text-sm font-medium text-slate-700 mb-1" htmlFor="invite-email">Email</label>
            <input
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
              id="invite-email"
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="colleague@company.com"
              required
              type="email"
              value={inviteEmail}
            />
          </div>
          <div className="w-48">
            <label className="block text-sm font-medium text-slate-700 mb-1" htmlFor="invite-role">Role</label>
            <select
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
              id="invite-role"
              onChange={(e) => setInviteRole(e.target.value)}
              value={inviteRole}
            >
              {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <Button disabled={isLoading} type="submit">
            <Mail className="h-4 w-4" />
            {isLoading ? "Sending…" : "Send invite"}
          </Button>
        </form>
        {error && <p className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900">{error}</p>}
        {success && <p className="mt-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">{success}</p>}
      </Card>

      {/* Members list */}
      <Card className="bg-white/90">
        <h2 className="text-lg font-semibold text-slate-950 mb-4">Members ({members.length})</h2>
        {members.length === 0 ? (
          <p className="text-sm text-muted-foreground">No members loaded. Make sure you are signed in with a verified account.</p>
        ) : (
          <div className="divide-y divide-slate-100">
            {members.map((member) => (
              <div className="flex items-center justify-between py-3" key={member.userId}>
                <div>
                  <p className="text-sm font-medium text-slate-900">{member.email}</p>
                  <Badge className={`mt-1 text-xs ${roleBadgeClass[member.role] ?? "bg-slate-50 text-slate-700"}`}>
                    {member.role}
                  </Badge>
                </div>
                <button
                  className="ml-4 rounded-md p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                  onClick={() => handleRemove(member.userId, member.email)}
                  title="Remove member"
                  type="button"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Pending invites */}
      {invites.length > 0 && (
        <Card className="bg-white/90">
          <h2 className="text-lg font-semibold text-slate-950 mb-4">Pending invites ({invites.length})</h2>
          <div className="divide-y divide-slate-100">
            {invites.map((invite) => (
              <div className="flex items-center justify-between py-3" key={invite.id}>
                <div>
                  <p className="text-sm font-medium text-slate-900">{invite.email}</p>
                  <Badge className={`mt-1 text-xs ${roleBadgeClass[invite.role] ?? "bg-slate-50 text-slate-700"}`}>
                    {invite.role}
                  </Badge>
                </div>
                <Badge className="border-amber-200 bg-amber-50 text-amber-800 text-xs">Pending</Badge>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
