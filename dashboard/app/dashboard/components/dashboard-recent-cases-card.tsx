import Link from "next/link";
import { Building2 } from "lucide-react";

import {
  formatCompactCurrency,
  formatDateTime,
  getStatusBadgeClass,
  type DashboardRecentCase,
} from "../dashboard-types";

type DashboardRecentCasesCardProps = {
  title: string;
  subtitle: string;
  items: DashboardRecentCase[];
  emptyMessage: string;
};

export function DashboardRecentCasesCard({
  title,
  subtitle,
  items,
  emptyMessage,
}: DashboardRecentCasesCardProps) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h2 className="font-semibold text-slate-900">{title}</h2>
          <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
        </div>

        <Link
          href="/dashboard/cases"
          className="text-sm font-medium text-slate-700 transition hover:text-slate-950"
        >
          View all →
        </Link>
      </div>

      <div className="space-y-5">
        {items.length === 0 ? (
          <p className="text-sm text-slate-500">{emptyMessage}</p>
        ) : (
          items.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between gap-4 rounded-xl border border-transparent px-1 py-1"
            >
              <div className="flex items-center gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-50 text-cyan-600">
                  <Building2 className="h-5 w-5" />
                </div>

                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold text-slate-900">
                      {item.company_name || "-"}
                    </p>
                    <span
                      className={`rounded-md px-2 py-0.5 text-xs font-medium ${getStatusBadgeClass(
                        item.status
                      )}`}
                    >
                      {item.status || "New"}
                    </span>
                  </div>

                  <p className="text-sm text-slate-500">
                    {item.client_name || "-"} • {item.industry || "-"}
                  </p>
                </div>
              </div>

              <div className="text-right">
                <p className="font-semibold text-slate-900">
                  {formatCompactCurrency(
                    Number(item.requested_amount ?? item.loan_amount ?? 0)
                  )}
                </p>
                <p className="text-xs text-slate-500">
                  {formatDateTime(item.updated_at || item.created_at)}
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
