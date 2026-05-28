import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Banknote,
  BriefcaseBusiness,
  Building2,
  ChartNoAxesColumn,
  RefreshCcw,
  TrendingUp
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import {
  type ApiResult,
  getDashboardSummary,
  getOverdueProjects,
  getPlVsBudget,
  getRunningProjects,
  getSubsidiaryDrilldown,
  getYoyComparison
} from "@/lib/api";
import { AiQueryConsole } from "@/components/ai-query-console";

export const dynamic = "force-dynamic";

function money(amount: number, currency: string) {
  return new Intl.NumberFormat("en-US", {
    currency,
    maximumFractionDigits: 0,
    style: "currency"
  }).format(amount);
}

function percent(value: number) {
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
}

function SectionHeader({
  eyebrow,
  result,
  title
}: {
  eyebrow: string;
  result: ApiResult<unknown>;
  title: string;
}) {
  return (
    <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <p className="text-sm font-medium text-muted-foreground">{eyebrow}</p>
        <h2 className="mt-1 text-xl font-semibold">{title}</h2>
      </div>
      {result.isFallback ? (
        <Badge className="border-amber-300 bg-amber-50 text-amber-900">
          <AlertTriangle className="mr-1 h-3.5 w-3.5" />
          Mock fallback
        </Badge>
      ) : (
        <Badge className="border-emerald-300 bg-emerald-50 text-emerald-900">Live mock API</Badge>
      )}
    </div>
  );
}

function FallbackNotice({ result }: { result: ApiResult<unknown> }) {
  if (!result.isFallback) {
    return null;
  }

  return (
    <p className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
      API data is unavailable for this section, so the dashboard is showing safe mock data.
      {result.error ? ` ${result.error}.` : ""}
    </p>
  );
}

function statusLabel(status: string) {
  return status.replaceAll("_", " ");
}

