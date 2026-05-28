import assert from "node:assert/strict";
import test from "node:test";

import { yoyComparisonInputSchema } from "../src/schemas/cfo.js";
import { approvedNetSuiteQueryTemplateIdSchema } from "../src/schemas/netsuite.js";

test("allows approved NetSuite query templates", () => {
  assert.equal(
    approvedNetSuiteQueryTemplateIdSchema.safeParse("cash_position_summary").success,
    true
  );
});

test("rejects arbitrary SQL-shaped input", () => {
  assert.equal(
    approvedNetSuiteQueryTemplateIdSchema.safeParse("select * from transaction").success,
    false
  );
});

test("rejects invalid YoY year order", () => {
  assert.equal(
    yoyComparisonInputSchema.safeParse({ currentYear: 2025, priorYear: 2026 }).success,
    false
  );
});
