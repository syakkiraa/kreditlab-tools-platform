"use client";

type ReportPreviewFrameProps = {
  html: string;
  title: string;
  className?: string;
  iframeClassName?: string;
};

export function ReportPreviewFrame({
  html,
  title,
  className = "",
  iframeClassName = "h-[900px]",
}: ReportPreviewFrameProps) {
  return (
    <div
      className={`overflow-hidden rounded-xl border border-slate-200 bg-white ${className}`}
    >
      <iframe
        title={title}
        srcDoc={html}
        sandbox="allow-scripts allow-forms allow-popups allow-downloads allow-modals"
        referrerPolicy="no-referrer"
        className={`w-full border-0 bg-white ${iframeClassName}`}
      />
    </div>
  );
}
