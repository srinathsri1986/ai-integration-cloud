"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { Cable, CheckCircle2, FlaskConical, Save } from "lucide-react";
import type {
  NetSuiteConnectionTestResponse,
  NetSuiteConnectorConfig
} from "@netsuite-cfo/shared";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import {
  type ApiResult,
  testNetSuiteConnection,
  updateNetSuiteConnectorConfig
} from "@/lib/api";

function statusLabel(status: string) {
  return status.replaceAll("_", " ");
}

export function ConnectorStudio({
  initialConfig
}: {
  initialConfig: ApiResult<NetSuiteConnectorConfig>;
}) {
  const [accountId, setAccountId] = useState(initialConfig.data.accountId);
  const [environment, setEnvironment] = useState(initialConfig.data.environment);
  const [config, setConfig] = useState(initialConfig.data);
  const [error, setError] = useState<string | undefined>(
    initialConfig.isFallback ? initialConfig.error : undefined
  );
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<NetSuiteConnectionTestResponse | undefined>();

  async function onSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(undefined);
    setIsSaving(true);

    const response = await updateNetSuiteConnectorConfig({
      accountId,
      authMode: "placeholder",
      environment,
      mockMode: true
    });

    setConfig(response.data);
    setError(response.ok ? undefined : response.error ?? "Unable to save connector config.");
    setIsSaving(false);
  }

  async function onTest() {
    setError(undefined);
    setIsTesting(true);

    const response = await testNetSuiteConnection();
    setTestResult(response.data);
    if (response.ok) {
      setConfig((current) => ({
        ...current,
        lastTestedAt: response.data.testedAt,
        status: response.data.status
      }));
    } else {
      setError(response.error ?? "Unable to test connector.");
    }
    setIsTesting(false);
  }

  return (
    <section className="mx-auto max-w-7xl px-6 pb-12">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-medium text-muted-foreground">Connector Studio</p>
          <h2 className="mt-1 text-xl font-semibold">Mock NetSuite connection</h2>
        </div>
        <Badge className="border-emerald-300 bg-emerald-50 text-emerald-900">
          <FlaskConical className="mr-1 h-3.5 w-3.5" />
          Mock mode
        </Badge>
      </div>

      <Card>
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(320px,420px)]">
          <div>
            <CardHeader>
              <CardTitle>NetSuite connector</CardTitle>
            </CardHeader>
            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <p className="text-sm text-muted-foreground">Status</p>
                <p className="mt-1 font-medium">{statusLabel(config.status)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Auth mode</p>
                <p className="mt-1 font-medium">{config.authMode}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Last tested</p>
                <p className="mt-1 font-medium">
                  {config.lastTestedAt ? new Date(config.lastTestedAt).toLocaleString() : "Never"}
                </p>
              </div>
            </div>

            <p className="mt-5 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
              V0.7 stores placeholder connector settings only. Real credentials, tokens, and
              passwords are not accepted or stored.
            </p>

            {error ? (
              <p className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-950">
                {error}
              </p>
            ) : null}

            {testResult ? (
              <p className="mt-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-950">
                {testResult.message}
              </p>
            ) : null}
          </div>

          <form className="rounded-md border border-border bg-muted/50 p-4" onSubmit={onSave}>
            <div className="flex items-center gap-2">
              <Cable className="h-4 w-4 text-primary" />
              <p className="text-sm font-medium">Placeholder config</p>
            </div>

            <div className="mt-4 space-y-3">
              <div>
                <label className="text-sm text-muted-foreground" htmlFor="netsuite-account-id">
                  Account ID
                </label>
                <input
                  id="netsuite-account-id"
                  className="mt-1 h-10 w-full rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
                  maxLength={64}
                  minLength={3}
                  onChange={(event) => setAccountId(event.target.value)}
                  value={accountId}
                />
              </div>

              <div>
                <label className="text-sm text-muted-foreground" htmlFor="netsuite-environment">
                  Environment
                </label>
                <select
                  id="netsuite-environment"
                  className="mt-1 h-10 w-full rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
                  onChange={(event) =>
                    setEnvironment(event.target.value as NetSuiteConnectorConfig["environment"])
                  }
                  value={environment}
                >
                  <option value="sandbox">Sandbox</option>
                  <option value="production">Production placeholder</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-sm text-muted-foreground">Mock mode</p>
                  <p className="mt-1 font-medium">{config.mockMode ? "Enabled" : "Disabled"}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Credential storage</p>
                  <p className="mt-1 font-medium">Disabled</p>
                </div>
              </div>
            </div>

            <div className="mt-5 flex flex-col gap-3 sm:flex-row">
              <Button disabled={isSaving} type="submit">
                <Save className="h-4 w-4" />
                {isSaving ? "Saving" : "Save config"}
              </Button>
              <Button disabled={isTesting} onClick={onTest} type="button" variant="secondary">
                <CheckCircle2 className="h-4 w-4" />
                {isTesting ? "Testing" : "Test connection"}
              </Button>
            </div>
          </form>
        </div>
      </Card>
    </section>
  );
}
