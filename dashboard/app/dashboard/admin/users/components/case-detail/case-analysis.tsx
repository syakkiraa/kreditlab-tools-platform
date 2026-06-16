"use client";

import { useState } from "react";
import {
  Play,
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  FileSpreadsheet,
  FileText,
  CreditCard,
  GitCompareArrows,
  RefreshCw,
  Eye,
} from "lucide-react";

type AnalysisType =
  | "bank_statement"
  | "financial_statement"
  | "credit_score"
  | "bank_matching";

type AnalysisStatus = "pending" | "running" | "completed" | "failed";

type AnalysisResult = {
  id: string;
  type: AnalysisType;
  status: AnalysisStatus;
  score?: number;
  summary?: string;
  createdAt: string;
  completedAt?: string;
};

type CaseData = {
  id: string;
  company_name: string;
  client_name: string;
  requested_amount: number;
  initial_notes?: string | null;
};

interface CaseAnalysisProps {
  caseData: CaseData;
}

interface AnalysisModule {
  id: string;
  type: AnalysisType;
  name: string;
  description: string;
  icon: typeof FileSpreadsheet;
  requiredDocs: string[];
}

const ANALYSIS_MODULES: AnalysisModule[] = [
  {
    id: "bank_statement",
    type: "bank_statement",
    name: "Bank Statement Analyzer",
    description: "Analyze cash flow patterns, transaction history, and account health",
    icon: FileSpreadsheet,
    requiredDocs: ["bank_statement"],
  },
  {
    id: "credit_score",
    type: "credit_score",
    name: "Credit Scoring Engine",
    description: "Calculate credit worthiness based on multiple data points",
    icon: CreditCard,
    requiredDocs: ["bank_statement", "financial_statement"],
  },
  {
    id: "bank_matching",
    type: "bank_matching",
    name: "Bank Matching Engine",
    description: "Match case profile with suitable bank criteria",
    icon: GitCompareArrows,
    requiredDocs: ["bank_statement", "financial_statement"],
  },
];

