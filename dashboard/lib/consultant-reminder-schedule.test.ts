import test from "node:test";
import assert from "node:assert/strict";

import {
  buildConsultantReminderSchedule,
  filterEligibleConsultantReminderCases,
  wasConsultantReminderSent,
} from "./consultant-reminder-schedule.ts";

test("buildConsultantReminderSchedule returns a seven-day cutoff", () => {
  const schedule = buildConsultantReminderSchedule(
    new Date("2026-06-29T12:00:00.000Z")
  );

  assert.equal(schedule.createdBeforeUtcIso, "2026-06-22T12:00:00.000Z");
});

test("filterEligibleConsultantReminderCases keeps only cases older than seven days", () => {
  const cases = [
    {
      id: "older-case",
      created_at: "2026-06-21T11:59:59.000Z",
      consultant_reminder_sent_at: null,
    },
    {
      id: "fresh-case",
      created_at: "2026-06-23T12:00:01.000Z",
      consultant_reminder_sent_at: null,
    },
  ];

  const eligible = filterEligibleConsultantReminderCases(
    cases,
    buildConsultantReminderSchedule(new Date("2026-06-29T12:00:00.000Z"))
  );

  assert.deepEqual(
    eligible.map((item) => item.id),
    ["older-case"]
  );
});

test("filterEligibleConsultantReminderCases excludes cases already reminded", () => {
  const cases = [
    {
      id: "already-reminded",
      created_at: "2026-06-20T12:00:00.000Z",
      consultant_reminder_sent_at: "2026-06-28T08:00:00.000Z",
    },
    {
      id: "pending-reminder",
      created_at: "2026-06-20T12:00:00.000Z",
      consultant_reminder_sent_at: null,
    },
  ];

  const eligible = filterEligibleConsultantReminderCases(
    cases,
    buildConsultantReminderSchedule(new Date("2026-06-29T12:00:00.000Z"))
  );

  assert.deepEqual(
    eligible.map((item) => item.id),
    ["pending-reminder"]
  );
});

test("wasConsultantReminderSent reports false when the timestamp is missing", () => {
  assert.equal(wasConsultantReminderSent(null), false);
});
