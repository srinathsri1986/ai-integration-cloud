"use client";

import { useEffect, useState } from "react";
import { use } from "react";
import { FlowRunDetail } from "@/components/flow-run-detail";
import { PlatformShell } from "@/components/platform-shell";
import { getFlowRun } from "@/lib/api";
import type { FlowRunResponse } from "@ai-integration-cloud/shared";

const POLL_INTERVAL_MS = 3000;

export default function FlowRunDetailPage({
  params
}: {
  params: Promise<{ requestId: string }>;
}) {
  const { requestId } = use(params);
  const [runResult, setRunResult] = useState<{
    data: FlowRunResponse;
    isFallback: boolean;
    error?: string;
    ok: boolean;
  } | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      while (!cancelled) {
        const result = await getFlowRun(requestId);
        if (cancelled) break;
        setRunResult(result);
        if (!result.ok || result.data.status !== "running") break;
        await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
      }
    }

    poll();
    return () => {
      cancelled = true;
    };
  }, [requestId]);

  return (
    <PlatformShell
      active="/flows"
      subtitle="Inspect each integration run with step status, payload previews, warnings, and audit trace identifiers."
      title="Run Detail"
    >
      <div className="-mx-5 lg:-mx-8">
        {runResult ? (
          <FlowRunDetail runResult={runResult} />
        ) : (
          <div className="flex flex-col items-center justify-center gap-3 py-24 text-muted-foreground">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            <p className="text-sm">Loading run detail…</p>
          </div>
        )}
      </div>
    </PlatformShell>
  );
}
