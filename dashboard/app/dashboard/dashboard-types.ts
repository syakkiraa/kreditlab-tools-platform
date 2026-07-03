import type { DashboardCaseRecord, DashboardOverview } from "@/lib/dashboard-overview";
import type { MainDashboardOverview } from "@/lib/main-dashboard-overview";

export type DashboardRecentCase = DashboardCaseRecord;
export type DashboardPipelineStage = DashboardOverview["pipelineStages"][number];
export type DashboardActivityItem = DashboardOverview["recentActivity"][number];
export type DashboardRemoteOverview = MainDashboardOverview;

const ACTIVITY_PROGRESS_BY_STATUS: Record<string, number> = {
  New: 22,
  "In Progress": 48,
  "Under Review": 72,
  Approved: 100,
  Rejected: 100,
  Qualification: 35,
  Analysis: 62,
  Proposal: 78,
  Negotiation: 88,
  "Closed Won": 100,
  "Closed Lost": 100,
};

export function formatCompactCurrency(value: number) {
  if (value >= 1000000) {
    return `MYR ${(value / 1000000).toFixed(1)}M`;
  }

  if (value >= 1000) {
    return `MYR ${(value / 1000).toFixed(0)}K`;
  }

  return `MYR ${Math.round(value)}`;
}

export function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-MY", {
    style: "currency",
    currency: "MYR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "-";
  }

  return new Date(value).toLocaleString("en-MY", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function getStatusBadgeClass(status: string | null) {
  switch (status) {
    case "Approved":
    case "Closed Won":
      return "bg-green-100 text-green-700";
    case "Rejected":
    case "Closed Lost":
      return "bg-red-100 text-red-700";
    case "In Progress":
      return "bg-yellow-100 text-yellow-700";
    case "Under Review":
    case "Analysis":
      return "bg-purple-100 text-purple-700";
    case "Qualification":
    case "Proposal":
    case "Negotiation":
      return "bg-sky-100 text-sky-700";
    default:
      return "bg-cyan-100 text-cyan-700";
  }
}

export function getActivityProgress(status: string | null) {
  if (!status) {
    return 18;
  }

  return ACTIVITY_PROGRESS_BY_STATUS[status] ?? 40;
}

export function getActivityLabel(status: string | null) {
  if (!status) {
    return "Case Progress";
  }

  return `${status} Progress`;
}
