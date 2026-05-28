import { Activity, ArrowDownRight, ArrowUpRight, Banknote, RefreshCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { getDashboardSummary } from "@/lib/api";

export const dynamic = "force-dynamic";

function money(amount: number, currency: string) {
  return new Intl.NumberFormat("en-US", {
    currency,
    maximumFractionDigits: 0,
    style: "currency"
  }).format(amount);
}

export default async function Home() {
  const summary = await getDashboardSummary();

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
    </main>
  );
}
