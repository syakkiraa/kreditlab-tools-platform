import { createClient } from "@supabase/supabase-js";
import { Resend } from "resend";

import {
  buildConsultantReminderSchedule,
  filterEligibleConsultantReminderCases,
} from "@/lib/consultant-reminder-schedule";

type ConsultantReminderCase = {
  id: string;
  case_code: string | null;
  client_name: string | null;
  company_name: string | null;
  email: string | null;
  phone: string | null;
  status: string | null;
  created_at: string | null;
  consultant_reminder_sent_at: string | null;
};

export async function GET() {
  return Response.json({
    success: true,
    message: "Consultant reminder route exists. Use POST to send reminders.",
  });
}

export async function POST(req: Request) {
  try {
    const cronSecret = process.env.CRON_SECRET;

    if (!cronSecret) {
      return Response.json(
        { error: "CRON_SECRET is missing" },
        { status: 500 }
      );
    }

    const authHeader = req.headers.get("authorization");

    if (authHeader !== `Bearer ${cronSecret}`) {
      return Response.json({ error: "Unauthorized" }, { status: 401 });
    }

    const resendApiKey = process.env.RESEND_API_KEY;
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const supabaseServiceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
    const consultantReminderEmail = process.env.CONSULTANT_REMINDER_EMAIL;

    if (
      !resendApiKey ||
      !supabaseUrl ||
      !supabaseServiceRoleKey ||
      !consultantReminderEmail
    ) {
      return Response.json(
        {
          error: "Missing environment variables",
          hasResendApiKey: !!resendApiKey,
          hasSupabaseUrl: !!supabaseUrl,
          hasSupabaseServiceRoleKey: !!supabaseServiceRoleKey,
          hasConsultantReminderEmail: !!consultantReminderEmail,
        },
        { status: 500 }
      );
    }

    const resend = new Resend(resendApiKey);
    const supabaseAdmin = createClient(supabaseUrl, supabaseServiceRoleKey);
    const schedule = buildConsultantReminderSchedule(new Date());

    const { data: cases, error: fetchError } = await supabaseAdmin
      .from("cases")
      .select(
        "id, case_code, client_name, company_name, email, phone, status, created_at, consultant_reminder_sent_at"
      )
      .lte("created_at", schedule.createdBeforeUtcIso);

    if (fetchError) {
      return Response.json({ error: fetchError.message }, { status: 500 });
    }

    const eligibleCases = filterEligibleConsultantReminderCases(
      (cases || []) as ConsultantReminderCase[],
      schedule
    );

    if (eligibleCases.length === 0) {
      return Response.json({
        success: true,
        message: "No consultant reminders to send",
        cutoff: schedule.createdBeforeUtcIso,
        foundCases: cases?.length || 0,
        eligibleCases: 0,
        sent: 0,
      });
    }

    const sendTimestamp = new Date().toISOString();
    const { data: emailData, error: emailError } = await resend.emails.send({
      from: "Capital Island <noreply@kreditlab.my>",
      to: [consultantReminderEmail],
      subject: `Consultant reminder: ${eligibleCases.length} case${
        eligibleCases.length === 1 ? "" : "s"
      } pending 7+ days`,
      html: buildConsultantReminderHtml(eligibleCases),
    });

    if (emailError) {
      return Response.json(
        {
          error: "Failed to send consultant reminder email",
          detail: emailError,
        },
        { status: 500 }
      );
    }

    const { error: updateError } = await supabaseAdmin
      .from("cases")
      .update({
        consultant_reminder_sent_at: sendTimestamp,
      })
      .in(
        "id",
        eligibleCases.map((item) => item.id)
      );

    if (updateError) {
      return Response.json(
        {
          error: "Consultant reminder email sent but case update failed",
          detail: updateError.message,
          sent: eligibleCases.length,
          caseIds: eligibleCases.map((item) => item.id),
        },
        { status: 500 }
      );
    }

    return Response.json({
      success: true,
      cutoff: schedule.createdBeforeUtcIso,
      foundCases: cases?.length || 0,
      eligibleCases: eligibleCases.length,
      sent: eligibleCases.length,
      caseIds: eligibleCases.map((item) => item.id),
      resendData: emailData,
    });
  } catch (error) {
    return Response.json(
      {
        error: "Failed to send consultant reminders",
        detail: error instanceof Error ? error.message : String(error),
      },
      { status: 500 }
    );
  }
}

function buildConsultantReminderHtml(cases: ConsultantReminderCase[]) {
  return `
    <h2>Consultant Follow-up Reminder</h2>
    <p>These cases are at least 7 days old and still need follow-up.</p>
    <ul>
      ${cases
        .map(
          (item) => `
        <li>
          <strong>${item.case_code || item.id}</strong><br />
          Client: ${item.client_name || "-"}<br />
          Company: ${item.company_name || "-"}<br />
          Status: ${item.status || "New"}<br />
          Email: ${item.email || "-"}<br />
          Phone: ${item.phone || "-"}<br />
          Created: ${formatReminderDate(item.created_at)}
        </li>
      `
        )
        .join("")}
    </ul>
    <p>Capital Island Sdn Bhd</p>
  `;
}

function formatReminderDate(value: string | null) {
  if (!value) {
    return "-";
  }

  return new Date(value).toLocaleDateString("en-MY", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}
