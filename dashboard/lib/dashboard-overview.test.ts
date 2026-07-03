import assert from "node:assert/strict";
import test from "node:test";

import { buildDashboardOverview } from "./dashboard-overview.ts";

test("buildDashboardOverview summarizes local case KPIs and preserves recency", () => {
  const overview = buildDashboardOverview([
    {
      id: "case-1",
      case_code: "CASE-1",
      company_name: "AAA Enterprise",
      client_name: "Arthur",
      industry: "Finance",
      status: "New",
      requested_amount: 190000,
      created_at: "2026-06-16T09:04:00.000Z",
      updated_at: "2026-06-16T09:04:00.000Z",
    },
    {
      id: "case-2",
      case_code: "CASE-2",
      company_name: "BBB Enterprise",
      client_name: "Bella",
      industry: "Technology",
      status: "Approved",
      requested_amount: 250000,
      created_at: "2026-06-15T09:04:00.000Z",
      updated_at: "2026-06-15T09:04:00.000Z",
    },
    {
      id: "case-3",
      case_code: "CASE-3",
      company_name: "CCC Enterprise",
      client_name: "Chris",
      industry: "Healthcare",
      status: "Under Review",
      loan_amount: 1200000,
      created_at: "2026-06-14T09:04:00.000Z",
      updated_at: "2026-06-17T09:04:00.000Z",
    },
  ]);

  assert.equal(overview.stats.totalCases, 3);
  assert.equal(overview.stats.activeCases, 2);
  assert.equal(overview.stats.pendingAnalysis, 2);
  assert.equal(overview.stats.pipelineValue, 1640000);
  assert.deepEqual(
    overview.recentCases.map((item) => item.id),
    ["case-3", "case-1", "case-2"]
  );
  assert.equal(overview.pipelineStages[0]?.name, "New");
  assert.equal(overview.pipelineStages[0]?.count, 1);
});

test("buildDashboardOverview defaults missing stage values to zero counts", () => {
  const overview = buildDashboardOverview([]);

  assert.equal(overview.stats.totalCases, 0);
  assert.equal(overview.pipelineStages.length, 7);
  assert.ok(
    overview.pipelineStages.every((stage) => stage.count === 0 && stage.value === 0)
  );
});
