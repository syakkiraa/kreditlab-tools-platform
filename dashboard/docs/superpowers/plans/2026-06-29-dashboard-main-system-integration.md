# Dashboard Main System Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dashboard overview page in this repo that matches the main dashboard visual pattern, summarizes local case progress, and also shows authenticated progress data from the main dashboard system.

**Architecture:** Keep the browser simple: fetch local data from this repo's Supabase-backed route logic and fetch main-system data through one server-to-server proxy route in this repo. Split the UI into a small set of dashboard cards and move non-trivial aggregation/normalization into `lib/` helpers with targeted `node --test` coverage.

**Tech Stack:** Next.js App Router, React client components, Supabase JS, native `fetch`, Node test runner, TypeScript

---

### Task 1: Add dashboard summary helper and failing tests

**Files:**
- Create: `lib/dashboard-overview.ts`
- Create: `lib/dashboard-overview.test.ts`
- Modify: `app/dashboard/page.tsx`

- [ ] **Step 1: Write the failing test for local KPI and pipeline shaping**

```ts
import test from "node:test";
import assert from "node:assert/strict";

import { buildDashboardOverview } from "./dashboard-overview.ts";

test("buildDashboardOverview summarizes KPIs and recent cases", () => {
  const overview = buildDashboardOverview([
    {
      id: "case-1",
      case_code: "CASE-1",
      company_name: "AAA Enterprise",
      client_name: "Arthur",
      industry: "Finance",
      status: "New",
      requested_amount: 190000,
      created_at: "2026-06-16T09:04:00.000Z",
      updated_at: "2026-06-16T09:04:00.000Z",
    },
    {
      id: "case-2",
      case_code: "CASE-2",
      company_name: "BBB Enterprise",
      client_name: "Bella",
      industry: "Technology",
      status: "Approved",
      requested_amount: 250000,
      created_at: "2026-06-15T09:04:00.000Z",
      updated_at: "2026-06-15T09:04:00.000Z",
    },
  ]);

  assert.equal(overview.stats.totalCases, 2);
  assert.equal(overview.stats.activeCases, 1);
  assert.equal(overview.stats.pendingAnalysis, 1);
  assert.equal(overview.stats.pipelineValue, 440000);
  assert.equal(overview.recentCases[0]?.id, "case-1");
  assert.equal(overview.pipelineStages[0]?.name, "New");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test lib/dashboard-overview.test.ts`
Expected: FAIL with `ERR_MODULE_NOT_FOUND` or missing export because `lib/dashboard-overview.ts` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```ts
export type DashboardCaseRecord = {
  id: string;
  case_code: string | null;
  company_name: string | null;
  client_name: string | null;
  industry: string | null;
  status: string | null;
  requested_amount?: number | null;
  loan_amount?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
};

const PIPELINE_STAGES = [
  "New",
  "Qualification",
  "Analysis",
  "Proposal",
  "Negotiation",
  "Closed Won",
  "Closed Lost",
] as const;

export function buildDashboardOverview(cases: DashboardCaseRecord[]) {
  const sortedCases = [...cases].sort((a, b) =>
    (b.updated_at || b.created_at || "").localeCompare(a.updated_at || a.created_at || "")
  );

  const pipelineValue = cases.reduce(
    (sum, item) => sum + Number(item.requested_amount ?? item.loan_amount ?? 0),
    0
  );

  return {
    stats: {
      totalCases: cases.length,
      activeCases: cases.filter((item) =>
        !["Rejected", "Closed Lost", "Closed Won", "Approved"].includes(item.status || "")
      ).length,
      pendingAnalysis: cases.filter((item) =>
        ["New", "In Progress", "Under Review"].includes(item.status || "")
      ).length,
      pipelineValue,
    },
    recentCases: sortedCases.slice(0, 5),
    recentActivity: sortedCases.slice(0, 6),
    pipelineStages: PIPELINE_STAGES.map((name) => {
      const stageCases = cases.filter((item) => item.status === name);

      return {
        name,
        count: stageCases.length,
        value: stageCases.reduce(
          (sum, item) => sum + Number(item.requested_amount ?? item.loan_amount ?? 0),
          0
        ),
      };
    }),
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test lib/dashboard-overview.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lib/dashboard-overview.ts lib/dashboard-overview.test.ts
git commit -m "feat: add dashboard overview summary helper"
```

### Task 2: Add main-system normalization helper and proxy route

**Files:**
- Create: `lib/main-dashboard-overview.ts`
- Create: `lib/main-dashboard-overview.test.ts`
- Create: `app/api/dashboard/main-system-overview/route.ts`

- [ ] **Step 1: Write the failing test for main-system payload normalization**

