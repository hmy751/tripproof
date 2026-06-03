import { useState } from "react";
import { AppHeader } from "./components/AppHeader";
import { ChatWorkspace } from "./components/ChatWorkspace";
import { DraftListPanel } from "./components/DraftListPanel";
import { LeftRail } from "./components/LeftRail";
import { RecommendationRail } from "./components/RecommendationRail";
import { StaticEmptyView } from "./components/StaticEmptyView";
import { ViewTabs } from "./components/ViewTabs";
import type { ChatMessage, LibraryItem, View } from "./types";

export function App() {
  const [materials] = useState<LibraryItem[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activeView, setActiveView] = useState<View>("ask");
  const [question, setQuestion] = useState("");
  const [toast, setToast] = useState("");

  function flash(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(""), 1800);
  }

  function prepareLibraryInput() {
    flash("아직 자료를 추가할 수 없습니다.");
  }

  function ask(rawQuestion = question) {
    const trimmed = rawQuestion.trim();
    if (!trimmed) return;

    if (materials.length === 0) {
      flash("먼저 자료를 추가해야 자료함에 물어볼 수 있습니다.");
      return;
    }

    const idSeed = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    setMessages((current) => [
      ...current,
      { id: `u-${idSeed}`, role: "user", text: trimmed },
      {
        id: `a-${idSeed}`,
        role: "assistant",
        text: "아직 자료를 읽지 못했습니다. 자료를 추가한 뒤 다시 물어보세요.",
        tone: "blocked",
      },
    ]);
    setQuestion("");
  }

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 antialiased">
      <AppHeader materialCount={materials.length} />

      <main className="mx-auto grid max-w-[1680px] gap-4 px-4 py-5 sm:px-6 lg:grid-cols-[320px_minmax(0,1fr)_320px]">
        <LeftRail
          materials={materials}
          onPrepareLibraryInput={prepareLibraryInput}
        />

        <section className="grid min-w-0 content-start gap-4">
          <ViewTabs activeView={activeView} onChange={setActiveView} />

          {activeView === "ask" ? (
            <>
              <ChatWorkspace
                materialCount={materials.length}
                messages={messages}
                question={question}
                onAsk={ask}
                onQuestionChange={setQuestion}
              />
              <DraftListPanel />
            </>
          ) : null}

          {activeView === "board" ? (
            <StaticEmptyView
              description="원문에서 확인한 정보가 카드로 정리되면 여기에 모입니다."
              title="대시보드가 비어 있습니다"
            />
          ) : null}

          {activeView === "field" ? (
            <StaticEmptyView
              description="현장에서 다시 볼 정보만 따로 저장하면 여기에 모입니다."
              title="현장 카드가 비어 있습니다"
            />
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
