import { Eye, MessageSquare } from "lucide-react";
import type { TripFact } from "../../shared/tripFacts";
import { candidateCards, categoryThemes } from "../data/tripSession";
import type { CardDecision } from "../data/tripSession";
import { EvidenceList } from "./EvidenceList";
import { Button, EvidencePill, Panel, PanelHeader, Pill, cx } from "./ui";

export function CandidateRail({
  decisions,
  expandedCandidates,
  factById,
  onAskCandidate,
  onStageFact,
  onToggleEvidence,
}: {
  decisions: Record<string, CardDecision>;
  expandedCandidates: Record<string, boolean>;
  factById: Map<string, TripFact>;
  onAskCandidate: (factId: string) => void;
  onStageFact: (factId: string) => void;
  onToggleEvidence: (factId: string) => void;
}) {
  return (
    <aside className="grid content-start gap-4 lg:sticky lg:top-20">
      <Panel>
        <PanelHeader aside={<Pill className="border-amber-200 bg-amber-50 text-amber-800">{candidateCards.length}</Pill>}>
          <h2 className="text-sm font-bold text-slate-950">AI 추천 후보</h2>
          <p className="mt-0.5 text-xs text-slate-500">채팅으로 보내거나 바로 초안</p>
        </PanelHeader>
        <div className="grid gap-3 p-3">
          {candidateCards.map((candidate) => {
            const fact = factById.get(candidate.factId);
            if (!fact) return null;
            const confirmed = decisions[fact.id]?.state === "confirmed";
            const expanded = Boolean(expandedCandidates[fact.id]);
            const theme = categoryThemes[candidate.category];

            return (
              <article className="rounded-md border border-slate-200 bg-slate-50 p-3" key={candidate.factId}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
                      <span className={cx("h-2 w-2 rounded-full", theme.dot)} />
                      {candidate.category}
                    </div>
                    <h3 className="mt-1 truncate text-sm font-bold text-slate-950">{fact.label}</h3>
                  </div>
                  <EvidencePill state={fact.evidenceState} />
                </div>
                <p className="mt-2 text-sm font-semibold text-slate-800">{fact.value ?? "값 미정 · 직접 확인"}</p>
                <p className="mt-1 text-xs leading-5 text-slate-500">{candidate.note}</p>
                {expanded ? <EvidenceList compact fact={fact} /> : null}
                <div className="mt-3 flex flex-wrap gap-1.5">
                  <Button onClick={() => onToggleEvidence(fact.id)} size="sm" variant="ghost">
                    <Eye size={14} />
                    {expanded ? "접기" : "근거"}
                  </Button>
                  <Button onClick={() => onAskCandidate(fact.id)} size="sm" variant="ghost">
                    <MessageSquare size={14} />
                    채팅
                  </Button>
                  <Button
                    disabled={confirmed}
                    onClick={() => onStageFact(fact.id)}
                    size="sm"
                    variant={fact.evidenceState === "supported" ? "primary" : "secondary"}
                  >
                    {confirmed ? "올림" : "초안"}
                  </Button>
                </div>
              </article>
            );
          })}
        </div>
      </Panel>
    </aside>
  );
}