```ts
import test from "node:test";
import assert from "node:assert/strict";

import { normalizeMainDashboardOverview } from "./main-dashboard-overview.ts";

test("normalizeMainDashboardOverview applies safe defaults", () => {
  const overview = normalizeMainDashboardOverview({
    stats: {
      totalCases: 3,
      activeCases: 3,
      pendingAnalysis: 3,
      pipelineValue: 1213600000,
    },
    recentCases: [],
  });

  assert.equal(overview.stats.totalCases, 3);
  assert.equal(overview.pipelineStages.length > 0, true);
  assert.deepEqual(overview.recentActivity, []);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test lib/main-dashboard-overview.test.ts`
Expected: FAIL because `lib/main-dashboard-overview.ts` does not exist yet.

- [ ] **Step 3: Write minimal implementation and proxy route**

```ts
const DEFAULT_PIPELINE_STAGES = [
  "New",
  "Qualification",
  "Analysis",
  "Proposal",
  "Negotiation",
  "Closed Won",
  "Closed Lost",
];

export function normalizeMainDashboardOverview(payload: Record<string, unknown>) {
  const stats = typeof payload.stats === "object" && payload.stats ? payload.stats as Record<string, unknown> : {};
  const pipelineStages = Array.isArray(payload.pipelineStages) ? payload.pipelineStages : DEFAULT_PIPELINE_STAGES.map((name) => ({
    name,
    count: 0,
    value: 0,
  }));

  return {
    source: "main-dashboard",
    stats: {
      totalCases: Number(stats.totalCases || 0),
      activeCases: Number(stats.activeCases || 0),
      pendingAnalysis: Number(stats.pendingAnalysis || 0),
      pipelineValue: Number(stats.pipelineValue || 0),
    },
    recentCases: Array.isArray(payload.recentCases) ? payload.recentCases : [],
    pipelineStages,
    recentActivity: Array.isArray(payload.recentActivity) ? payload.recentActivity : [],
  };
}
```

```ts
import { normalizeMainDashboardOverview } from "@/lib/main-dashboard-overview";

export async function GET() {
  const baseUrl = process.env.MAIN_DASHBOARD_BASE_URL;
  const token = process.env.MAIN_DASHBOARD_API_TOKEN;

  if (!baseUrl || !token) {
    return Response.json(
      {
        error: "Missing main dashboard configuration",
        hasMainDashboardBaseUrl: !!baseUrl,
        hasMainDashboardApiToken: !!token,
      },
      { status: 500 }
    );
  }

  const response = await fetch(`${baseUrl}/api/dashboard/overview`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });

  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    return Response.json(
      {
        error: "Main dashboard request failed",
        status: response.status,
      },
      { status: 502 }
    );
  }

  return Response.json(normalizeMainDashboardOverview(payload));
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test lib/main-dashboard-overview.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lib/main-dashboard-overview.ts lib/main-dashboard-overview.test.ts app/api/dashboard/main-system-overview/route.ts
git commit -m "feat: add main dashboard overview proxy"
```

### Task 3: Build the dashboard page UI and client fetch flow

**Files:**
- Create: `app/dashboard/dashboard-types.ts`
- Create: `app/dashboard/components/dashboard-stat-card.tsx`
- Create: `app/dashboard/components/dashboard-recent-cases-card.tsx`
- Create: `app/dashboard/components/dashboard-pipeline-card.tsx`
- Create: `app/dashboard/components/dashboard-activity-card.tsx`
- Create: `app/dashboard/components/dashboard-main-system-card.tsx`
- Modify: `app/dashboard/page.tsx`

- [ ] **Step 1: Write the failing test for a formatting/helper behavior if extraction is needed**

```ts
import test from "node:test";
import assert from "node:assert/strict";

import { formatCompactCurrency } from "./dashboard-types.ts";

test("formatCompactCurrency formats large MYR values for KPI display", () => {
  assert.equal(formatCompactCurrency(1213600000), "MYR 1213.6M");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test app/dashboard/dashboard-types.test.ts`
Expected: FAIL because helper file or export does not exist yet.

- [ ] **Step 3: Implement the dashboard UI**

