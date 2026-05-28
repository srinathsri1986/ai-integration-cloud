import assert from "node:assert/strict";
import test, { afterEach } from "node:test";

import {
  getCfoDashboardSummary,
  getOverdueProjectsByAccountManager,
  getPlVsBudget,
  getRunningProjects,
  getSubsidiaryDrilldown,
  getYoyComparison
} from "../src/tools/cfoTools.js";

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
});

function mockFetch(body: unknown, seenUrls: string[]) {
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    seenUrls.push(String(input));
    return {
      ok: true,
      json: async () => body
    } as Response;
  }) as typeof fetch;
}

function parseToolText(result: { content: Array<{ text: string }> }) {
  return JSON.parse(result.content[0].text);
}

test("get_cfo_dashboard_summary calls the approved dashboard endpoint", async () => {
  const seenUrls: string[] = [];
  mockFetch(
    {
      generated_at: "2026-05-28T00:00:00.000Z",
      mode: "mock",
      cash_position: { amount: 100, currency: "USD" },
      open_receivables: { amount: 50, currency: "USD" },
      monthly_revenue: { amount: 75, currency: "USD" },
      kpis: [{ label: "DSO", value: 42, trend: "down", narrative: "Mock trend." }]
    },
    seenUrls
  );

  const result = parseToolText(await getCfoDashboardSummary());

  assert.equal(seenUrls[0], "http://localhost:8000/api/v1/cfo/dashboard-summary");
  assert.equal(result.mode, "mock");
  assert.equal(result.cashPosition.currency, "USD");
});

test("get_pl_vs_budget calls the approved P/L endpoint", async () => {
  const seenUrls: string[] = [];
  mockFetch(
    {
      source: "mock",
      period: "2026-Q1",
      subsidiary_id: "NA",
      lines: [
        {
          period: "2026-Q1",
          subsidiary_id: "NA",
          line: "Revenue",
          actual: 100,
          budget: 90,
          variance: 10,
          variance_pct: 11.1,
          currency: "USD"
        }
      ]
    },
    seenUrls
  );

  const result = parseToolText(await getPlVsBudget({ period: "2026-Q1", subsidiaryId: "NA" }));

  assert.equal(
    seenUrls[0],
    "http://localhost:8000/api/v1/cfo/pl-vs-budget?period=2026-Q1&subsidiary_id=NA"
  );
  assert.equal(result.lines[0].variancePct, 11.1);
});

test("get_yoy_comparison calls the approved YoY endpoint", async () => {
  const seenUrls: string[] = [];
  mockFetch(
    {
      source: "mock",
      current_year: 2026,
      prior_year: 2025,
      subsidiary_id: "NA",
      lines: [
        {
          current_year: 2026,
          prior_year: 2025,
          subsidiary_id: "NA",
          metric: "Revenue",
          current_value: 100,
          prior_value: 90,
          change: 10,
          change_pct: 11.1,
          currency: "USD"
        }
      ]
    },
    seenUrls
  );

  const result = parseToolText(
    await getYoyComparison({ currentYear: 2026, priorYear: 2025, subsidiaryId: "NA" })
  );

  assert.equal(
    seenUrls[0],
    "http://localhost:8000/api/v1/cfo/yoy-comparison?current_year=2026&prior_year=2025&subsidiary_id=NA"
  );
  assert.equal(result.lines[0].currentYear, 2026);
});

test("get_subsidiary_drilldown calls the approved drilldown endpoint", async () => {
  const seenUrls: string[] = [];
  mockFetch(
    {
      source: "mock",
      period: "2026-Q1",
      subsidiary_id: "EMEA",
      lines: [
        {
          period: "2026-Q1",
          subsidiary_id: "EMEA",
          subsidiary_name: "EMEA",
          department: "Enterprise Services",
          revenue: 100,
          expenses: 40,
          operating_income: 60,
          currency: "USD"
        }
      ]
    },
    seenUrls
  );

  const result = parseToolText(
    await getSubsidiaryDrilldown({ period: "2026-Q1", subsidiaryId: "EMEA" })
  );

  assert.equal(
    seenUrls[0],
    "http://localhost:8000/api/v1/cfo/subsidiary-drilldown?period=2026-Q1&subsidiary_id=EMEA"
  );
  assert.equal(result.lines[0].operatingIncome, 60);
});

test("get_running_projects calls the approved running projects endpoint", async () => {
  const seenUrls: string[] = [];
  mockFetch(
    {
      source: "mock",
      account_manager: "Maya Rao",
      subsidiary_id: null,
      projects: [
        {
          project_id: "PRJ-1001",
          project_name: "Revenue Automation Rollout",
          customer: "Aster Manufacturing",
          account_manager: "Maya Rao",
          subsidiary_id: "NA",
          status: "on_track",
          budget: 100,
          actual_cost: 50,
          forecast_cost: 90,
          currency: "USD"
        }
      ]
    },
    seenUrls
  );

  const result = parseToolText(await getRunningProjects({ accountManager: "Maya Rao" }));

  assert.equal(
    seenUrls[0],
    "http://localhost:8000/api/v1/cfo/running-projects?account_manager=Maya+Rao"
  );
  assert.equal(result.projects[0].projectId, "PRJ-1001");
});

test("get_overdue_projects_by_account_manager calls the approved overdue endpoint", async () => {
  const seenUrls: string[] = [];
  mockFetch(
    {
      source: "mock",
      min_days_overdue: 20,
      managers: [
        {
          account_manager: "Maya Rao",
          overdue_project_count: 2,
          total_overdue_amount: 145000,
          max_days_overdue: 31,
          currency: "USD"
        }
      ]
    },
    seenUrls
  );

  const result = parseToolText(
    await getOverdueProjectsByAccountManager({ minDaysOverdue: 20 })
  );

  assert.equal(
    seenUrls[0],
    "http://localhost:8000/api/v1/cfo/overdue-projects/by-account-manager?min_days_overdue=20"
  );
  assert.equal(result.managers[0].overdueProjectCount, 2);
});

test("tool handlers reject invalid input before calling the backend", async () => {
  const seenUrls: string[] = [];
  mockFetch({}, seenUrls);

  await assert.rejects(() => getPlVsBudget({ period: "select * from transaction" }));
  await assert.rejects(() =>
    getYoyComparison({ currentYear: 2025, priorYear: 2026 })
  );

  assert.deepEqual(seenUrls, []);
});
