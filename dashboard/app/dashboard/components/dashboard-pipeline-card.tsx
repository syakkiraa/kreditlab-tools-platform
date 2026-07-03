import {
  formatCompactCurrency,
  type DashboardPipelineStage,
} from "../dashboard-types";

type DashboardPipelineCardProps = {
  title: string;
  subtitle: string;
  stages: DashboardPipelineStage[];
};

export function DashboardPipelineCard({
  title,
  subtitle,
  stages,
}: DashboardPipelineCardProps) {
  const maxCount = Math.max(...stages.map((stage) => stage.count), 1);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-6">
        <h2 className="font-semibold text-slate-900">{title}</h2>
        <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
      </div>

      <div className="space-y-4">
        {stages.map((stage) => {
          const width = `${(stage.count / maxCount) * 100}%`;

          return (
            <div key={stage.name}>
              <div className="mb-1 flex items-center justify-between gap-4 text-sm">
                <span className="font-medium text-slate-800">{stage.name}</span>
                <span className="text-slate-500">
                  {stage.count} ({formatCompactCurrency(stage.value)})
                </span>
              </div>

              <div className="h-2 rounded-full bg-slate-200">
                <div
                  className="h-2 rounded-full bg-teal-400 transition-[width]"
                  style={{ width }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
