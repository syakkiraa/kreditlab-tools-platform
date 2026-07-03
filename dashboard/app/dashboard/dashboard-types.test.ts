import assert from "node:assert/strict";
import test from "node:test";

import { formatCompactCurrency } from "./dashboard-types.ts";

test("formatCompactCurrency formats large MYR values for KPI display", () => {
  assert.equal(formatCompactCurrency(1213600000), "MYR 1213.6M");
});

test("formatCompactCurrency formats small values without compact suffix", () => {
  assert.equal(formatCompactCurrency(500), "MYR 500");
});
