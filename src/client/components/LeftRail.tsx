import { Clipboard, Upload } from "lucide-react";
import type { TravelArtifact } from "../../shared/tripFacts";
import { artifactSummaries } from "../data/tripSession";
import { kindLabel } from "../lib/tripUi";
import { Button, Panel, PanelHeader } from "./ui";

export function LeftRail({
  artifactCount,
  artifacts,
  boardCount,
  fieldCount,
  onArtifactClick,
  onAttach,
  onPaste,
}: {
  artifactCount: number;
  artifacts: TravelArtifact[];
  boardCount: number;
  fieldCount: number;
  onArtifactClick: (artifact: TravelArtifact) => void;
  onAttach: () => void;
  onPaste: () => void;
}) {
  return (
    <aside className="grid content-start gap-4 lg:sticky lg:top-20">
      <Panel>
        <div className="p-4">
          <div className="text-xl font-extrabold text-slate-950">오사카 4박 5일</div>
          <div className="mt-1 text-sm text-slate-500">자료함 기반 확인 중 · 출발 D-3</div>
          <div className="mt-4 grid grid-cols-3 gap-2">
            <Metric value={artifactCount} label="자료" />
            <Metric value={boardCount} label="올린 카드" />
            <Metric value={fieldCount} label="현장" />
          </div>
          <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
            <Button block onClick={onAttach} variant="primary">
              <Upload size={16} />
              자료 첨부
            </Button>
            <Button block onClick={onPaste}>
              <Clipboard size={16} />
              붙여넣기
            </Button>
          </div>
        </div>
      </Panel>

      <Panel>
        <PanelHeader aside={<span className="text-xs font-medium text-slate-500">근거 원천</span>}>
          <h2 className="text-sm font-bold text-slate-950">자료함</h2>
        </PanelHeader>
        <div className="grid gap-1 p-2">
          {artifacts.map((artifact) => (
            <button
              className="flex min-w-0 items-start gap-3 rounded-md px-2 py-2.5 text-left transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              key={artifact.id}
              onClick={() => onArtifactClick(artifact)}
            >
              <span className="mt-0.5 inline-flex h-7 min-w-10 items-center justify-center rounded bg-slate-900 px-2 font-mono text-[11px] font-bold text-white">
                {kindLabel(artifact)}
              </span>
              <span className="min-w-0">
                <strong className="block truncate text-sm text-slate-900">{artifact.name}</strong>
                <span className="block truncate text-xs text-slate-500">{artifactSummaries[artifact.id] ?? artifact.fileName}</span>
              </span>
            </button>
          ))}
        </div>
      </Panel>
    </aside>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 px-2 py-3 text-center">
      <strong className="block text-lg leading-none text-slate-950">{value}</strong>
      <span className="mt-1 block text-xs text-slate-500">{label}</span>
    </div>
  );
}
