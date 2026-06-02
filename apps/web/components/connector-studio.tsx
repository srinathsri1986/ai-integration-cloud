"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import {
  Cable,
  CheckCircle2,
  DatabaseZap,
  FlaskConical,
  Globe2,
  KeyRound,
  LockKeyhole,
  Network,
  Save,
  ShieldCheck,
  Sparkles,
  Workflow
} from "lucide-react";
import type {
  NetSuiteConnectionTestResponse,
  NetSuiteConnectorConfig,
  RestApiApprovedObject,
  RestApiConnectionTestResponse,
  RestApiConnectorConfig
} from "@netsuite-cfo/shared";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import {
  type ApiResult,
  testRestApiConnection,
  testNetSuiteConnection,
  updateRestApiConnectorConfig,
  updateNetSuiteConnectorConfig
} from "@/lib/api";

function statusLabel(status: string) {
  return status.replaceAll("_", " ");
}

function readinessLabel(value: boolean) {
  return value ? "Ready" : "Missing";
}

export function ConnectorStudio({
  initialConfig,
  initialRestApiConfig,
  initialRestApiObjects
}: {
  initialConfig: ApiResult<NetSuiteConnectorConfig>;
  initialRestApiConfig: ApiResult<RestApiConnectorConfig>;
  initialRestApiObjects: ApiResult<RestApiApprovedObject[]>;
}) {
  const [accountId, setAccountId] = useState(initialConfig.data.accountId);
  const [environment, setEnvironment] = useState(initialConfig.data.environment);
  const [config, setConfig] = useState(initialConfig.data);
  const [restApiDisplayName, setRestApiDisplayName] = useState(
    initialRestApiConfig.data.displayName
  );
  const [restApiBaseUrl, setRestApiBaseUrl] = useState(
    initialRestApiConfig.data.baseUrlPlaceholder
  );
  const [restApiConfig, setRestApiConfig] = useState(initialRestApiConfig.data);
  const [restApiObjects] = useState(initialRestApiObjects.data);
  const [error, setError] = useState<string | undefined>(
    initialConfig.isFallback ? initialConfig.error : undefined
  );
  const [restApiError, setRestApiError] = useState<string | undefined>(
    initialRestApiConfig.isFallback
      ? initialRestApiConfig.error
      : initialRestApiObjects.isFallback
        ? initialRestApiObjects.error
        : undefined
  );
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [isSavingRestApi, setIsSavingRestApi] = useState(false);
  const [isTestingRestApi, setIsTestingRestApi] = useState(false);
  const [testResult, setTestResult] = useState<NetSuiteConnectionTestResponse | undefined>();
  const [restApiTestResult, setRestApiTestResult] = useState<
    RestApiConnectionTestResponse | undefined
  >();

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

  async function onSaveRestApi(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRestApiError(undefined);
    setIsSavingRestApi(true);

    const response = await updateRestApiConnectorConfig({
      authMode: "placeholder",
      baseUrlPlaceholder: restApiBaseUrl,
      displayName: restApiDisplayName,
      mockMode: true
    });

    setRestApiConfig(response.data);
    setRestApiError(response.ok ? undefined : response.error ?? "Unable to save REST API config.");
    setIsSavingRestApi(false);
  }

  async function onTestRestApi() {
    setRestApiError(undefined);
    setIsTestingRestApi(true);

    const response = await testRestApiConnection();
    setRestApiTestResult(response.data);
    if (response.ok) {
      setRestApiConfig((current) => ({
        ...current,
        lastTestedAt: response.data.testedAt,
        status: response.data.status
      }));
    } else {
      setRestApiError(response.error ?? "Unable to test REST API connector.");
    }
    setIsTestingRestApi(false);
  }

  return (
    <section className="mx-auto max-w-7xl space-y-8 px-6 pb-12">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-medium text-muted-foreground">Connector Studio</p>
          <h2 className="mt-1 text-xl font-semibold">NetSuite sandbox gateway</h2>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge
            className={
              config.mode === "sandbox"
                ? "border-sky-300 bg-sky-50 text-sky-950"
                : "border-emerald-300 bg-emerald-50 text-emerald-900"
            }
          >
            {config.mode === "sandbox" ? (
              <DatabaseZap className="mr-1 h-3.5 w-3.5" />
            ) : (
              <FlaskConical className="mr-1 h-3.5 w-3.5" />
            )}
            {config.mode === "sandbox" ? "Sandbox mode" : "Mock mode"}
          </Badge>
          <Badge className="border-slate-300 bg-white text-slate-700">
            <ShieldCheck className="mr-1 h-3.5 w-3.5" />
            Approved actions only
          </Badge>
        </div>
      </div>

      <Card className="overflow-hidden p-0">
        <div className="grid lg:grid-cols-[minmax(0,1fr)_420px]">
          <div className="p-5">
            <CardHeader>
              <CardTitle>Connector posture</CardTitle>
            </CardHeader>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-md border border-border bg-slate-50 p-3">
                <p className="text-sm text-muted-foreground">Status</p>
                <p className="mt-1 text-base font-semibold">{statusLabel(config.status)}</p>
              </div>
              <div className="rounded-md border border-border bg-sky-50 p-3">
                <p className="text-sm text-muted-foreground">Auth mode</p>
                <p className="mt-1 text-base font-semibold">{statusLabel(config.authMode)}</p>
              </div>
              <div className="rounded-md border border-border bg-amber-50 p-3">
                <p className="text-sm text-muted-foreground">Last tested</p>
                <p className="mt-1 text-base font-semibold">
                  {config.lastTestedAt ? new Date(config.lastTestedAt).toLocaleString() : "Never"}
                </p>
              </div>
            </div>

            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              <div className="flex items-start gap-3 rounded-md border border-border p-3">
                <Cable className="mt-0.5 h-4 w-4 text-primary" />
                <div>
                  <p className="text-sm font-medium">Base URL</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {readinessLabel(config.baseUrlConfigured)}
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3 rounded-md border border-border p-3">
                <KeyRound className="mt-0.5 h-4 w-4 text-primary" />
                <div>
                  <p className="text-sm font-medium">Credentials</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {readinessLabel(config.credentialsConfigured)}
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3 rounded-md border border-border p-3">
                <LockKeyhole className="mt-0.5 h-4 w-4 text-primary" />
                <div>
                  <p className="text-sm font-medium">Secret display</p>
                  <p className="mt-1 text-sm text-muted-foreground">Blocked</p>
                </div>
              </div>
            </div>

            <p className="mt-5 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm leading-6 text-amber-950">
              V1.3 can read sandbox readiness from local environment variables, but the UI never
              accepts or displays token values. CFO data access still goes through approved
              connector actions only.
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

          <form className="border-t border-border bg-slate-950 p-5 text-white lg:border-l lg:border-t-0" onSubmit={onSave}>
            <div className="flex items-center gap-2">
              <DatabaseZap className="h-4 w-4 text-sky-300" />
              <p className="text-sm font-medium">Local connector settings</p>
            </div>

            <div className="mt-4 space-y-3">
              <div>
                <label className="text-sm text-slate-300" htmlFor="netsuite-account-id">
                  Account ID
                </label>
                <input
                  id="netsuite-account-id"
                  className="mt-1 h-10 w-full rounded-md border border-slate-700 bg-slate-900 px-3 text-sm text-white outline-none focus:border-sky-300"
                  maxLength={64}
                  minLength={3}
                  onChange={(event) => setAccountId(event.target.value)}
                  value={accountId}
                />
              </div>

              <div>
                <label className="text-sm text-slate-300" htmlFor="netsuite-environment">
                  Environment
                </label>
                <select
                  id="netsuite-environment"
                  className="mt-1 h-10 w-full rounded-md border border-slate-700 bg-slate-900 px-3 text-sm text-white outline-none focus:border-sky-300"
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
                <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
                  <p className="text-sm text-slate-300">Runtime mode</p>
                  <p className="mt-1 font-medium">{config.mode}</p>
                </div>
                <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
                  <p className="text-sm text-slate-300">Credential storage</p>
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

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-medium text-muted-foreground">Generic connector foundation</p>
          <h2 className="mt-1 text-xl font-semibold">REST API integration gateway</h2>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge className="border-amber-300 bg-amber-50 text-amber-950">
            <Globe2 className="mr-1 h-3.5 w-3.5" />
            System agnostic
          </Badge>
          <Badge className="border-slate-300 bg-white text-slate-700">
            <Workflow className="mr-1 h-3.5 w-3.5" />
            Approved schemas only
          </Badge>
        </div>
      </div>

      <Card className="overflow-hidden border-slate-200 bg-white p-0 shadow-sm">
        <div className="grid lg:grid-cols-[minmax(0,1fr)_420px]">
          <div className="p-5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Network className="h-4 w-4 text-amber-600" />
                REST object tray
              </CardTitle>
            </CardHeader>

            <div className="grid gap-3 md:grid-cols-3">
              {restApiObjects.map((object) => (
                <div
                  className="rounded-md border border-slate-200 bg-gradient-to-br from-white to-amber-50/60 p-4"
                  key={object.objectId}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-950">{object.label}</p>
                      <p className="mt-1 text-xs leading-5 text-muted-foreground">
                        {object.description}
                      </p>
                    </div>
                    <Badge className="border-amber-200 bg-white text-amber-900">
                      {object.fields.length} fields
                    </Badge>
                  </div>
                  <div className="mt-4 space-y-2">
                    {object.fields.slice(0, 4).map((field) => (
                      <div
                        className="flex items-center justify-between rounded-md border border-slate-200 bg-white px-3 py-2 text-xs"
                        key={field.name}
                      >
                        <span className="font-medium text-slate-800">{field.label}</span>
                        <span className="text-muted-foreground">{field.type}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              <div className="rounded-md border border-border bg-slate-50 p-3">
                <p className="text-sm text-muted-foreground">Status</p>
                <p className="mt-1 text-base font-semibold">
                  {statusLabel(restApiConfig.status)}
                </p>
              </div>
              <div className="rounded-md border border-border bg-amber-50 p-3">
                <p className="text-sm text-muted-foreground">Actions</p>
                <p className="mt-1 text-base font-semibold">
                  {restApiConfig.approvedActions.length} approved
                </p>
              </div>
              <div className="rounded-md border border-border bg-emerald-50 p-3">
                <p className="text-sm text-muted-foreground">Runtime safety</p>
                <p className="mt-1 text-base font-semibold">No outbound calls</p>
              </div>
            </div>

            <p className="mt-5 rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-sm leading-6 text-sky-950">
              REST support starts as a governed mock connector for object discovery, mapping, and
              flow design. It does not execute arbitrary URLs, headers, tokens, or payloads.
            </p>

            {restApiError ? (
              <p className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-950">
                {restApiError}
              </p>
            ) : null}

            {restApiTestResult ? (
              <p className="mt-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-950">
                {restApiTestResult.message}
              </p>
            ) : null}
          </div>

          <form
            className="border-t border-border bg-slate-950 p-5 text-white lg:border-l lg:border-t-0"
            onSubmit={onSaveRestApi}
          >
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-amber-300" />
              <p className="text-sm font-medium">REST connector profile</p>
            </div>

            <div className="mt-4 space-y-3">
              <div>
                <label className="text-sm text-slate-300" htmlFor="rest-api-display-name">
                  Display name
                </label>
                <input
                  id="rest-api-display-name"
                  className="mt-1 h-10 w-full rounded-md border border-slate-700 bg-slate-900 px-3 text-sm text-white outline-none focus:border-amber-300"
                  maxLength={80}
                  minLength={3}
                  onChange={(event) => setRestApiDisplayName(event.target.value)}
                  value={restApiDisplayName}
                />
              </div>

              <div>
                <label className="text-sm text-slate-300" htmlFor="rest-api-base-url">
                  Base URL placeholder
                </label>
                <input
                  id="rest-api-base-url"
                  className="mt-1 h-10 w-full rounded-md border border-slate-700 bg-slate-900 px-3 text-sm text-white outline-none focus:border-amber-300"
                  maxLength={120}
                  minLength={3}
                  onChange={(event) => setRestApiBaseUrl(event.target.value)}
                  value={restApiBaseUrl}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
                  <p className="text-sm text-slate-300">Auth mode</p>
                  <p className="mt-1 font-medium">placeholder</p>
                </div>
                <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
                  <p className="text-sm text-slate-300">Secret storage</p>
                  <p className="mt-1 font-medium">Disabled</p>
                </div>
              </div>
            </div>

            <div className="mt-5 flex flex-col gap-3 sm:flex-row">
              <Button disabled={isSavingRestApi} type="submit">
                <Save className="h-4 w-4" />
                {isSavingRestApi ? "Saving" : "Save profile"}
              </Button>
              <Button
                disabled={isTestingRestApi}
                onClick={onTestRestApi}
                type="button"
                variant="secondary"
              >
                <CheckCircle2 className="h-4 w-4" />
                {isTestingRestApi ? "Testing" : "Test REST"}
              </Button>
            </div>
          </form>
        </div>
      </Card>
    </section>
  );
}
