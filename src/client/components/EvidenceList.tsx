import type { TripFact } from "../../shared/tripFacts";
import { tripSession } from "../data/tripSession";
import { kindLabel } from "../lib/tripUi";
import { cx } from "./ui";

export function EvidenceList({ compact = false, fact }: { compact?: boolean; fact: TripFact }) {
  if (fact.evidence.length === 0) {
    return (
      <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
        이 답변에는 자료 근거가 없습니다. 직접 확인이 필요해요.
      </div>
    );
  }

  return (
    <div className={cx("grid gap-2", compact ? "mt-2" : "mt-3")}>
      {fact.evidence.map((ref) => {
        const artifact = tripSession.artifacts.find((item) => item.id === ref.artifactId);
        return (
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3" key={`${ref.artifactId}-${ref.locator}`}>
            <div className="flex items-start gap-2">
              <span className="mt-0.5 inline-flex h-6 min-w-9 items-center justify-center rounded bg-slate-900 px-1.5 font-mono text-[11px] font-bold text-white">
                {artifact ? kindLabel(artifact) : "DOC"}
              </span>
              <div className="min-w-0">
                <strong className="block truncate text-sm text-slate-900">{artifact?.name ?? ref.label}</strong>
                <span className="block truncate text-xs text-slate-500">{ref.locator}</span>
              </div>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">{ref.snippet}</p>
          </div>
        );
      })}
    </div>
  );
}
