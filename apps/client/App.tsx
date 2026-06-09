import { useEffect, useMemo, useState } from "react";
import { ApiError } from "./api/http";
import { fetchMaterials, uploadMaterial } from "./api/materials";
import { askQuestion } from "./api/questions";
import { canConfirmDraft, createDashboardCardFromDraft, markCardForField } from "./cards";
import { createDraftFromAnswerItem, markDraftAsManual } from "./drafts";
import { AppHeader } from "./components/AppHeader";
import { CardCollectionPanel } from "./components/CardCollectionPanel";
import { ChatWorkspace } from "./components/ChatWorkspace";
import { DraftListPanel } from "./components/DraftListPanel";
import { LeftRail } from "./components/LeftRail";
import { RecommendationRail } from "./components/RecommendationRail";
import { ViewTabs } from "./components/ViewTabs";
import type { CardDraft, ChatAnswerItem, ChatMessage, DashboardCard, LibraryItem, View } from "./types";

export function App() {
  const [materials, setMaterials] = useState<LibraryItem[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [drafts, setDrafts] = useState<CardDraft[]>([]);
  const [dashboardCards, setDashboardCards] = useState<DashboardCard[]>([]);
  const [activeView, setActiveView] = useState<View>("ask");
  const [question, setQuestion] = useState("");
  const [toast, setToast] = useState("");
  const [isUploading, setIsUploading] = useState(false);

  const readyMaterials = useMemo(() => materials.filter((material) => material.status === "ready"), [materials]);
  const fieldCards = useMemo(() => dashboardCards.filter((card) => card.fieldSavedAt), [dashboardCards]);

  useEffect(() => {
    fetchMaterials()
      .then(setMaterials)
      .catch((error: unknown) => {
        flash(error instanceof ApiError ? error.message : "자료함을 불러오지 못했습니다.");
      });
  }, []);

  function flash(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(""), 1800);
  }

  async function addMaterial(file: File) {
    setIsUploading(true);
    try {
      const material = await uploadMaterial(file);
      setMaterials((current) => [...current, material]);
      flash(material.status === "ready" ? "PDF를 읽었습니다." : material.error ?? "PDF를 읽지 못했습니다.");
    } catch (error) {
      flash(error instanceof ApiError ? error.message : "PDF를 추가하지 못했습니다.");
    } finally {
      setIsUploading(false);
    }
  }

  async function ask(rawQuestion = question) {
    const trimmed = rawQuestion.trim();
    if (!trimmed) return;

    if (readyMaterials.length === 0) {
      flash("읽기 완료된 자료가 필요합니다.");
      return;
    }

    const idSeed = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    setMessages((current) => [
      ...current,
      { id: `u-${idSeed}`, role: "user", text: trimmed },
    ]);
    setQuestion("");

    try {
      const response = await askQuestion(
        trimmed,
        readyMaterials.map((material) => material.id),
      );
      setMessages((current) => [
        ...current,
        {
          id: `a-${idSeed}`,
          role: "assistant",
          text: response.message,
          meta:
            response.status === "accepted"
              ? `자료 ${response.materialCount}개 · ${response.pageCount}쪽 · ${response.charCount.toLocaleString()}자`
              : undefined,
          answer: response.answer,
          tone: response.status === "blocked" ? "blocked" : "neutral",
        },
      ]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: `a-${idSeed}`,
          role: "assistant",
          text: error instanceof ApiError ? error.message : "질문을 처리하지 못했습니다.",
          tone: "blocked",
        },
      ]);
    }
  }

  function addDraftFromAnswer(message: ChatMessage, item: ChatAnswerItem) {
    const draftId = `${message.id}-${item.id}`;
    setDrafts((current) => {
      if (current.some((draft) => draft.id === draftId)) return current;
      return [...current, createDraftFromAnswerItem({ id: draftId, item })];
    });
  }

  function updateDraft(id: string, field: "schedule" | "title" | "value", value: string) {
    setDrafts((current) =>
      current.map((draft) =>
        draft.id === id
          ? {
              ...markDraftAsManual(draft),
              [field]: value,
            }
          : draft,
      ),
    );
  }

  function removeDraft(id: string) {
    setDrafts((current) => current.filter((draft) => draft.id !== id));
  }

  function confirmDraft(id: string) {
    const draft = drafts.find((candidate) => candidate.id === id);
    if (!draft) return;

    if (!canConfirmDraft(draft)) {
      flash("이름과 값을 입력해야 대시보드에 올릴 수 있습니다.");
      return;
    }

    const card = createDashboardCardFromDraft({ draft, id: `card-${draft.id}` });
    setDashboardCards((current) => {
      if (current.some((candidate) => candidate.draftId === draft.id)) return current;
      return [...current, card];
    });
    setDrafts((current) => current.filter((candidate) => candidate.id !== draft.id));
    flash("대시보드에 올렸습니다.");
  }

  function saveCardForField(id: string) {
    setDashboardCards((current) => current.map((card) => (card.id === id ? markCardForField(card) : card)));
    flash("현장 카드에 저장했습니다.");
  }

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 antialiased">
      <AppHeader materialCount={materials.length} />

      <main className="mx-auto grid max-w-[1680px] gap-4 px-4 py-5 sm:px-6 lg:grid-cols-[320px_minmax(0,1fr)_320px]">
        <LeftRail
          materials={materials}
          isUploading={isUploading}
          onUploadMaterial={addMaterial}
        />

        <section className="grid min-w-0 content-start gap-4">
          <ViewTabs activeView={activeView} onChange={setActiveView} />

          {activeView === "ask" ? (
            <>
              <ChatWorkspace
                materialCount={readyMaterials.length}
                messages={messages}
                onCreateDraft={addDraftFromAnswer}
                question={question}
                onAsk={ask}
                onQuestionChange={setQuestion}
              />
              <DraftListPanel
                drafts={drafts}
                onClearDrafts={() => setDrafts([])}
                onConfirmDraft={confirmDraft}
                onRemoveDraft={removeDraft}
                onUpdateDraft={updateDraft}
              />
            </>
          ) : null}

          {activeView === "board" ? (
            <CardCollectionPanel cards={dashboardCards} onSaveForField={saveCardForField} view="board" />
          ) : null}

          {activeView === "field" ? (
            <CardCollectionPanel cards={fieldCards} view="field" />
          ) : null}
        </section>

        <RecommendationRail materialCount={materials.length} />
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
