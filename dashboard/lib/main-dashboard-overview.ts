export type MainDashboardOverview = {
  source: "main-dashboard";
  stats: {
    totalCases: number;
    activeCases: number;
    pendingAnalysis: number;
    pipelineValue: number;
  };
  recentCases: unknown[];
  pipelineStages: Array<{
    name: string;
    count: number;
    value: number;
  }>;
  recentActivity: unknown[];
};

const DEFAULT_PIPELINE_STAGES = [
  "New",
  "Qualification",
  "Analysis",
  "Proposal",
  "Negotiation",
  "Closed Won",
  "Closed Lost",
];

export function normalizeMainDashboardOverview(
  payload: Record<string, unknown>
): MainDashboardOverview {
  const rawStats =
    typeof payload.stats === "object" && payload.stats
      ? (payload.stats as Record<string, unknown>)
      : {};
  const pipelineStages = Array.isArray(payload.pipelineStages)
    ? payload.pipelineStages
    : DEFAULT_PIPELINE_STAGES.map((name) => ({
        name,
        count: 0,
        value: 0,
      }));

  return {
    source: "main-dashboard",
    stats: {
      totalCases: toNumber(rawStats.totalCases),
      activeCases: toNumber(rawStats.activeCases),
      pendingAnalysis: toNumber(rawStats.pendingAnalysis),
      pipelineValue: toNumber(rawStats.pipelineValue),
    },
    recentCases: Array.isArray(payload.recentCases) ? payload.recentCases : [],
    pipelineStages: pipelineStages.map((stage) => normalizeStage(stage)),
    recentActivity: Array.isArray(payload.recentActivity)
      ? payload.recentActivity
      : [],
  };
}

function normalizeStage(stage: unknown) {
  if (typeof stage !== "object" || !stage) {
    return {
      name: "Unknown",
      count: 0,
      value: 0,
    };
  }

  const item = stage as Record<string, unknown>;

  return {
    name: typeof item.name === "string" ? item.name : "Unknown",
    count: toNumber(item.count),
    value: toNumber(item.value),
  };
}

function toNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}
