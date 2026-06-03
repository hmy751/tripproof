import { useMemo, useState } from "react";
import type { TravelArtifact, TripFact } from "../shared/tripFacts";
import { AppHeader } from "./components/AppHeader";
import { CandidateRail } from "./components/CandidateRail";
import { ChatWorkspace } from "./components/ChatWorkspace";
import { DashboardView } from "./components/DashboardView";
import { FieldView } from "./components/FieldView";
import { LeftRail } from "./components/LeftRail";
import { ViewTabs } from "./components/ViewTabs";
import { tripSession } from "./data/tripSession";
import type { CardDecision } from "./data/tripSession";
import { findQuestionFactId, metaForFact, sourceNames } from "./lib/tripUi";
import type { ChatMessage, DraftCard, View } from "./types";

const initialThread: ChatMessage[] = [{ id: "m1", role: "ai", kind: "intro" }];

export function App() {
  const [activeView, setActiveView] = useState<View>("ask");
  const [question, setQuestion] = useState("");
  const [thread, setThread] = useState<ChatMessage[]>(initialThread);
  const [draft, setDraft] = useState<DraftCard | null>(null);
  const [decisions, setDecisions] = useState<Record<string, CardDecision>>({});
  const [expandedAnswers, setExpandedAnswers] = useState<Record<string, boolean>>({});
  const [expandedCandidates, setExpandedCandidates] = useState<Record<string, boolean>>({});
  const [toast, setToast] = useState("");

  const factById = useMemo(
    () => new Map(tripSession.facts.map((fact) => [fact.id, fact])),
    [],
  );
  const artifactById = useMemo(
    () => new Map(tripSession.artifacts.map((artifact) => [artifact.id, artifact])),
    [],
  );

  const confirmedCards = Object.values(decisions).filter(
    (decision) => decision.state === "confirmed",
  );
  const fieldCards = confirmedCards.filter((decision) => decision.fieldSaved);

  function flash(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(""), 1800);
  }

  function getFact(factId: string) {
    return factById.get(factId) ?? tripSession.facts[0];
  }

  function ask(rawQuestion = question) {
    const trimmed = rawQuestion.trim();
    if (!trimmed) return;

    const factId = findQuestionFactId(trimmed);
    const idSeed = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    setThread((current) => [
      ...current,
      { id: `u-${idSeed}`, role: "user", text: trimmed },
      { id: `a-${idSeed}`, role: "ai", kind: "answer", factId },
    ]);
    setQuestion("");
    setActiveView("ask");
  }

  function stageFact(factId: string) {
    if (decisions[factId]?.state === "confirmed") {
      flash("이미 대시보드에 올라간 카드입니다.");
      return;
    }

    const fact = getFact(factId);
    const meta = metaForFact(factId);
    const value = fact.value ?? "";
    setDraft({
      factId,
      title: fact.label,
      value,
      category: meta.category,
      phase: meta.phase,
      originalTitle: fact.label,
      originalValue: value,
    });
    setActiveView("ask");
    window.setTimeout(() => {
      document.querySelector("#draft-panel")?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 0);
  }

  function updateDraft<K extends keyof DraftCard>(key: K, value: DraftCard[K]) {
    setDraft((current) => (current ? { ...current, [key]: value } : current));
  }

  function confirmDraft() {
    if (!draft) return;
    const fact = getFact(draft.factId);
    const value = draft.value.trim();
    const title = draft.title.trim();

    if (!value) {
      flash("값을 입력해야 대시보드에 올릴 수 있습니다.");
      return;
    }

    const edited = title !== draft.originalTitle || value !== draft.originalValue;
    const source = fact.evidenceState === "supported" && !edited ? "ai_supported" : "manual";

    setDecisions((current) => ({
      ...current,
      [draft.factId]: {
        factId: draft.factId,
        state: "confirmed",
        source,
        fieldSaved: current[draft.factId]?.fieldSaved ?? false,
        titleOverride: title,
        valueOverride: value,
        category: draft.category,
        phase: draft.phase,
      },
    }));
    setDraft(null);
    setActiveView("board");
    flash("대시보드에 올렸습니다.");
  }

  function toggleFieldSave(factId: string) {
    const current = decisions[factId];
    if (!current || current.state !== "confirmed") return;

    setDecisions((all) => ({
      ...all,
      [factId]: {
        ...current,
        fieldSaved: !current.fieldSaved,
      },
    }));
    flash(current.fieldSaved ? "현장 카드에서 내렸습니다." : "현장 카드로 저장했습니다.");
  }

  function showArtifactHint(artifact: TravelArtifact) {
    flash(`${artifact.name} - 채팅에서 자료명을 멘션해 범위를 좁힐 수 있습니다.`);
  }

  function showEvidenceToast(fact: TripFact) {
    flash(`근거: ${sourceNames(fact, artifactById)}`);
  }

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 antialiased">
      <AppHeader boardCount={confirmedCards.length} fieldCount={fieldCards.length} />

      <main className="mx-auto grid max-w-[1680px] gap-4 px-4 py-5 sm:px-6 lg:grid-cols-[300px_minmax(0,1fr)_340px]">
        <LeftRail
          artifactCount={tripSession.artifacts.length}
          artifacts={tripSession.artifacts}
          boardCount={confirmedCards.length}
          fieldCount={fieldCards.length}
          onArtifactClick={showArtifactHint}
          onAttach={() => flash("자료 첨부 흐름은 다음 slice에서 연결합니다.")}
          onPaste={() => flash("붙여넣기 입력은 다음 slice에서 연결합니다.")}
        />

        <section className="grid min-w-0 content-start gap-4">
          <ViewTabs
            activeView={activeView}
            boardCount={confirmedCards.length}
            fieldCount={fieldCards.length}
            onChange={setActiveView}
          />

          {activeView === "ask" ? (
            <ChatWorkspace
              artifactCount={tripSession.artifacts.length}
              decisions={decisions}
              draft={draft}
              expandedAnswers={expandedAnswers}
              factById={factById}
              question={question}
              thread={thread}
              onAsk={ask}
              onCloseDraft={() => setDraft(null)}
              onConfirmDraft={confirmDraft}
              onDraftChange={updateDraft}
              onQuestionChange={setQuestion}
              onStageFact={stageFact}
              onToggleEvidence={(messageId) =>
                setExpandedAnswers((current) => ({ ...current, [messageId]: !current[messageId] }))
              }
            />
          ) : null}

          {activeView === "board" ? (
            <DashboardView
              decisions={confirmedCards}
              factById={factById}
              onShowEvidence={(factId) => showEvidenceToast(getFact(factId))}
              onToggleFieldSave={toggleFieldSave}
            />
          ) : null}

          {activeView === "field" ? (
            <FieldView decisions={fieldCards} factById={factById} onOpenBoard={() => setActiveView("board")} />
          ) : null}
        </section>

        <CandidateRail
          decisions={decisions}
          expandedCandidates={expandedCandidates}
          factById={factById}
          onAskCandidate={(factId) => ask(metaForFact(factId).question)}
          onStageFact={stageFact}
          onToggleEvidence={(factId) =>
            setExpandedCandidates((current) => ({ ...current, [factId]: !current[factId] }))
          }
        />
      </main>

      <div
        aria-live="polite"
        className={`fixed bottom-5 left-1/2 z-40 -translate-x-1/2 rounded-lg bg-slate-950 px-4 py-3 text-sm font-medium text-white shadow-lg transition ${
          toast ? "translate-y-0 opacity-100" : "pointer-events-none translate-y-2 opacity-0"
        }`}
      >
        {toast}
      </div>
    </div>
  );
}

export default App;
