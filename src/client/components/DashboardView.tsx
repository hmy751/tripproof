import { Eye, MapPin } from "lucide-react";
import type { TripFact } from "../../shared/tripFacts";
import { categoryThemes, phases } from "../data/tripSession";
import type { CardDecision } from "../data/tripSession";
import { Button, Panel, PanelHeader, Pill, SourcePill, cx } from "./ui";

export function DashboardView({
  decisions,
  factById,
  onShowEvidence,
  onToggleFieldSave,
}: {
  decisions: CardDecision[];
  factById: Map<string, TripFact>;
  onShowEvidence: (factId: string) => void;
  onToggleFieldSave: (factId: string) => void;
}) {
  return (
    <Panel>
      <PanelHeader aside={<Pill className="border-emerald-200 bg-emerald-50 text-emerald-700">{decisions.length}</Pill>}>
        <h2 className="text-sm font-bold text-slate-950">최종 대시보드</h2>
        <p className="mt-0.5 text-xs text-slate-500">사람이 올린 카드만 · 일정 순서로</p>
      </PanelHeader>
      <div className="p-4">
        {decisions.length === 0 ? (
          <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center">
            <strong className="block text-sm text-slate-900">아직 올린 카드가 없습니다</strong>
            <p className="mt-1 text-sm text-slate-500">초안을 확정하면 일정 순서로 쌓입니다.</p>
          </div>
        ) : (
          <div className="grid gap-6">
            {phases
              .filter((phase) => decisions.some((decision) => decision.phase === phase.key))
              .map((phase, index, usedPhases) => {
                const phaseCards = decisions.filter((decision) => decision.phase === phase.key);
                const categories = Array.from(new Set(phaseCards.map((decision) => decision.category)));
                return (
                  <div className="grid grid-cols-[24px_minmax(0,1fr)] gap-3" key={phase.key}>
                    <div className="relative flex justify-center">
                      <span className="mt-1 h-3 w-3 rounded-full bg-slate-950" />
                      {index === usedPhases.length - 1 ? null : <span className="absolute top-5 bottom-[-25px] w-px bg-slate-200" />}
                    </div>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-end justify-between gap-2">
                        <h3 className="text-base font-extrabold text-slate-950">{phase.label}</h3>
                        <span className="text-xs font-medium text-slate-500">{phase.when}</span>
                      </div>
                      <div className="mt-3 grid gap-4">
                        {categories.map((category) => {
                          const theme = categoryThemes[category];
                          return (
                            <div key={category}>
                              <div className="mb-2 flex items-center gap-2 text-xs font-bold text-slate-500">
                                <span className={cx("h-2 w-2 rounded-full", theme.dot)} />
                                {category}
                              </div>
                              <div className="grid gap-3 md:grid-cols-2">
                                {phaseCards
                                  .filter((decision) => decision.category === category)
                                  .map((decision) => {
                                    const fact = factById.get(decision.factId);
                                    if (!fact) return null;
                                    return (
                                      <BoardCard
                                        decision={decision}
                                        fact={fact}
                                        key={decision.factId}
                                        onShowEvidence={onShowEvidence}
                                        onToggleFieldSave={onToggleFieldSave}
                                      />
                                    );
                                  })}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                );
              })}
          </div>
        )}
      </div>
    </Panel>
  );
}

function BoardCard({
  decision,
  fact,
  onShowEvidence,
  onToggleFieldSave,
}: {
  decision: CardDecision;
  fact: TripFact;
  onShowEvidence: (factId: string) => void;
  onToggleFieldSave: (factId: string) => void;
}) {
  return (
    <article className={cx("rounded-lg border bg-white p-4", decision.fieldSaved ? "border-violet-200 ring-2 ring-violet-100" : "border-slate-200")}>
      <div className="flex items-start justify-between gap-3">
        <h4 className="min-w-0 text-sm font-bold text-slate-950">{decision.titleOverride || fact.label}</h4>
        <div className="flex shrink-0 flex-wrap justify-end gap-1.5">
          <SourcePill source={decision.source} />
          {decision.fieldSaved ? <Pill className="border-violet-200 bg-violet-50 text-violet-700">현장 저장</Pill> : null}
        </div>
      </div>
      <div className="mt-3 text-lg font-extrabold text-slate-950">{decision.valueOverride || fact.value || "-"}</div>
      <div className="mt-4 flex flex-wrap justify-end gap-2">
        <Button disabled={fact.evidence.length === 0} onClick={() => onShowEvidence(fact.id)} size="sm" variant="ghost">
          <Eye size={14} />
          {fact.evidence.length ? "근거" : "근거 없음"}
        </Button>
        <Button onClick={() => onToggleFieldSave(fact.id)} size="sm" variant={decision.fieldSaved ? "secondary" : "primary"}>
          <MapPin size={14} />
          {decision.fieldSaved ? "저장됨" : "현장 저장"}
        </Button>
      </div>
    </article>
  );
}
