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

  try {
    const response = await fetch(`${baseUrl}/api/dashboard/overview`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
    });
    const payload = (await response.json().catch(() => ({}))) as Record<
      string,
      unknown
    >;

    if (!response.ok) {
      return Response.json(
        {
          error: "Main dashboard request failed",
          status: response.status,
          detail: typeof payload.error === "string" ? payload.error : undefined,
        },
        { status: 502 }
      );
    }

    return Response.json(normalizeMainDashboardOverview(payload));
  } catch (error) {
    return Response.json(
      {
        error: "Failed to reach main dashboard",
        detail: error instanceof Error ? error.message : String(error),
      },
      { status: 502 }
    );
  }
}
