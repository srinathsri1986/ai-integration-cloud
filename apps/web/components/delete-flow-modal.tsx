"use client";

import { useState } from "react";
import { AlertTriangle, Loader2, Trash2 } from "lucide-react";
import type { FlowDefinition } from "@netsuite-cfo/shared";

import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { deleteFlowDefinition } from "@/lib/api";

interface DeleteFlowModalProps {
  flow: FlowDefinition;
  open: boolean;
  onClose: () => void;
  onDeleted: (flowId: string) => void;
}

export function DeleteFlowModal({ flow, open, onClose, onDeleted }: DeleteFlowModalProps) {
  const [confirmText, setConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const confirmed = confirmText === flow.name;

  async function handleDelete() {
    if (!confirmed) return;
    setDeleting(true);
    setError(null);
    const result = await deleteFlowDefinition(flow.flowId);
    setDeleting(false);
    if (!result.ok) {
      setError(result.error ?? "Could not delete integration.");
      return;
    }
    setConfirmText("");
    onDeleted(flow.flowId);
    onClose();
  }

  function handleClose() {
    if (deleting) return;
    setConfirmText("");
    setError(null);
    onClose();
  }

  return (
    <Modal open={open} onClose={handleClose} title="Delete integration">
      <div className="space-y-4">
        <div className="flex items-start gap-3 p-3 rounded-lg bg-rose-50 border border-rose-200">
          <AlertTriangle className="h-5 w-5 text-rose-500 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-rose-800">This action cannot be undone.</p>
            <p className="text-xs text-rose-700 mt-0.5">
              The integration definition and all associated run history will be permanently removed.
            </p>
          </div>
        </div>

        <div>
          <p className="text-sm text-slate-600 mb-2">
            To confirm, type the name of the integration:
          </p>
          <p className="text-sm font-semibold text-slate-900 mb-2 font-mono bg-slate-100 px-2 py-1 rounded">
            {flow.name}
          </p>
          <input
            type="text"
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder="Type integration name to confirm"
            className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-rose-400 bg-white"
            autoFocus
            disabled={deleting}
          />
        </div>

        {error && (
          <p className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded px-2 py-1">
            {error}
          </p>
        )}

        <div className="flex justify-end gap-2 pt-1">
          <Button variant="secondary" onClick={handleClose} disabled={deleting}>
            Cancel
          </Button>
          <Button
            onClick={handleDelete}
            disabled={!confirmed || deleting}
            className="gap-2 bg-rose-600 hover:bg-rose-700 text-white"
          >
            {deleting ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Deleting…</>
            ) : (
              <><Trash2 className="h-4 w-4" /> Delete</>
            )}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
