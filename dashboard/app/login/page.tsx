"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { FileText, Eye, EyeOff } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg("");

    const { data, error } = await supabase.auth.signInWithPassword({
      email: email.trim(),
      password,
    });

    console.log("LOGIN DATA:", data);
    console.log("LOGIN ERROR:", error);

    if (error) {
      setErrorMsg(error.message);
      setLoading(false);
      return;
    }

    router.push("/dashboard");
    setLoading(false);
  };

  return (
    <main className="min-h-screen bg-[#031b2f] flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 flex flex-col items-center justify-center gap-2">
          <img
            src="/logo-dark.png"
            alt="Company Logo"
            className="h-20 w-auto"
          />

          <p className="text-lg text-slate-400">
            Capital Island Sdn Bhd
          </p>
        </div>

        <div className="rounded-2xl bg-white p-7 shadow-2xl">
          <div className="mb-7 text-center">
            <h2 className="text-4xl font-bold text-slate-900">Welcome back</h2>
            <p className="mt-3 text-sm text-slate-500">
              Sign in to your account to continue
            </p>
          </div>

          <form onSubmit={handleLogin} className="space-y-5">
            <div>
              <label className="mb-2 block text-lg font-semibold text-slate-900">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@kreditlab.com"
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-lg text-slate-900 outline-none transition focus:border-[#48c7ba] focus:ring-2 focus:ring-[#48c7ba]/20"
                required
              />
            </div>

            <div>
              <label className="mb-2 block text-lg font-semibold text-slate-900">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 pr-12 text-lg text-slate-900 outline-none transition focus:border-[#48c7ba] focus:ring-2 focus:ring-[#48c7ba]/20"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-700"
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5" />
                  ) : (
                    <Eye className="h-5 w-5" />
                  )}
                </button>
              </div>
            </div>

            {errorMsg && (
              <div className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">
                {errorMsg}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-[#48c7ba] px-4 py-3 text-lg font-semibold text-[#031b2f] transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>
        </div>
      </div>
    </main>
  );
}