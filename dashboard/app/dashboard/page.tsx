"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  Bell,
  BriefcaseBusiness,
  ClipboardList,
  Search,
  TrendingUp,
} from "lucide-react";

import { supabase } from "@/lib/supabase";
import {
  buildDashboardOverview,
  type DashboardCaseRecord,
} from "@/lib/dashboard-overview";
import { type MainDashboardOverview } from "@/lib/main-dashboard-overview";
import { DashboardActivityCard } from "./components/dashboard-activity-card";
import { DashboardMainSystemCard } from "./components/dashboard-main-system-card";
import { DashboardPipelineCard } from "./components/dashboard-pipeline-card";
import { DashboardRecentCasesCard } from "./components/dashboard-recent-cases-card";
import { DashboardStatCard } from "./components/dashboard-stat-card";
import { formatCompactCurrency } from "./dashboard-types";

export default function DashboardPage() {
  const [cases, setCases] = useState<DashboardCaseRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [mainOverview, setMainOverview] = useState<MainDashboardOverview | null>(
    null
  );
  const [mainLoading, setMainLoading] = useState(true);
  const [mainError, setMainError] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    async function loadLocalCases() {
      setLoading(true);
      setErrorMsg("");

      const { data, error } = await supabase
        .from("cases")
        .select("*")
        .order("updated_at", { ascending: false });

      if (error) {
        setCases([]);
        setErrorMsg(error.message);
      } else {
        setCases((data as DashboardCaseRecord[]) || []);
      }

      setLoading(false);
    }

    async function loadMainOverview() {
      setMainLoading(true);
      setMainError("");

      try {
        const response = await fetch("/api/dashboard/main-system-overview");
        const payload = (await response.json().catch(() => ({}))) as Partial<
          MainDashboardOverview
        > & {
          error?: string;
        };

        if (!response.ok) {
          throw new Error(payload.error || "Main dashboard is unavailable");
        }

        setMainOverview(payload as MainDashboardOverview);
      } catch (error) {
        setMainError(error instanceof Error ? error.message : String(error));
        setMainOverview(null);
      } finally {
        setMainLoading(false);
      }
    }

    void loadLocalCases();
    void loadMainOverview();
  }, []);

  const filteredCases = useMemo(() => {
    const keyword = search.trim().toLowerCase();

    if (!keyword) {
      return cases;
    }

    return cases.filter((item) =>
      [item.company_name, item.client_name, item.case_code, item.status]
        .filter((value): value is string => Boolean(value))
        .some((value) => value.toLowerCase().includes(keyword))
    );
  }, [cases, search]);

  const overview = useMemo(
    () => buildDashboardOverview(filteredCases),
    [filteredCases]
  );

  const notificationCount = overview.stats.pendingAnalysis;

  return (
    <main className="min-h-screen bg-slate-100">
      <header className="flex flex-col gap-4 border-b bg-white px-6 py-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-500">
            Welcome back! Here&apos;s your overview.
          </p>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search cases..."
              className="w-full rounded-xl border border-slate-300 bg-white py-2.5 pl-10 pr-4 text-sm outline-none transition focus:border-cyan-400 sm:w-64"
            />
          </label>

          <div className="flex items-center gap-4">
            <div className="relative">
              <button className="rounded-full p-2 transition hover:bg-slate-100">
                <Bell className="h-4 w-4 text-amber-500" />
              </button>
              {notificationCount > 0 ? (
                <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-cyan-400 text-[10px] font-bold text-white">
                  {notificationCount}
                </span>
              ) : null}
            </div>

            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-cyan-100 text-sm font-bold text-cyan-700">
                A
              </div>
              <span className="text-sm font-semibold text-slate-700">
                Admin User
              </span>
            </div>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl space-y-6 p-6">
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <DashboardStatCard
            title="Total Cases"
            value={loading ? "..." : overview.stats.totalCases}
            sub={loading ? "Loading local data" : "+ cases recorded"}
            icon={<BriefcaseBusiness className="h-5 w-5" />}
          />
          <DashboardStatCard
            title="Active Cases"
            value={loading ? "..." : overview.stats.activeCases}
            sub={loading ? "Loading local data" : "currently active"}
            icon={<Activity className="h-5 w-5" />}
          />
          <DashboardStatCard
            title="Pending Analysis"
            value={loading ? "..." : overview.stats.pendingAnalysis}
            sub={loading ? "Loading local data" : "needs review"}
            icon={<ClipboardList className="h-5 w-5" />}
          />
          <DashboardStatCard
            title="Pipeline Value"
            value={
              loading ? "..." : formatCompactCurrency(overview.stats.pipelineValue)
            }
            sub={loading ? "Loading local data" : "total requested amount"}
            icon={<TrendingUp className="h-5 w-5" />}
          />
        </section>

        {errorMsg ? (
          <section className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {errorMsg}
          </section>
        ) : null}

        <section className="grid gap-6 lg:grid-cols-[2fr_1fr]">
          <DashboardRecentCasesCard
            title="Recent Cases"
            subtitle="Latest local cases in this dashboard workspace"
            items={loading ? [] : overview.recentCases}
            emptyMessage={loading ? "Loading local cases..." : "No cases found."}
          />

          <DashboardPipelineCard
            title="Pipeline Overview"
            subtitle="Local stage distribution by case status"
            stages={overview.pipelineStages}
          />
        </section>

        <DashboardActivityCard
          title="Recent Case Activity"
          subtitle="Latest local case progress updates"
          items={loading ? [] : overview.recentActivity}
          emptyMessage={loading ? "Loading local activity..." : "No activity yet."}
        />

        <DashboardMainSystemCard
          overview={mainOverview}
          loading={mainLoading}
          errorMsg={mainError}
        />
      </div>
    </main>
  );
}
