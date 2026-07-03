const SEVEN_DAYS_IN_MS = 7 * 24 * 60 * 60 * 1000;

export type ConsultantReminderCaseRecord = {
  id: string;
  created_at: string | null;
  consultant_reminder_sent_at: string | null;
};

export type ConsultantReminderSchedule = {
  createdBeforeUtcIso: string;
};

export function buildConsultantReminderSchedule(
  now: Date
): ConsultantReminderSchedule {
  return {
    createdBeforeUtcIso: new Date(
      now.getTime() - SEVEN_DAYS_IN_MS
    ).toISOString(),
  };
}

export function filterEligibleConsultantReminderCases<
  TCase extends ConsultantReminderCaseRecord,
>(cases: TCase[], schedule: ConsultantReminderSchedule): TCase[] {
  const cutoffTime = Date.parse(schedule.createdBeforeUtcIso);

  return cases.filter((item) => {
    if (wasConsultantReminderSent(item.consultant_reminder_sent_at)) {
      return false;
    }

    if (!item.created_at) {
      return false;
    }

    return Date.parse(item.created_at) <= cutoffTime;
  });
}

export function wasConsultantReminderSent(sentAt: string | null): boolean {
  return Boolean(sentAt);
}
