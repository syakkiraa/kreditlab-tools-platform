import { createClient } from "@supabase/supabase-js";

const DOCUMENT_BUCKET = "case-documents";

export const runtime = "nodejs";

type CaseDocument = {
  id: string;
  case_id: string;
  file_name: string | null;
  file_path: string;
};

export async function POST(req: Request) {
  try {
    const body = (await req.json()) as {
      caseId?: unknown;
      documentId?: unknown;
    };
    const caseId = typeof body.caseId === "string" ? body.caseId : "";
    const documentId =
      typeof body.documentId === "string" ? body.documentId : "";

    if (!caseId || !documentId) {
      return Response.json(
        { error: "caseId and documentId are required", code: "missing_input" },
        { status: 400 }
      );
    }

    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

    if (!supabaseUrl || !serviceRoleKey) {
      return Response.json(
        {
          error: "Missing server environment variables",
          code: "missing_supabase_env",
          hasSupabaseUrl: !!supabaseUrl,
          hasServiceRoleKey: !!serviceRoleKey,
        },
        { status: 500 }
      );
    }

    const supabaseAdmin = createClient(supabaseUrl, serviceRoleKey);
    const { data: document, error: documentError } = await supabaseAdmin
      .from("case_documents")
      .select("*")
      .eq("case_id", caseId)
      .eq("id", documentId)
      .single();

    if (documentError || !document) {
      return Response.json(
        {
          error: documentError?.message || "Document was not found",
          code: "missing_input",
        },
        { status: 404 }
      );
    }

    const caseDocument = document as CaseDocument;
    const { error: storageError } = await supabaseAdmin.storage
      .from(DOCUMENT_BUCKET)
      .remove([caseDocument.file_path]);

    if (storageError) {
      return Response.json(
        {
          error: storageError.message,
          code: "dashboard_execution_failure",
        },
        { status: 500 }
      );
    }

    const { error: deleteError } = await supabaseAdmin
      .from("case_documents")
      .delete()
      .eq("case_id", caseId)
      .eq("id", documentId);

    if (deleteError) {
      return Response.json(
        {
          error: deleteError.message,
          code: "dashboard_execution_failure",
        },
        { status: 500 }
      );
    }

    return Response.json({
      success: true,
      deletedDocument: {
        id: caseDocument.id,
        fileName: caseDocument.file_name,
      },
    });
  } catch (error) {
    return Response.json(
      {
        error: "Failed to delete document",
        code: "dashboard_execution_failure",
        detail: error instanceof Error ? error.message : String(error),
      },
      { status: 500 }
    );
  }
}
