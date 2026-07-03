import { CheckCircle2 } from "lucide-react";

import {
  formatDateTime,
  getActivityLabel,
  getActivityProgress,
  type DashboardActivityItem,
} from "../dashboard-types";

type DashboardActivityCardProps = {
  title: string;
  subtitle: string;
  items: DashboardActivityItem[];
  emptyMessage: string;
};

export function DashboardActivityCard({
  title,
  subtitle,
  items,
  emptyMessage,
}: DashboardActivityCardProps) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-5">
        <h2 className="font-semibold text-slate-900">{title}</h2>
        <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
      </div>

      {items.length === 0 ? (
        <p className="text-sm text-slate-500">{emptyMessage}</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          {items.map((item) => {
            const progress = getActivityProgress(item.status);

            return (
              <div
                key={item.id}
                className="rounded-xl border border-slate-200 p-4"
              >
                <div className="mb-2 flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                  <p className="font-medium text-slate-900">
                    {getActivityLabel(item.status)}
                  </p>
                  <span className="rounded-md bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                    Updated
                  </span>
                </div>

                <p className="text-sm text-slate-700">{item.company_name || "-"}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {formatDateTime(item.updated_at || item.created_at)}
                </p>

                <div className="mt-3 flex items-center gap-2">
                  <div className="h-2 flex-1 rounded-full bg-slate-200">
                    <div
                      className="h-2 rounded-full bg-green-500"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  <span className="text-xs font-medium text-slate-600">
                    {progress}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
