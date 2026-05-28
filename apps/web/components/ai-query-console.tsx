"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { Bot, SendHorizonal } from "lucide-react";
import type { OrchestratorQueryResponse } from "@netsuite-cfo/shared";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { submitOrchestratorQuery } from "@/lib/api";

const exampleQuestion = "Show me P/L vs budget for Q1";

export function AiQueryConsole() {
  const [error, setError] = useState<string | undefined>();
  const [isLoading, setIsLoading] = useState(false);
  const [question, setQuestion] = useState(exampleQuestion);
  const [result, setResult] = useState<OrchestratorQueryResponse | undefined>();

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(undefined);
    setIsLoading(true);

    const response = await submitOrchestratorQuery({
      periodRange: "2026-Q1",
      question,
      subsidiary: "NA"
    });

    setResult(response.data);
    setError(response.ok ? undefined : response.error ?? "Unable to query the orchestrator.");
    setIsLoading(false);
  }

  return (
    <section className="mx-auto max-w-7xl px-6 pt-8">
      <Card>
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(320px,440px)]">
          <div>
            <CardHeader>
              <CardTitle>AI Query Console</CardTitle>
            </CardHeader>
            <form className="flex flex-col gap-3 sm:flex-row" onSubmit={onSubmit}>
              <label className="sr-only" htmlFor="cfo-question">
                CFO question
              </label>
              <input
                id="cfo-question"
                className="h-10 min-w-0 flex-1 rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
                maxLength={500}
                minLength={3}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Ask a CFO question"
                type="text"
                value={question}
              />
              <Button disabled={isLoading} type="submit">
                <SendHorizonal className="h-4 w-4" />
                {isLoading ? "Running" : "Submit"}
              </Button>
            </form>
            {error ? (
              <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
                {error}
              </p>
            ) : null}
          </div>

          <div className="rounded-md border border-border bg-muted/50 p-4">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Bot className="h-4 w-4 text-primary" />
                <p className="text-sm font-medium">Orchestrator result</p>
              </div>
              {result ? <Badge>{result.detectedIntent}</Badge> : <Badge>Waiting</Badge>}
            </div>
            {result ? (
              <div className="mt-4 space-y-3 text-sm">
                <p className="leading-6 text-muted-foreground">{result.executiveSummary}</p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-muted-foreground">Confidence</p>
                    <p className="font-medium">{Math.round(result.confidence * 100)}%</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Fallback</p>
                    <p className="font-medium">{result.fallbackUsed ? "Yes" : "No"}</p>
                  </div>
                </div>
                <div>
                  <p className="text-muted-foreground">Tools used</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {result.toolsUsed.length > 0 ? (
                      result.toolsUsed.map((tool) => <Badge key={tool}>{tool}</Badge>)
                    ) : (
                      <Badge>None</Badge>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <p className="mt-4 text-sm leading-6 text-muted-foreground">
                Ask a CFO question to route it through the deterministic rule-based orchestrator.
              </p>
            )}
          </div>
        </div>
      </Card>
    </section>
  );
}
