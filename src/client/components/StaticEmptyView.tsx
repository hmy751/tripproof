import { ClipboardList } from "lucide-react";
import { Panel, PanelHeader } from "./ui";

export function StaticEmptyView({
  description,
  title,
}: {
  description: string;
  title: string;
}) {
  return (
    <Panel>
      <PanelHeader>
        <h1 className="text-sm font-bold text-slate-950">{title}</h1>
        <p className="mt-0.5 text-xs text-slate-500">사용자가 확인한 정보만 표시됩니다</p>
      </PanelHeader>
      <div className="p-4">
        <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-4 py-12 text-center">
          <ClipboardList className="mx-auto text-slate-400" size={36} />
          <strong className="mt-4 block text-base text-slate-950">{title}</strong>
          <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">{description}</p>
        </div>
      </div>
    </Panel>
  );
}