export function CaseAnalysis({ caseData }: CaseAnalysisProps) {
  const [runningModules, setRunningModules] = useState<Set<string>>(new Set());

  // Temporary mock results so the UI looks alive
  const [analysisResults, setAnalysisResults] = useState<AnalysisResult[]>([
    {
      id: "result-1",
      type: "bank_statement",
      status: "completed",
      score: 78,
      summary: "Cash flow appears stable with moderate anomalies flagged.",
      createdAt: new Date().toISOString(),
      completedAt: new Date().toISOString(),
    },
  ]);

  const getAnalysisResult = (type: AnalysisType) => {
    return analysisResults.find((a) => a.type === type);
  };

  // For now always true so you can see the UI working
  const hasRequiredDocs = (_requiredDocs: string[]) => {
    return true;
  };

  const runAnalysis = async (moduleId: string, type: AnalysisType) => {
    setRunningModules((prev) => new Set(prev).add(moduleId));

    setAnalysisResults((prev) => {
      const existing = prev.find((item) => item.type === type);

      if (existing) {
        return prev.map((item) =>
          item.type === type
            ? {
                ...item,
                status: "running",
                createdAt: new Date().toISOString(),
              }
            : item
        );
      }

      return [
        ...prev,
        {
          id: `${type}-${Date.now()}`,
          type,
          status: "running",
          createdAt: new Date().toISOString(),
        },
      ];
    });

    await new Promise((resolve) => setTimeout(resolve, 2500));

    setAnalysisResults((prev) =>
      prev.map((item) =>
        item.type === type
          ? {
              ...item,
              status: "completed",
              score: Math.floor(Math.random() * 30) + 70,
              summary: `${type.replaceAll("_", " ")} completed successfully for ${caseData.company_name}.`,
              completedAt: new Date().toISOString(),
            }
          : item
      )
    );

    setRunningModules((prev) => {
      const next = new Set(prev);
      next.delete(moduleId);
      return next;
    });
  };

  const formatDate = (date: string) => {
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(date));
  };

  const getStatusIcon = (status: AnalysisStatus) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 className="h-5 w-5 text-green-600" />;
      case "running":
        return <Loader2 className="h-5 w-5 animate-spin text-cyan-600" />;
      case "failed":
        return <XCircle className="h-5 w-5 text-red-600" />;
      default:
        return <Clock className="h-5 w-5 text-slate-400" />;
    }
  };

  const getStatusBadge = (status: AnalysisStatus) => {
    switch (status) {
      case "completed":
        return (
          <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700">
            Completed
          </span>
        );
      case "running":
        return (
          <span className="rounded-full bg-cyan-100 px-3 py-1 text-xs font-medium text-cyan-700">
            Running
          </span>
        );
      case "failed":
        return (
          <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-medium text-red-700">
            Failed
          </span>
        );
      default:
        return (
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
            Pending
          </span>
        );
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 70) return "text-green-600";
    if (score >= 50) return "text-yellow-600";
    return "text-red-600";
  };

  const getScoreBg = (score: number) => {
    if (score >= 70) return "bg-green-500";
    if (score >= 50) return "bg-yellow-500";
    return "bg-red-500";
  };

  return (
    <div className="space-y-6">
      {/* Analysis Modules */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {ANALYSIS_MODULES.map((module) => {
          const result = getAnalysisResult(module.type);
          const isRunning = runningModules.has(module.id) || result?.status === "running";
          const canRun = hasRequiredDocs(module.requiredDocs) && !isRunning;
          const ModuleIcon = module.icon;

          return (
            <div
              key={module.id}
              className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
            >
              {result?.status === "completed" && (
                <div className={`absolute left-0 top-0 h-full w-1 ${getScoreBg(result.score || 0)}`} />
              )}

              <div className="border-b border-slate-100 p-6">
                <div className="flex items-start gap-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-50">
                    <ModuleIcon className="h-5 w-5 text-cyan-700" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-slate-900">{module.name}</h3>
                    <p className="mt-1 text-sm text-slate-500">{module.description}</p>
                  </div>
                </div>
              </div>

              <div className="p-6">
                {result ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(result.status)}
                        {getStatusBadge(result.status)}
                      </div>

                      {result.score !== undefined && (
                        <div className={`text-2xl font-bold ${getScoreColor(result.score)}`}>
                          {result.score}
                        </div>
                      )}
                    </div>

                    {result.summary && (
                      <p className="text-sm text-slate-600">{result.summary}</p>
                    )}

                    <div className="flex items-center justify-between text-xs text-slate-400">
                      <span>Started: {formatDate(result.createdAt)}</span>
                      {result.completedAt && (
                        <span>Completed: {formatDate(result.completedAt)}</span>
                      )}
                    </div>

                    {result.status === "completed" && (
                      <div className="flex gap-2">
                        <button className="flex flex-1 items-center justify-center rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
                          <Eye className="mr-2 h-4 w-4" />
                          View Details
                        </button>

                        <button
                          onClick={() => runAnalysis(module.id, module.type)}
                          className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                        >
                          <RefreshCw className="h-4 w-4" />
                        </button>
                      </div>
                    )}

                    {result.status === "failed" && (
                      <button
                        onClick={() => runAnalysis(module.id, module.type)}
                        className="flex w-full items-center justify-center rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                      >
                        <RefreshCw className="mr-2 h-4 w-4" />
                        Retry Analysis
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="rounded-xl bg-slate-100 p-3">
                      <p className="text-sm text-slate-500">
                        Required documents:{" "}
                        {module.requiredDocs.map((d) => d.replaceAll("_", " ")).join(", ")}
                      </p>
                    </div>

                    <button
                      className="flex w-full items-center justify-center rounded-xl bg-cyan-400 px-4 py-3 text-sm font-medium text-slate-900 hover:bg-cyan-300 disabled:opacity-60"
                      disabled={!canRun}
                      onClick={() => runAnalysis(module.id, module.type)}
                    >
                      {isRunning ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Running Analysis...
                        </>
                      ) : (
                        <>
                          <Play className="mr-2 h-4 w-4" />
                          Run Analysis
                        </>
                      )}
                    </button>

                    {!canRun && !isRunning && (
                      <p className="text-center text-xs text-slate-400">
                        Upload and process required documents first
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Run All */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="font-semibold text-slate-900">Run All Analysis Modules</h3>
            <p className="text-sm text-slate-500">
              Execute all available analysis modules for this case
            </p>
          </div>

          <button className="flex items-center justify-center rounded-xl bg-cyan-400 px-5 py-3 text-sm font-medium text-slate-900 hover:bg-cyan-300">
            <Play className="mr-2 h-4 w-4" />
            Run All Modules
          </button>
        </div>
      </div>

      {/* Analysis History */}
      {analysisResults.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 p-6">
            <h3 className="text-lg font-semibold text-slate-900">Analysis History</h3>
          </div>

          <div className="space-y-3 p-6">
            {[...analysisResults]
              .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
              .map((result) => {
                const analysisModule = ANALYSIS_MODULES.find((m) => m.type === result.type);
                const ModuleIcon = analysisModule?.icon || FileText;

                return (
                  <div
                    key={result.id}
                    className="flex items-center gap-4 rounded-xl border border-slate-200 p-4"
                  >
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 shrink-0">
                      <ModuleIcon className="h-5 w-5 text-slate-500" />
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-slate-900">{analysisModule?.name}</p>
                        {getStatusBadge(result.status)}
                      </div>
                      <p className="text-xs text-slate-400">
                        {formatDate(result.createdAt)}
                      </p>
                    </div>

                    {result.score !== undefined && (
                      <div className={`text-xl font-bold ${getScoreColor(result.score)}`}>
                        {result.score}
                      </div>
                    )}
                  </div>
                );
              })}
          </div>
        </div>
      )}
    </div>
  );
}
