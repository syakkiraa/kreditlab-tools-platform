import {
  Activity,
  BriefcaseBusiness,
  ClipboardList,
  TrendingUp,
} from "lucide-react";

import { DashboardStatCard } from "./dashboard-stat-card";
import { DashboardRecentCasesCard } from "./dashboard-recent-cases-card";
import { DashboardPipelineCard } from "./dashboard-pipeline-card";
import {
  formatCompactCurrency,
  type DashboardRemoteOverview,
} from "../dashboard-types";

type DashboardMainSystemCardProps = {
  overview: DashboardRemoteOverview | null;
  loading: boolean;
  errorMsg: string;
};

export function DashboardMainSystemCard({
  overview,
  loading,
  errorMsg,
}: DashboardMainSystemCardProps) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h2 className="font-semibold text-slate-900">Main Dashboard System</h2>
          <p className="mt-1 text-sm text-slate-500">
            Live progress summary fetched from the reference dashboard.
          </p>
        </div>

        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
          {loading ? "Syncing..." : errorMsg ? "Unavailable" : "Connected"}
        </span>
      </div>

      {loading ? (
        <p className="text-sm text-slate-500">Loading main dashboard data...</p>
      ) : errorMsg ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errorMsg}
        </div>
      ) : !overview ? (
        <p className="text-sm text-slate-500">No synced data yet.</p>
      ) : (
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-4">
            <DashboardStatCard
              title="Main Total Cases"
              value={overview.stats.totalCases}
              sub="tracked in main system"
              icon={<BriefcaseBusiness className="h-5 w-5" />}
            />
            <DashboardStatCard
              title="Main Active Cases"
              value={overview.stats.activeCases}
              sub="currently active"
              icon={<Activity className="h-5 w-5" />}
            />
            <DashboardStatCard
              title="Main Pending Analysis"
              value={overview.stats.pendingAnalysis}
              sub="needs review"
              icon={<ClipboardList className="h-5 w-5" />}
            />
            <DashboardStatCard
              title="Main Pipeline Value"
              value={formatCompactCurrency(overview.stats.pipelineValue)}
              sub="total requested amount"
              icon={<TrendingUp className="h-5 w-5" />}
            />
          </div>

          <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
            <DashboardRecentCasesCard
              title="Main Recent Cases"
              subtitle="Preview of the latest synced cases from the main system"
              items={overview.recentCases as never[]}
              emptyMessage="No synced cases found."
            />
            <DashboardPipelineCard
              title="Main Pipeline Overview"
              subtitle="Stage distribution from the main dashboard system"
              stages={overview.pipelineStages}
            />
          </div>
        </div>
      )}
    </section>
  );
}
