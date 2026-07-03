export type DashboardCaseRecord = {
  id: string;
  case_code: string | null;
  company_name: string | null;
  client_name: string | null;
  industry: string | null;
  status: string | null;
  requested_amount?: number | null;
  loan_amount?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type DashboardOverview = {
  stats: {
    totalCases: number;
    activeCases: number;
    pendingAnalysis: number;
    pipelineValue: number;
  };
  recentCases: DashboardCaseRecord[];
  recentActivity: DashboardCaseRecord[];
  pipelineStages: Array<{
    name: string;
    count: number;
    value: number;
  }>;
};

const PIPELINE_STAGES = [
  "New",
  "Qualification",
  "Analysis",
  "Proposal",
  "Negotiation",
  "Closed Won",
  "Closed Lost",
];

const PENDING_STATUSES = new Set(["New", "In Progress", "Under Review"]);
const CLOSED_STATUSES = new Set([
  "Rejected",
  "Closed Lost",
  "Closed Won",
  "Approved",
]);

export function buildDashboardOverview(
  cases: DashboardCaseRecord[]
): DashboardOverview {
  const sortedCases = [...cases].sort((left, right) =>
    getSortDate(right).localeCompare(getSortDate(left))
  );

  return {
    stats: {
      totalCases: cases.length,
      activeCases: cases.filter((item) => !CLOSED_STATUSES.has(item.status || ""))
        .length,
      pendingAnalysis: cases.filter((item) =>
        PENDING_STATUSES.has(item.status || "")
      ).length,
      pipelineValue: cases.reduce(
        (sum, item) => sum + getCaseAmount(item),
        0
      ),
    },
    recentCases: sortedCases.slice(0, 5),
    recentActivity: sortedCases.slice(0, 6),
    pipelineStages: PIPELINE_STAGES.map((stage) => {
      const stageCases = cases.filter((item) => item.status === stage);

      return {
        name: stage,
        count: stageCases.length,
        value: stageCases.reduce((sum, item) => sum + getCaseAmount(item), 0),
      };
    }),
  };
}

function getCaseAmount(item: DashboardCaseRecord) {
  return Number(item.requested_amount ?? item.loan_amount ?? 0);
}

function getSortDate(item: DashboardCaseRecord) {
  return item.updated_at || item.created_at || "";
}
