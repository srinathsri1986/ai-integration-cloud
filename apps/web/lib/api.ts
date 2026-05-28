import type { CfoDashboardSummary } from "@netsuite-cfo/shared";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const fallbackDashboardSummary: CfoDashboardSummary = {
  generatedAt: new Date(0).toISOString(),
  mode: "mock",
  cashPosition: {
    amount: 4_250_000,
    currency: "USD"
  },
  openReceivables: {
    amount: 1_175_000,
    currency: "USD"
  },
  monthlyRevenue: {
    amount: 2_980_000,
    currency: "USD"
  },
  kpis: [
    {
      label: "Cash runway",
      value: "14.2 months",
      trend: "up",
      narrative: "Mock operating cash trend improved against the prior period."
    },
    {
      label: "DSO",
      value: 42,
      trend: "down",
      narrative: "Mock receivables collection velocity improved by 3 days."
    },
    {
      label: "Gross margin",
      value: "61.4%",
      trend: "flat",
      narrative: "Mock margin stayed within the expected operating band."
    }
  ]
};

export async function getDashboardSummary(): Promise<CfoDashboardSummary> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/cfo/dashboard-summary`, {
      cache: "no-store"
    });

    if (!response.ok) {
      return fallbackDashboardSummary;
    }

    const body = await response.json();
    return {
      generatedAt: body.generated_at,
      mode: body.mode,
      cashPosition: body.cash_position,
      openReceivables: body.open_receivables,
      monthlyRevenue: body.monthly_revenue,
      kpis: body.kpis
    };
  } catch {
    return fallbackDashboardSummary;
  }
}
