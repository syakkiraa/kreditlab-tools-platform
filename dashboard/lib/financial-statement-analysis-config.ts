export const financialStatementAnalysisSection = {
  id: "financial-statement-analysis",
  label: "Financial Statement Analysis",
  convertAction: "/api/convert-financial-pdf",
  action: "/api/run-financial-analysis",
  tool: {
    id: "financial-statement",
    analysisType: "financial_statement",
    displayName: "Financial Statement Analyzer",
    supportedExtensions: [".pdf", ".txt", ".md", ".json"],
    accept:
      ".pdf,.txt,.md,.json,application/pdf,text/plain,text/markdown,application/json",
  },
} as const;
