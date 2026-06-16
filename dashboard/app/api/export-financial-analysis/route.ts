import {
  exportFinancialAnalysisArtifact,
  FinancialAnalysisError,
  type FinancialAnalysisExportFormat,
} from "@/lib/server/financial-statement-analysis";

export const runtime = "nodejs";
export const maxDuration = 300;

const EXPORT_FORMATS = new Set<FinancialAnalysisExportFormat>([
  "html",
  "pdf",
  "excel",
]);

export async function POST(req: Request) {
  try {
    const body = (await req.json()) as {
      format?: unknown;
      report?: unknown;
      fileName?: unknown;
    };
    const format =
      typeof body.format === "string" &&
      EXPORT_FORMATS.has(body.format as FinancialAnalysisExportFormat)
        ? (body.format as FinancialAnalysisExportFormat)
        : null;

    if (!format) {
      return Response.json(
        {
          error: "Export format must be html, pdf, or excel",
          code: "missing_input",
        },
        { status: 400 }
      );
    }

    const artifact = await exportFinancialAnalysisArtifact({
      format,
      report: body.report,
      fileName: typeof body.fileName === "string" ? body.fileName : undefined,
    });

    return new Response(
      new Blob([artifact.content], { type: artifact.contentType }),
      {
        headers: {
          "Content-Type": artifact.contentType,
          "Content-Disposition": `attachment; filename="${sanitizeHeaderFileName(
            artifact.fileName
          )}"`,
          "Cache-Control": "no-store",
        },
      }
    );
  } catch (error) {
    if (error instanceof FinancialAnalysisError) {
      return Response.json(
        {
          error: error.message,
          code: error.code,
          detail: error.detail,
        },
        { status: error.status }
      );
    }

    return Response.json(
      {
        error: "Failed to export financial analysis",
        code: "dashboard_execution_failure",
        detail: error instanceof Error ? error.message : String(error),
      },
      { status: 500 }
    );
  }
}

function sanitizeHeaderFileName(fileName: string) {
  return fileName.replace(/["\r\n]/g, "").trim() || "financial-analysis";
}
