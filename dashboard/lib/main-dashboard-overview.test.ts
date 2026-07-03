import assert from "node:assert/strict";
import test from "node:test";

import { normalizeMainDashboardOverview } from "./main-dashboard-overview.ts";

test("normalizeMainDashboardOverview preserves valid stats and fills missing sections", () => {
  const overview = normalizeMainDashboardOverview({
    stats: {
      totalCases: 3,
      activeCases: 3,
      pendingAnalysis: 3,
      pipelineValue: 1213600000,
    },
    recentCases: [],
  });

  assert.equal(overview.source, "main-dashboard");
  assert.equal(overview.stats.totalCases, 3);
  assert.equal(overview.stats.pipelineValue, 1213600000);
  assert.equal(overview.pipelineStages.length, 7);
  assert.deepEqual(overview.recentActivity, []);
});

test("normalizeMainDashboardOverview falls back to zero values for invalid stats", () => {
  const overview = normalizeMainDashboardOverview({});

  assert.equal(overview.stats.totalCases, 0);
  assert.equal(overview.stats.activeCases, 0);
  assert.equal(overview.stats.pendingAnalysis, 0);
  assert.equal(overview.stats.pipelineValue, 0);
});