```tsx
"use client";

import { useEffect, useMemo, useState } from "react";
import { supabase } from "@/lib/supabase";
import { buildDashboardOverview, type DashboardCaseRecord } from "@/lib/dashboard-overview";
import { DashboardStatCard } from "./components/dashboard-stat-card";
import { DashboardRecentCasesCard } from "./components/dashboard-recent-cases-card";
import { DashboardPipelineCard } from "./components/dashboard-pipeline-card";
import { DashboardActivityCard } from "./components/dashboard-activity-card";
import { DashboardMainSystemCard } from "./components/dashboard-main-system-card";

export default function DashboardPage() {
  const [cases, setCases] = useState<DashboardCaseRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [mainOverview, setMainOverview] = useState<unknown>(null);
  const [mainLoading, setMainLoading] = useState(true);
  const [mainError, setMainError] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    async function loadLocalCases() {
      const { data, error } = await supabase.from("cases").select("*").order("updated_at", { ascending: false });

      if (error) {
        setErrorMsg(error.message);
        setCases([]);
      } else {
        setCases((data as DashboardCaseRecord[]) || []);
      }

      setLoading(false);
    }

    async function loadMainOverview() {
      try {
        const response = await fetch("/api/dashboard/main-system-overview");
        const payload = await response.json();

        if (!response.ok) {
          throw new Error(typeof payload.error === "string" ? payload.error : "Main system unavailable");
        }

        setMainOverview(payload);
      } catch (error) {
        setMainError(error instanceof Error ? error.message : String(error));
      } finally {
        setMainLoading(false);
      }
    }

    void loadLocalCases();
    void loadMainOverview();
  }, []);

  const filteredCases = useMemo(() => {
    const keyword = search.toLowerCase();

    return cases.filter((item) =>
      [item.company_name, item.client_name, item.case_code, item.status]
        .filter(Boolean)
        .some((value) => value!.toLowerCase().includes(keyword))
    );
  }, [cases, search]);

  const overview = useMemo(() => buildDashboardOverview(filteredCases), [filteredCases]);

  return <main>{/* render cards and states */}</main>;
}
```

- [ ] **Step 4: Run targeted verification**

Run:
- `node --test lib/dashboard-overview.test.ts`
- `node --test lib/main-dashboard-overview.test.ts`
- `node --test app/dashboard/dashboard-types.test.ts`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/dashboard/page.tsx app/dashboard/dashboard-types.ts app/dashboard/components
git commit -m "feat: add integrated dashboard overview UI"
```

### Task 4: Add the main dashboard overview endpoint in the reference repo

**Files:**
- Create: `C:/Users/Sharky/Documents/kreditlabfullsystem/kredit-lab-dashboard/lib/dashboard-overview.ts`
- Create: `C:/Users/Sharky/Documents/kreditlabfullsystem/kredit-lab-dashboard/lib/dashboard-overview.test.ts`
- Create: `C:/Users/Sharky/Documents/kreditlabfullsystem/kredit-lab-dashboard/app/api/dashboard/overview/route.ts`

- [ ] **Step 1: Write the failing test for the main dashboard summary helper**

```ts
import test from "node:test";
import assert from "node:assert/strict";

import { buildDashboardOverview } from "./dashboard-overview.ts";

test("buildDashboardOverview shapes the main dashboard API payload", () => {
  const overview = buildDashboardOverview([
    {
      id: "case-1",
      case_code: "CASE-1",
      company_name: "AAA Enterprise",
      client_name: "Arthur",
      industry: "Finance",
      status: "New",
      requested_amount: 190000,
      created_at: "2026-06-16T09:04:00.000Z",
    },
  ]);

  assert.equal(overview.stats.totalCases, 1);
  assert.equal(overview.recentCases.length, 1);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test lib/dashboard-overview.test.ts`
Expected: FAIL because the helper does not exist yet in the main dashboard repo.

- [ ] **Step 3: Implement the helper and overview route**

```ts
import { createClient } from "@supabase/supabase-js";
import { buildDashboardOverview } from "@/lib/dashboard-overview";

export async function GET(req: Request) {
  const token = process.env.MAIN_DASHBOARD_API_TOKEN;

  if (!token) {
    return Response.json({ error: "MAIN_DASHBOARD_API_TOKEN is missing" }, { status: 500 });
  }

  if (req.headers.get("authorization") !== `Bearer ${token}`) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!supabaseUrl || !serviceRoleKey) {
    return Response.json({ error: "Missing environment variables" }, { status: 500 });
  }

  const supabaseAdmin = createClient(supabaseUrl, serviceRoleKey);
  const { data, error } = await supabaseAdmin.from("cases").select("*").order("updated_at", { ascending: false });

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  return Response.json(buildDashboardOverview(data || []));
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test lib/dashboard-overview.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git -C C:/Users/Sharky/Documents/kreditlabfullsystem/kredit-lab-dashboard add lib/dashboard-overview.ts lib/dashboard-overview.test.ts app/api/dashboard/overview/route.ts
git -C C:/Users/Sharky/Documents/kreditlabfullsystem/kredit-lab-dashboard commit -m "feat: add dashboard overview api"
```
