import { Resend } from "resend";

export async function POST(req: Request) {
  try {
    const resendApiKey = process.env.RESEND_API_KEY;

    if (!resendApiKey) {
      return Response.json(
        { error: "RESEND_API_KEY is missing" },
        { status: 500 }
      );
    }

    const resend = new Resend(resendApiKey);
    const { email, clientName, companyName, caseCode } = await req.json();

    if (!email) {
      return Response.json({ error: "Email is required" }, { status: 400 });
    }

    const { data, error } = await resend.emails.send({
      from: "Capital Island <noreply@kreditlab.my>",
      to: email,
      subject: "Your financing case has been registered",
      html: `
        <h2>Hi ${clientName || "there"},</h2>
        <p>Your financing case has been registered successfully.</p>
        <p><strong>Company:</strong> ${companyName || "-"}</p>
        <p><strong>Case ID:</strong> ${caseCode || "-"}</p>
        <p>Our consultant will contact you soon.</p>
        <br />
        <p>Capital Island Sdn Bhd</p>
      `,
    });

    if (error) {
      return Response.json({ error }, { status: 500 });
    }

    return Response.json({ success: true, data });
  } catch (error) {
    return Response.json(
      {
        error: "Failed to send email",
        detail: error instanceof Error ? error.message : String(error),
      },
      { status: 500 }
    );
  }
}