export default async function Home() {
  const [summaryResult, plResult, yoyResult, subsidiaryResult, projectsResult, overdueResult] =
    await Promise.all([
      getDashboardSummary(),
      getPlVsBudget(),
      getYoyComparison(),
      getSubsidiaryDrilldown(),
      getRunningProjects(),
      getOverdueProjects()
    ]);
  const summary = summaryResult.data;
  const plVsBudget = plResult.data;
  const yoyComparison = yoyResult.data;
  const subsidiary = subsidiaryResult.data;
  const projects = projectsResult.data;
  const overdue = overdueResult.data;

  return (
    <main className="min-h-screen">
      <header className="border-b border-border bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">NetSuite CFO Intelligence</p>
            <h1 className="mt-1 text-2xl font-semibold tracking-normal">Executive finance cockpit</h1>
          </div>
          <Button variant="secondary" title="Refresh mock data">
            <RefreshCcw className="h-4 w-4" />
            Refresh
          </Button>
        </div>
      </header>

      <AiQueryConsole />

      <section className="mx-auto grid max-w-7xl gap-5 px-6 py-8 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Cash position</CardTitle>
          </CardHeader>
          <div className="flex items-end justify-between gap-4">
            <p className="text-3xl font-semibold">
              {money(summary.cashPosition.amount, summary.cashPosition.currency)}
            </p>
            <Banknote className="h-7 w-7 text-primary" />
          </div>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Open receivables</CardTitle>
          </CardHeader>
          <p className="text-3xl font-semibold">
            {money(summary.openReceivables.amount, summary.openReceivables.currency)}
          </p>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Monthly revenue</CardTitle>
          </CardHeader>
          <p className="text-3xl font-semibold">
            {money(summary.monthlyRevenue.amount, summary.monthlyRevenue.currency)}
          </p>
        </Card>
      </section>

      <section className="mx-auto max-w-7xl px-6 pb-10">
        <FallbackNotice result={summaryResult} />
        <div className="grid gap-4 lg:grid-cols-3">
          {summary.kpis.map((kpi) => (
            <Card key={kpi.label}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">{kpi.label}</p>
                  <p className="mt-2 text-2xl font-semibold">{kpi.value}</p>
                </div>
                {kpi.trend === "down" ? (
                  <ArrowDownRight className="h-5 w-5 text-emerald-700" />
                ) : kpi.trend === "up" ? (
                  <ArrowUpRight className="h-5 w-5 text-emerald-700" />
                ) : (
                  <Activity className="h-5 w-5 text-accent" />
                )}
              </div>
              <p className="mt-4 text-sm leading-6 text-muted-foreground">{kpi.narrative}</p>
            </Card>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 pb-10">
        <SectionHeader eyebrow="P/L vs budget" result={plResult} title="Actuals against plan" />
        <FallbackNotice result={plResult} />
        <div className="grid gap-4 lg:grid-cols-3">
          {plVsBudget.lines.map((line) => (
            <Card key={`${line.subsidiaryId}-${line.line}`}>
              <CardHeader>
                <CardTitle>{line.line}</CardTitle>
              </CardHeader>
              <div className="space-y-3">
                <div className="flex items-end justify-between gap-4">
                  <p className="text-2xl font-semibold">{money(line.actual, line.currency)}</p>
                  <Badge>{percent(line.variancePct)}</Badge>
                </div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-muted-foreground">Budget</p>
                    <p className="font-medium">{money(line.budget, line.currency)}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Variance</p>
                    <p className="font-medium">{money(line.variance, line.currency)}</p>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 pb-10">
        <SectionHeader
          eyebrow="YoY comparison"
          result={yoyResult}
          title={`${yoyComparison.currentYear} vs ${yoyComparison.priorYear}`}
        />
        <FallbackNotice result={yoyResult} />
        <div className="grid gap-4 lg:grid-cols-2">
          {yoyComparison.lines.map((line) => (
            <Card key={`${line.subsidiaryId}-${line.metric}`}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">{line.metric}</p>
                  <p className="mt-2 text-2xl font-semibold">
                    {money(line.currentValue, line.currency)}
                  </p>
                </div>
                <TrendingUp className="h-5 w-5 text-emerald-700" />
              </div>
              <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
                <div>
                  <p className="text-muted-foreground">Prior</p>
                  <p className="font-medium">{money(line.priorValue, line.currency)}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Change</p>
                  <p className="font-medium">{money(line.change, line.currency)}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Rate</p>
                  <p className="font-medium">{percent(line.changePct)}</p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 pb-10">
        <SectionHeader
          eyebrow="Subsidiary drilldown"
          result={subsidiaryResult}
          title={`${subsidiary.subsidiaryId} operating view`}
        />
        <FallbackNotice result={subsidiaryResult} />
        <div className="grid gap-4 lg:grid-cols-3">
          {subsidiary.lines.map((line) => (
            <Card key={`${line.subsidiaryId}-${line.department}`}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">{line.subsidiaryName}</p>
                  <p className="mt-2 text-xl font-semibold">{line.department}</p>
                </div>
                <Building2 className="h-5 w-5 text-primary" />
              </div>
              <div className="mt-4 space-y-2 text-sm">
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">Revenue</span>
                  <span className="font-medium">{money(line.revenue, line.currency)}</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">Expenses</span>
                  <span className="font-medium">{money(line.expenses, line.currency)}</span>
                </div>
                <div className="flex justify-between gap-4 border-t border-border pt-2">
                  <span className="text-muted-foreground">Operating income</span>
                  <span className="font-semibold">{money(line.operatingIncome, line.currency)}</span>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 pb-10">
        <SectionHeader
          eyebrow="Running projects"
          result={projectsResult}
          title="Delivery financial exposure"
        />
        <FallbackNotice result={projectsResult} />
        <div className="grid gap-4 lg:grid-cols-3">
          {projects.projects.map((project) => (
            <Card key={project.projectId}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">{project.customer}</p>
                  <p className="mt-2 text-lg font-semibold">{project.projectName}</p>
                </div>
                <BriefcaseBusiness className="h-5 w-5 text-primary" />
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <Badge>{statusLabel(project.status)}</Badge>
                <Badge>{project.accountManager}</Badge>
              </div>
              <div className="mt-4 space-y-2 text-sm">
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">Budget</span>
                  <span className="font-medium">{money(project.budget, project.currency)}</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">Actual cost</span>
                  <span className="font-medium">{money(project.actualCost, project.currency)}</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">Forecast</span>
                  <span className="font-medium">{money(project.forecastCost, project.currency)}</span>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 pb-12">
        <SectionHeader
          eyebrow="Overdue projects"
          result={overdueResult}
          title="Aging by account manager"
        />
        <FallbackNotice result={overdueResult} />
        <div className="grid gap-4 lg:grid-cols-2">
          {overdue.managers.map((manager) => (
            <Card key={manager.accountManager}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Account manager</p>
                  <p className="mt-2 text-2xl font-semibold">{manager.accountManager}</p>
                </div>
                <ChartNoAxesColumn className="h-5 w-5 text-accent" />
              </div>
              <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
                <div>
                  <p className="text-muted-foreground">Projects</p>
                  <p className="font-medium">{manager.overdueProjectCount}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Exposure</p>
                  <p className="font-medium">
                    {money(manager.totalOverdueAmount, manager.currency)}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground">Max days</p>
                  <p className="font-medium">{manager.maxDaysOverdue}</p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </section>
    </main>
  );
}
