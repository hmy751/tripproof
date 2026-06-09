import { useEffect, useMemo, useState } from "react";
import { ApiError } from "./api/http";
import { fetchMaterials, uploadMaterial } from "./api/materials";
import { askQuestion } from "./api/questions";
import { AppHeader } from "./components/AppHeader";
import { ChatWorkspace } from "./components/ChatWorkspace";
import { DraftListPanel } from "./components/DraftListPanel";
import { LeftRail } from "./components/LeftRail";
import { RecommendationRail } from "./components/RecommendationRail";
import { StaticEmptyView } from "./components/StaticEmptyView";
import { ViewTabs } from "./components/ViewTabs";
import type { ChatMessage, LibraryItem, View } from "./types";

export function App() {
  const [materials, setMaterials] = useState<LibraryItem[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activeView, setActiveView] = useState<View>("ask");
  const [question, setQuestion] = useState("");
  const [toast, setToast] = useState("");
  const [isUploading, setIsUploading] = useState(false);

  const readyMaterials = useMemo(() => materials.filter((material) => material.status === "ready"), [materials]);

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
          excerpt: response.excerpt,
          facts: response.facts,
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
