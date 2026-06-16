"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { supabase } from "@/lib/supabase";

export default function NewCasePage() {
  const router = useRouter();

  const [ssmId, setSsmId] = useState("");
  const [clientName, setClientName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [industry, setIndustry] = useState("");
  const [employeeCount, setEmployeeCount] = useState("");
  const [annualRevenue, setAnnualRevenue] = useState("");
  const [requestedAmount, setRequestedAmount] = useState("");
  const [loanPurpose, setLoanPurpose] = useState("");
  const [initialNotes, setInitialNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

const handleCreateCase = async (e: React.FormEvent) => {
  e.preventDefault();
  setLoading(true);
  setErrorMsg("");

  const {
    data: { user },
    error: userError,
  } = await supabase.auth.getUser();

  if (userError || !user) {
    setErrorMsg("You must be logged in first.");
    setLoading(false);
    return;
  }

    // ✅ CREATE CASE CODE ONCE
    const caseCode = `CASE-${Date.now()}`;

    const { error } = await supabase.from("cases").insert([
      {
        client_name: clientName,
        company_name: companyName,
        ssm_registration_id: ssmId,
        email,
        phone,
        industry,
        employee_count: employeeCount ? Number(employeeCount) : null,
        annual_revenue: annualRevenue ? Number(annualRevenue) : null,
        requested_amount: Number(requestedAmount),
        loan_purpose: loanPurpose,
        initial_notes: initialNotes,
        case_code: caseCode,
        status: "New",
        assigned_to: "Admin User",
        updated_at: new Date().toISOString(),
        created_by: user.id,
      },
    ]);

    if (error) {
      setErrorMsg(error.message);
      setLoading(false);
      return;
    }

      // ✅ SEND EMAIL immediately after case is created
      try {
        const res = await fetch("/api/send-case-email/send-case-email", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email,
            clientName,
            companyName,
            caseCode,
          }),
        });

        const result = await res.json();

        console.log("EMAIL STATUS:", res.status);
        console.log("EMAIL RESULT:", result);
      } catch (err) {
        console.log("EMAIL FETCH ERROR:", err);
      }

      // ✅ THEN REDIRECT
      router.push("/dashboard/cases");
      router.refresh();
    };

  return (
    <main className="min-h-screen bg-slate-100 px-6 py-8">
      <div className="mx-auto max-w-5xl">
        <Link
          href="/dashboard/cases"
          className="mb-6 inline-flex text-sm text-slate-600 hover:text-slate-900"
        >
          ← Back to Cases
        </Link>

        <form onSubmit={handleCreateCase} className="space-y-6">
          {/* Client Info */}
          <section className="rounded-2xl border bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold">Client Information</h2>

            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <input
                placeholder="Client Name"
                value={clientName}
                onChange={(e) => setClientName(e.target.value)}
                className="border p-3 rounded-xl"
                required
              />

              <input
                placeholder="Company Name"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                className="border p-3 rounded-xl"
                required
              />

              <input
              placeholder="SSM Registration ID"
              value={ssmId}
              onChange={(e) => setSsmId(e.target.value)}
              className="border p-3 rounded-xl"
              />
                          
              <input
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="border p-3 rounded-xl"
                required
              />

              <input
                placeholder="Phone"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="border p-3 rounded-xl"
              />
            </div>
          </section>

          {/* Business */}
          <section className="rounded-2xl border bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold">Business Details</h2>

            <div className="mt-4 grid gap-4 md:grid-cols-2">
            <select
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              className="border p-3 rounded-xl bg-white"
              required
            >
              <option value="">Select industry</option>
              <option value="Technology">Technology</option>
              <option value="Healthcare">Healthcare</option>
              <option value="Finance">Finance</option>
              <option value="Manufacturing">Manufacturing</option>
              <option value="Retail">Retail</option>
              <option value="Food & Beverage">Food & Beverage</option>
              <option value="Agriculture">Agriculture</option>
              <option value="Construction">Construction</option>
              <option value="Real Estate">Real Estate</option>
              <option value="Transportation">Transportation</option>
              <option value="Energy">Energy</option>
              <option value="Education">Education</option>
              <option value="Other">Other</option>
            </select>

              <input
                type="number"
                placeholder="Employee Count"
                value={employeeCount}
                onChange={(e) => setEmployeeCount(e.target.value)}
                className="border p-3 rounded-xl"
              />

              <input
                type="number"
                placeholder="Annual Revenue"
                value={annualRevenue}
                onChange={(e) => setAnnualRevenue(e.target.value)}
                className="border p-3 rounded-xl md:col-span-2"
              />
            </div>
          </section>

          {/* Loan */}
          <section className="rounded-2xl border bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold">Loan Request</h2>

            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <input
                type="number"
                placeholder="Requested Amount"
                value={requestedAmount}
                onChange={(e) => setRequestedAmount(e.target.value)}
                className="border p-3 rounded-xl"
                required
              />

            <select
              value={loanPurpose}
              onChange={(e) => setLoanPurpose(e.target.value)}
              className="border p-3 rounded-xl bg-white"
              required
            >
              <option value="">Select purpose</option>
              <option value="Working Capital">Working Capital</option>
              <option value="Business Expansion">Business Expansion</option>
              <option value="Equipment Purchase">Equipment Purchase</option>
              <option value="Real Estate">Real Estate</option>
              <option value="Acquisition">Acquisition</option>
              <option value="Debt Refinancing">Debt Refinancing</option>
              <option value="Inventory">Inventory</option>
              <option value="Other">Other</option>
            </select>

              <textarea
                placeholder="Notes..."
                value={initialNotes}
                onChange={(e) => setInitialNotes(e.target.value)}
                className="border p-3 rounded-xl md:col-span-2"
              />
            </div>
          </section>

          {errorMsg && (
            <p className="text-red-500 text-sm">{errorMsg}</p>
          )}

          <div className="flex justify-end gap-3">
            <Link
              href="/dashboard/cases"
              className="border px-4 py-2 rounded-xl"
            >
              Cancel
            </Link>

            <button
              type="submit"
              className="bg-cyan-400 px-4 py-2 rounded-xl"
            >
              {loading ? "Creating..." : "Create Case"}
            </button>
          </div>
        </form>
      </div>
    </main>
  );
}