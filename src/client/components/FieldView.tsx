import { Library } from "lucide-react";
import type { TripFact } from "../../shared/tripFacts";
import { categoryThemes, phases } from "../data/tripSession";
import type { CardDecision } from "../data/tripSession";
import { Button, Pill, SourcePill, cx } from "./ui";

export function FieldView({
  decisions,
  factById,
  onOpenBoard,
}: {
  decisions: CardDecision[];
  factById: Map<string, TripFact>;
  onOpenBoard: () => void;
}) {
  if (decisions.length === 0) {
    return (
      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-extrabold text-slate-950">현장 카드</h3>
            <p className="mt-1 text-sm text-slate-500">대시보드에서 저장한 것만 · 현장에서 빠르게 보기</p>
          </div>
          <Button onClick={onOpenBoard}>
            <Library size={16} />
            대시보드
          </Button>
        </div>
        <div className="mt-5 rounded-md border border-dashed border-slate-300 bg-slate-50 px-4 py-10 text-center">
          <strong className="block text-sm text-slate-900">현장 카드가 비어 있습니다</strong>
          <p className="mt-1 text-sm text-slate-500">대시보드에서 '현장 저장'을 누른 카드만 여기에 모입니다.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-extrabold text-slate-950">현장 카드</h3>
          <p className="mt-1 text-sm text-slate-500">대시보드에서 저장한 것만 · 현장에서 빠르게 보기</p>
        </div>
        <Pill className="border-violet-200 bg-violet-50 text-violet-700">{decisions.length}</Pill>
      </div>

      <div className="mt-5 grid gap-5">
        {phases
          .filter((phase) => decisions.some((decision) => decision.phase === phase.key))
          .map((phase) => (
            <div key={phase.key}>
              <h4 className="mb-2 text-sm font-bold text-slate-600">
                {phase.label} · {phase.when}
              </h4>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {decisions
                  .filter((decision) => decision.phase === phase.key)
                  .map((decision) => {
                    const fact = factById.get(decision.factId);
                    if (!fact) return null;
                    const theme = categoryThemes[decision.category];
                    return (
                      <article className={cx("rounded-lg border bg-white p-4 ring-2", theme.ring, "border-slate-200")} key={decision.factId}>
                        <div className="flex items-center justify-between gap-2">
                          <span className="flex items-center gap-2 text-xs font-bold text-slate-500">
                            <span className={cx("h-2 w-2 rounded-full", theme.dot)} />
                            {decision.category}
                          </span>
                          <SourcePill source={decision.source} />
                        </div>
                        <span className="mt-4 block text-sm font-semibold text-slate-500">{decision.titleOverride || fact.label}</span>
                        <span className="mt-1 block text-2xl font-extrabold text-slate-950">{decision.valueOverride || fact.value || "-"}</span>
                      </article>
                    );
                  })}
              </div>
            </div>
          ))}
      </div>
    </section>
  );
}
