import { ReactNode } from "react";
import { Sidebar } from "./sidebar";
export default function DashboardLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-slate-100">
      <Sidebar />
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}