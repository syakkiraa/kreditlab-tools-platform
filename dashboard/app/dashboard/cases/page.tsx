"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

type CaseItem = {
  id: string;
  case_code: string | null;
  company_name: string | null;
  client_name: string | null;
  email?: string | null;
  client_email?: string | null;
  industry: string | null;
  requested_amount?: number | null;
  loan_amount?: number | null;
  status: string | null;
  assigned_to: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export default function CasesPage() {
  const router = useRouter();
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    const fetchCases = async () => {
      setLoading(true);
      setErrorMsg("");

      const { data, error } = await supabase
        .from("cases")
        .select("*")
        .order("updated_at", { ascending: false });

      console.log("CASES DATA:", data);
      console.log("CASES ERROR:", error);

      if (error) {
        setErrorMsg(error.message);
        setCases([]);
        setLoading(false);
        return;
      }

      setCases((data as CaseItem[]) || []);
      setLoading(false);
    };

    fetchCases();
  }, []);

  const filteredCases = useMemo(() => {
    return cases.filter((item) => {
      const emailValue = item.email || item.client_email || "";
      const codeValue = item.case_code || "";
      const companyValue = item.company_name || "";
      const clientValue = item.client_name || "";

      const matchesSearch =
        companyValue.toLowerCase().includes(search.toLowerCase()) ||
        clientValue.toLowerCase().includes(search.toLowerCase()) ||
        emailValue.toLowerCase().includes(search.toLowerCase()) ||
        codeValue.toLowerCase().includes(search.toLowerCase());

      const matchesStatus = statusFilter ? item.status === statusFilter : true;

      return matchesSearch && matchesStatus;
    });
  }, [cases, search, statusFilter]);

  const uniqueStatuses = [
    ...new Set(cases.map((item) => item.status).filter(Boolean)),
  ];

  const getStatusStyles = (status: string | null) => {
    switch (status) {
      case "Approved":
        return "bg-green-100 text-green-700 border-green-200";
      case "Rejected":
        return "bg-red-100 text-red-700 border-red-200";
      case "In Progress":
        return "bg-yellow-100 text-yellow-700 border-yellow-200";
      case "Under Review":
        return "bg-purple-100 text-purple-700 border-purple-200";
      default:
        return "bg-cyan-100 text-cyan-700 border-cyan-200";
    }
  };

  const formatDate = (value: string | null | undefined) => {
    if (!value) return "-";
    return new Date(value).toLocaleDateString();
  };

  const formatCurrency = (amount: number | null | undefined) => {
    return new Intl.NumberFormat("en-MY", {
      style: "currency",
      currency: "MYR",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount || 0);
  };

  return (
    <main className="p-6">
      <div className="mx-auto max-w-7xl">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Cases</h1>
            <p className="mt-1 text-slate-600">
              Manage and track all client cases
            </p>
          </div>

          <Link
            href="/dashboard/cases/new"
            className="inline-flex items-center justify-center rounded-xl bg-cyan-400 px-4 py-3 font-medium text-slate-900 transition hover:bg-cyan-300"
          >
            + New Case
          </Link>
        </div>

        <div className="mb-5 flex flex-col gap-3 md:flex-row">
          <input
            type="text"
            placeholder="Search by company, client, email, or case code..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-cyan-400 md:max-w-md"
          />

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-cyan-400"
          >
            <option value="">All Statuses</option>
            {uniqueStatuses.map((status) => (
              <option key={status} value={status || ""}>
                {status}
              </option>
            ))}
          </select>
        </div>

        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full">
            <thead className="bg-slate-50">
              <tr className="text-left text-sm font-medium text-slate-600">
                <th className="px-4 py-4">Case</th>
                <th className="px-4 py-4">Client</th>
                <th className="px-4 py-4">Industry</th>
                <th className="px-4 py-4">Loan Amount</th>
                <th className="px-4 py-4">Status</th>
                <th className="px-4 py-4">Assigned To</th>
                <th className="px-4 py-4">Updated</th>
              </tr>
            </thead>

            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-sm text-slate-500">
                    Loading...
                  </td>
                </tr>
              ) : errorMsg ? (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-sm text-red-600">
                    {errorMsg}
                  </td>
                </tr>
              ) : filteredCases.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-sm text-slate-500">
                    No cases found.
                  </td>
                </tr>
              ) : (
                filteredCases.map((item) => {
                  const emailValue = item.email || item.client_email || "-";
                  const amountValue = item.requested_amount ?? item.loan_amount ?? 0;
                  const updatedValue = item.updated_at || item.created_at || null;

                  return (
                    <tr
                      key={item.id}
                      onClick={() => router.push(`/dashboard/cases/${item.id}`)}
                      className="cursor-pointer border-t border-slate-200 text-sm transition hover:bg-slate-50"
                    >
                      <td className="px-4 py-4">
                        <div className="font-semibold text-slate-900">
                          {item.company_name || "-"}
                        </div>
                        <div className="text-xs text-slate-500">
                          {item.case_code || item.id.slice(0, 8)}
                        </div>
                      </td>

                      <td className="px-4 py-4">
                        <div className="font-medium text-slate-900">
                          {item.client_name || "-"}
                        </div>
                        <div className="text-xs text-slate-500">{emailValue}</div>
                      </td>

                      <td className="px-4 py-4">{item.industry || "-"}</td>

                      <td className="px-4 py-4 font-medium text-slate-900">
                        {formatCurrency(amountValue)}
                      </td>

                      <td className="px-4 py-4">
                        <span
                          className={`inline-flex rounded-full border px-3 py-1 text-xs font-medium ${getStatusStyles(
                            item.status
                          )}`}
                        >
                          {item.status || "New"}
                        </span>
                      </td>

                      <td className="px-4 py-4">{item.assigned_to || "-"}</td>

                      <td className="px-4 py-4">{formatDate(updatedValue)}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}