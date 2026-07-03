import type { ReactNode } from "react";

type DashboardStatCardProps = {
  title: string;
  value: string | number;
  sub: string;
  icon: ReactNode;
};

export function DashboardStatCard({
  title,
  value,
  sub,
  icon,
}: DashboardStatCardProps) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-600">{title}</p>
          <p className="mt-2 text-2xl font-bold text-slate-900">{value}</p>
          <p className="mt-2 text-xs text-green-600">{sub}</p>
        </div>

        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-50 text-cyan-600">
          {icon}
        </div>
      </div>
    </div>
  );
}
