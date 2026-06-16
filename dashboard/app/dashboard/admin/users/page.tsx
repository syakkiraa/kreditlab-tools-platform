"use client";

import { useEffect, useMemo, useState } from "react";
import { supabase } from "@/lib/supabase";
import {
  Users,
  UserCheck,
  Shield,
  Pencil,
  Trash2,
  Briefcase,
} from "lucide-react";

type Profile = {
  id: string;
  full_name: string | null;
  email: string | null;
  role: string | null;
  status: string | null;
  created_at: string | null;
};

export default function AdminUsersPage() {
  const [usersList, setUsersList] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");

  useEffect(() => {
    const fetchUsers = async () => {
      const { data, error } = await supabase
        .from("profiles")
        .select("*")
        .order("created_at", { ascending: false });

      console.log("USERS:", data);
      console.log("ERROR:", error);

      if (!error && data) {
        setUsersList(data);
      }

      setLoading(false);
    };

    fetchUsers();
  }, []);

  const filteredUsers = useMemo(() => {
    return usersList.filter((user) => {
      const name = user.full_name || "";
      const email = user.email || "";

      const matchesSearch =
        name.toLowerCase().includes(search.toLowerCase()) ||
        email.toLowerCase().includes(search.toLowerCase());

      const matchesRole = roleFilter ? user.role === roleFilter : true;

      return matchesSearch && matchesRole;
    });
  }, [usersList, search, roleFilter]);

  const totalUsers = usersList.length;
  const activeUsers = usersList.filter((u) => u.status === "active").length;
  const adminUsers = usersList.filter((u) => u.role === "admin").length;

  const formatDate = (value: string | null) => {
    if (!value) return "-";
    return new Date(value).toLocaleDateString();
  };

  const getInitial = (name: string | null, email: string | null) => {
    return (name || email || "U").charAt(0).toUpperCase();
  };

  return (
    <main className="min-h-screen bg-slate-100 p-6">
      <div className="mx-auto max-w-6xl">
        {/* HEADER */}
        <div className="mb-6 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              User Management
            </h1>
            <p className="mt-1 text-slate-600">
              Manage team members and permissions
            </p>
          </div>

          <button className="rounded-xl bg-cyan-400 px-4 py-3 font-medium text-slate-900 hover:bg-cyan-300">
            + Add User
          </button>
        </div>

        {/* STATS */}
        <div className="mb-6 grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border bg-white p-6 shadow-sm">
            <div className="flex items-center gap-4">
              <div className="rounded-xl bg-cyan-50 p-3">
                <Users className="h-6 w-6 text-cyan-500" />
              </div>
              <div>
                <p className="text-3xl font-bold">{totalUsers}</p>
                <p className="text-slate-600">Total Users</p>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border bg-white p-6 shadow-sm">
            <div className="flex items-center gap-4">
              <div className="rounded-xl bg-green-50 p-3">
                <UserCheck className="h-6 w-6 text-green-500" />
              </div>
              <div>
                <p className="text-3xl font-bold">{activeUsers}</p>
                <p className="text-slate-600">Active Users</p>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border bg-white p-6 shadow-sm">
            <div className="flex items-center gap-4">
              <div className="rounded-xl bg-blue-50 p-3">
                <Shield className="h-6 w-6 text-blue-500" />
              </div>
              <div>
                <p className="text-3xl font-bold">{adminUsers}</p>
                <p className="text-slate-600">Admins</p>
              </div>
            </div>
          </div>
        </div>

        {/* FILTERS */}
        <div className="mb-5 flex flex-col gap-3 md:flex-row">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search users..."
            className="w-full rounded-xl border px-4 py-3 text-sm md:max-w-md"
          />

          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="rounded-xl border px-4 py-3 text-sm"
          >
            <option value="">All Roles</option>
            <option value="admin">Admin</option>
            <option value="consultant">Consultant</option>
          </select>
        </div>

        {/* TABLE */}
        <div className="overflow-hidden rounded-2xl border bg-white shadow-sm">
          <table className="min-w-full">
            <thead className="bg-slate-50">
              <tr className="text-left text-sm text-slate-600">
                <th className="px-4 py-4">User</th>
                <th className="px-4 py-4">Role</th>
                <th className="px-4 py-4">Status</th>
                <th className="px-4 py-4">Cases</th>
                <th className="px-4 py-4">Joined</th>
                <th className="px-4 py-4">Actions</th>
              </tr>
            </thead>

            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="p-6 text-sm">
                    Loading...
                  </td>
                </tr>
              ) : filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-6 text-sm">
                    No users found.
                  </td>
                </tr>
              ) : (
                filteredUsers.map((user) => (
                  <tr key={user.id} className="border-t">
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-3">
                        <div className="h-10 w-10 flex items-center justify-center rounded-full bg-cyan-50 text-cyan-600 font-semibold">
                          {getInitial(user.full_name, user.email)}
                        </div>
                        <div>
                          <p className="font-semibold">
                            {user.full_name || "User"}
                          </p>
                          <p className="text-sm text-slate-500">
                            {user.email || "No email"}
                          </p>
                        </div>
                      </div>
                    </td>

                    <td className="px-4 py-4">
                      <span className="bg-slate-100 px-3 py-1 rounded text-xs capitalize">
                        {user.role || "consultant"}
                      </span>
                    </td>

                    <td className="px-4 py-4">
                      <span className="bg-green-100 text-green-700 px-3 py-1 rounded text-xs">
                        {user.status || "active"}
                      </span>
                    </td>

                    <td className="px-4 py-4 flex items-center gap-2">
                      <Briefcase className="h-4 w-4 text-slate-500" />0
                    </td>

                    <td className="px-4 py-4">
                      {formatDate(user.created_at)}
                    </td>

                    <td className="px-4 py-4 flex gap-3">
                      <button>
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button className="text-red-500">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}