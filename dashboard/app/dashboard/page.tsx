import Link from "next/link";

export default function DashboardPage() {
  return (
    <main className="min-h-screen bg-slate-50 p-6">
      <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
      <p className="mt-2 text-slate-600">Welcome to Kredit Lab System.</p>

      <div className="mt-6">
        <Link
          href="/dashboard/cases"
          className="inline-flex rounded-xl bg-cyan-400 px-4 py-3 font-medium text-slate-900 hover:bg-cyan-300"
        >
          Go to Cases
        </Link>
      </div>
    </main>
  );
}