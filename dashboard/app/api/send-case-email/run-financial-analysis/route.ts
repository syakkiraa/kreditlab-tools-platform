import { POST as runFinancialAnalysis } from "@/app/api/run-financial-analysis/route";

export const runtime = "nodejs";
export const maxDuration = 300;
export const POST = runFinancialAnalysis;
