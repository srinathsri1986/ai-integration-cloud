import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Banknote,
  BriefcaseBusiness,
  Building2,
  ChartNoAxesColumn,
  TrendingUp
} from "lucide-react";
import type { ReactNode } from "react";

import { PlatformShell } from "@/components/platform-shell";
import { Badge } from "@/components/ui/badge";
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

function statusLabel(status: string) {
  return status.replaceAll("_", " ");
}

function FallbackNotice({ result }: { result: ApiResult<unknown> }) {
  if (!result.isFallback) {
    return null;
  }

  return (
    <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
      Safe mock data is being shown for this section. {result.error ? `${result.error}.` : ""}
    </p>
  );
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
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <p className="text-sm font-medium text-muted-foreground">{eyebrow}</p>
        <h2 className="mt-1 text-xl font-semibold text-slate-950">{title}</h2>
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

export default async function CfoPage() {
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
    <PlatformShell
      active="/cfo"
      subtitle="Executive finance intelligence from approved CFO services, governed model calls, and safe NetSuite access patterns."
      title="CFO Executive Dashboard"
    >
      <div className="space-y-8">
        <section className="overflow-hidden rounded-2xl border border-white/80 bg-slate-950 text-white shadow-xl shadow-slate-300/50">
          <div className="grid gap-6 p-6 lg:grid-cols-[1.2fr_0.8fr] lg:p-8">
            <div>
              <Badge className="border-white/15 bg-white/10 text-white">Finance control tower</Badge>
              <h2 className="mt-5 max-w-3xl text-3xl font-semibold leading-tight tracking-normal">
                Board-ready CFO view with governed AI insight.
              </h2>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-300">
                P/L variance, cash position, project exposure, subsidiary drilldowns, and
                narrative-ready metrics stay grounded in approved service data.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
              <HeroMetric
                icon={<Banknote className="h-5 w-5" />}
                label="Cash position"
                value={money(summary.cashPosition.amount, summary.cashPosition.currency)}
              />
              <HeroMetric
                label="Open receivables"
                value={money(summary.openReceivables.amount, summary.openReceivables.currency)}
              />
              <HeroMetric
                label="Monthly revenue"
                value={money(summary.monthlyRevenue.amount, summary.monthlyRevenue.currency)}
              />
            </div>
          </div>
        </section>

        <FallbackNotice result={summaryResult} />

        <section className="grid gap-4 lg:grid-cols-3">
          {summary.kpis.map((kpi) => (
            <Card className="bg-white/90" key={kpi.label}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">{kpi.label}</p>
                  <p className="mt-2 text-2xl font-semibold text-slate-950">{kpi.value}</p>
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
        </section>

        <section className="space-y-4">
          <SectionHeader eyebrow="P/L vs budget" result={plResult} title="Actuals against plan" />
          <FallbackNotice result={plResult} />
          <div className="grid gap-4 lg:grid-cols-2">
            {plVsBudget.lines.map((line) => (
              <Card className="bg-white/90" key={`${line.subsidiaryId}-${line.line}`}>
                <CardHeader>
                  <CardTitle>{line.line}</CardTitle>
                </CardHeader>
                <div className="flex items-end justify-between gap-4">
                  <p className="text-2xl font-semibold text-slate-950">
                    {money(line.actual, line.currency)}
                  </p>
                  <Badge className="border-emerald-200 bg-emerald-50 text-emerald-900">
                    {percent(line.variancePct)}
                  </Badge>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                  <Metric label="Budget" value={money(line.budget, line.currency)} />
                  <Metric label="Variance" value={money(line.variance, line.currency)} />
                </div>
              </Card>
            ))}
          </div>
        </section>

        <section className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
          <div className="space-y-4">
            <SectionHeader
              eyebrow="YoY comparison"
              result={yoyResult}
              title={`${yoyComparison.currentYear} vs ${yoyComparison.priorYear}`}
            />
            <FallbackNotice result={yoyResult} />
            {yoyComparison.lines.map((line) => (
              <Card className="bg-white/90" key={`${line.subsidiaryId}-${line.metric}`}>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">{line.metric}</p>
                    <p className="mt-2 text-xl font-semibold text-slate-950">
                      {money(line.currentValue, line.currency)}
                    </p>
                  </div>
                  <TrendingUp className="h-5 w-5 text-emerald-700" />
                </div>
                <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
                  <Metric label="Prior" value={money(line.priorValue, line.currency)} />
                  <Metric label="Change" value={money(line.change, line.currency)} />
                  <Metric label="Rate" value={percent(line.changePct)} />
                </div>
              </Card>
            ))}
          </div>

          <div className="space-y-4">
            <SectionHeader
              eyebrow="Subsidiary drilldown"
              result={subsidiaryResult}
              title={`${subsidiary.subsidiaryId} operating view`}
            />
            <FallbackNotice result={subsidiaryResult} />
            <div className="grid gap-4 md:grid-cols-2">
              {subsidiary.lines.map((line) => (
                <Card className="bg-white/90" key={`${line.subsidiaryId}-${line.department}`}>
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">
                        {line.subsidiaryName}
                      </p>
                      <p className="mt-2 text-lg font-semibold text-slate-950">{line.department}</p>
                    </div>
                    <Building2 className="h-5 w-5 text-primary" />
                  </div>
                  <div className="mt-4 space-y-2 text-sm">
                    <Row label="Revenue" value={money(line.revenue, line.currency)} />
                    <Row label="Expenses" value={money(line.expenses, line.currency)} />
                    <Row
                      important
                      label="Operating income"
                      value={money(line.operatingIncome, line.currency)}
                    />
                  </div>
                </Card>
              ))}
            </div>
          </div>
        </section>

        <section className="space-y-4">
          <SectionHeader
            eyebrow="Project exposure"
            result={projectsResult}
            title="Running and overdue projects"
          />
          <FallbackNotice result={projectsResult} />
          <div className="grid gap-4 xl:grid-cols-[1fr_0.8fr]">
            <div className="grid gap-4 md:grid-cols-2">
              {projects.projects.map((project) => (
                <Card className="bg-white/90" key={project.projectId}>
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">{project.customer}</p>
                      <p className="mt-2 text-lg font-semibold text-slate-950">
                        {project.projectName}
                      </p>
                    </div>
                    <BriefcaseBusiness className="h-5 w-5 text-primary" />
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Badge>{statusLabel(project.status)}</Badge>
                    <Badge>{project.accountManager}</Badge>
                  </div>
                  <div className="mt-4 space-y-2 text-sm">
                    <Row label="Budget" value={money(project.budget, project.currency)} />
                    <Row label="Forecast" value={money(project.forecastCost, project.currency)} />
                  </div>
                </Card>
              ))}
            </div>

            <div className="space-y-4">
              <FallbackNotice result={overdueResult} />
              {overdue.managers.map((manager) => (
                <Card className="bg-white/90" key={manager.accountManager}>
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Account manager</p>
                      <p className="mt-2 text-xl font-semibold text-slate-950">
                        {manager.accountManager}
                      </p>
                    </div>
                    <ChartNoAxesColumn className="h-5 w-5 text-accent" />
                  </div>
                  <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
                    <Metric label="Projects" value={manager.overdueProjectCount} />
                    <Metric label="Exposure" value={money(manager.totalOverdueAmount, manager.currency)} />
                    <Metric label="Max days" value={manager.maxDaysOverdue} />
                  </div>
                </Card>
              ))}
            </div>
          </div>
        </section>
      </div>
    </PlatformShell>
  );
}

function HeroMetric({
  icon,
  label,
  value
}: {
  icon?: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-md border border-white/10 bg-white/10 p-4">
      <div className="flex items-center justify-between gap-3 text-slate-300">
        <p className="text-sm">{label}</p>
        {icon}
      </div>
      <p className="mt-2 text-xl font-semibold text-white">{value}</p>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div>
      <p className="text-muted-foreground">{label}</p>
      <p className="font-medium text-slate-950">{value}</p>
    </div>
  );
}

function Row({
  important,
  label,
  value
}: {
  important?: boolean;
  label: string;
  value: string;
}) {
  return (
    <div className={`flex justify-between gap-4 ${important ? "border-t border-border pt-2" : ""}`}>
      <span className="text-muted-foreground">{label}</span>
      <span className={important ? "font-semibold text-slate-950" : "font-medium text-slate-950"}>
        {value}
      </span>
    </div>
  );
}
