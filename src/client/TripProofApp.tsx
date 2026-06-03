import {
  AlertTriangle,
  Check,
  Clipboard,
  Eye,
  Library,
  MapPin,
  MessageSquare,
  Save,
  Send,
  ShieldAlert,
  Upload,
  X,
} from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import type { EvidenceState, TravelArtifact, TripFact } from "../shared/tripFacts";
import {
  artifactNotes,
  candidateMeta,
  categoryColors,
  demoTrip,
  extraQuestionMatches,
  phases,
  type CardDecision,
  type Category,
  type PhaseKey,
} from "./demoTrip";

type View = "ask" | "board" | "field";

type ChatMessage =
  | { id: string; role: "ai"; kind: "intro" }
  | { id: string; role: "user"; text: string }
  | { id: string; role: "ai"; kind: "answer"; factId: string };

type DraftCard = {
  factId: string;
  title: string;
  value: string;
  category: Category;
  phase: PhaseKey;
  originalTitle: string;
  originalValue: string;
};

const evidenceLabels: Record<EvidenceState, string> = {
  supported: "근거 있음",
  needs_review: "확인 필요",
  missing: "근거 부족",
  conflict: "자료 충돌",
};

const evidenceTone: Record<EvidenceState, "good" | "warn" | "danger"> = {
  supported: "good",
  needs_review: "warn",
  missing: "danger",
  conflict: "warn",
};

const sourceLabels: Record<CardDecision["source"], string> = {
  ai_supported: "근거 있음",
  manual: "직접 확인",
};

const sourceTone: Record<CardDecision["source"], "good" | "user"> = {
  ai_supported: "good",
  manual: "user",
};

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
    () => new Map(demoTrip.facts.map((fact) => [fact.id, fact])),
    [],
  );
  const artifactById = useMemo(
    () => new Map(demoTrip.artifacts.map((artifact) => [artifact.id, artifact])),
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
    return factById.get(factId) ?? demoTrip.facts[0];
  }

  function findQuestionFactId(rawQuestion: string) {
    const trimmed = rawQuestion.trim();
    if (extraQuestionMatches[trimmed]) return extraQuestionMatches[trimmed];

    const exact = candidateMeta.find((candidate) => candidate.question === trimmed);
    if (exact) return exact.factId;

    const normalized = trimmed.replace(/\s/g, "");
    if (normalized.includes("체크인") && normalized.includes("몇시")) return "checkin-time";
    if (normalized.includes("늦") && normalized.includes("호텔")) return "late-arrival";
    if (normalized.includes("바우처") || normalized.includes("프린트")) return "mobile-voucher";
    if (normalized.includes("렌터카") || normalized.includes("기름")) return "fuel-policy";
    if (normalized.includes("영수증") || normalized.includes("도시세")) return "city-tax";
    if (normalized.includes("출입") || normalized.includes("코드")) return "door-code";
    if (normalized.includes("환불") || normalized.includes("지각")) return "late-tour-refund";
    return "late-tour-refund";
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

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="mark">TP</div>
          <div>
            <strong>TripProof</strong>
            <span>자료에 묻고, 근거 있는 답변만 남깁니다</span>
          </div>
        </div>
        <select aria-label="여행 선택" defaultValue="osaka">
          <option value="osaka">오사카 4박 5일 · 출발 D-3</option>
          <option value="tokyo">도쿄 체크인 테스트 여행</option>
        </select>
        <span className="spacer" />
        <div className="counters">
          <span className="pill info">자료 {demoTrip.artifacts.length}</span>
          <span className="pill warn">후보 {candidateMeta.length}</span>
          <span className="pill good">대시보드 {confirmedCards.length}</span>
          <span className="pill saved">현장 {fieldCards.length}</span>
        </div>
      </header>

      <main className="layout">
        <aside className="rail">
          <TripSummary
            artifactCount={demoTrip.artifacts.length}
            boardCount={confirmedCards.length}
            fieldCount={fieldCards.length}
            onAttach={() => flash("자료 첨부 흐름은 다음 slice에서 연결합니다.")}
            onPaste={() => flash("붙여넣기 입력은 다음 slice에서 연결합니다.")}
          />
          <LibraryPanel
            artifacts={demoTrip.artifacts}
            onArtifactClick={(artifact) => flash(`${artifact.name} — 채팅에서 자료명을 멘션해 범위를 좁힐 수 있습니다.`)}
          />
        </aside>

        <section className="main">
          <nav className="tabs" aria-label="TripProof 화면">
            <TabButton active={activeView === "ask"} onClick={() => setActiveView("ask")}>
              확인 (채팅)
            </TabButton>
            <TabButton active={activeView === "board"} onClick={() => setActiveView("board")}>
              대시보드 <span className="badge">{confirmedCards.length}</span>
            </TabButton>
            <TabButton active={activeView === "field"} onClick={() => setActiveView("field")}>
              현장 <span className="badge">{fieldCards.length}</span>
            </TabButton>
          </nav>

          {activeView === "ask" ? (
            <div className="view active">
              <ChatPanel
                artifactCount={demoTrip.artifacts.length}
                decisions={decisions}
                expandedAnswers={expandedAnswers}
                factById={factById}
                question={question}
                thread={thread}
                onAsk={ask}
                onQuestionChange={setQuestion}
                onStageFact={stageFact}
                onToggleEvidence={(messageId) =>
                  setExpandedAnswers((current) => ({ ...current, [messageId]: !current[messageId] }))
                }
              />
              <DraftPanel
                draft={draft}
                fact={draft ? getFact(draft.factId) : null}
                onClose={() => setDraft(null)}
                onConfirm={confirmDraft}
                onDraftChange={updateDraft}
              />
            </div>
          ) : null}

          {activeView === "board" ? (
            <DashboardView
              decisions={confirmedCards}
              factById={factById}
              onShowEvidence={(factId) => flash(`근거: ${sourceNames(getFact(factId), artifactById)}`)}
              onToggleFieldSave={toggleFieldSave}
            />
          ) : null}

          {activeView === "field" ? (
            <FieldView decisions={fieldCards} factById={factById} onOpenBoard={() => setActiveView("board")} />
          ) : null}
        </section>

        <aside className="rail right">
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
        </aside>
      </main>

      <div className={`toast ${toast ? "show" : ""}`} aria-live="polite">
        {toast}
      </div>
    </div>
  );
}

function TripSummary({
  artifactCount,
  boardCount,
  fieldCount,
  onAttach,
  onPaste,
}: {
  artifactCount: number;
  boardCount: number;
  fieldCount: number;
  onAttach: () => void;
  onPaste: () => void;
}) {
  return (
    <section className="card-box">
      <div className="box-body">
        <div className="trip-name">오사카 4박 5일</div>
        <div className="trip-sub">자료함 기반 확인 중 · 출발 D-3</div>
        <div className="mini-stats">
          <div>
            <strong>{artifactCount}</strong>
            <span>자료</span>
          </div>
          <div>
            <strong>{boardCount}</strong>
            <span>올린 카드</span>
          </div>
          <div>
            <strong>{fieldCount}</strong>
            <span>현장</span>
          </div>
        </div>
        <div className="add-row">
          <button className="btn primary block" onClick={onAttach}>
            <Upload size={16} />
            자료 첨부
          </button>
          <button className="btn" onClick={onPaste}>
            <Clipboard size={16} />
            붙여넣기
          </button>
        </div>
      </div>
    </section>
  );
}

function LibraryPanel({
  artifacts,
  onArtifactClick,
}: {
  artifacts: TravelArtifact[];
  onArtifactClick: (artifact: TravelArtifact) => void;
}) {
  return (
    <section className="card-box">
      <div className="box-head">
        <h2>자료함</h2>
        <span className="sub">근거의 원천</span>
      </div>
      <div className="box-body">
        <div className="lib-list">
          {artifacts.map((artifact) => (
            <button className="lib-item" key={artifact.id} onClick={() => onArtifactClick(artifact)}>
              <span className="file-badge">{kindLabel(artifact)}</span>
              <span>
                <strong>{artifact.name}</strong>
                <span>{artifactNotes[artifact.id] ?? artifact.fileName}</span>
              </span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

function TabButton({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button className={`tab ${active ? "active" : ""}`} onClick={onClick}>
      {children}
    </button>
  );
}

function ChatPanel({
  artifactCount,
  decisions,
  expandedAnswers,
  factById,
  question,
  thread,
  onAsk,
  onQuestionChange,
  onStageFact,
  onToggleEvidence,
}: {
  artifactCount: number;
  decisions: Record<string, CardDecision>;
  expandedAnswers: Record<string, boolean>;
  factById: Map<string, TripFact>;
  question: string;
  thread: ChatMessage[];
  onAsk: (question?: string) => void;
  onQuestionChange: (value: string) => void;
  onStageFact: (factId: string) => void;
  onToggleEvidence: (messageId: string) => void;
}) {
  return (
    <section className="card-box chat-box">
      <div className="scope-row">
        대상: <strong>전체 자료함 ({artifactCount}개)</strong> · 자료를 멘션하면 좁혀서 물어볼 수 있어요
      </div>
      <div className="thread">
        {thread.map((message) => {
          if (message.role === "user") {
            return (
              <div className="msg user" key={message.id}>
                <div className="bubble-user">{message.text}</div>
              </div>
            );
          }

          if (message.kind === "intro") {
            return (
              <div className="msg msg-ai" key={message.id}>
                <AiWho />
                <div className="answer intro-answer">
                  <div className="answer-body">
                    자료 {artifactCount}개를 읽었어요. 오른쪽 <strong>추천 후보</strong>를 채팅으로 보내거나 바로 카드 초안으로 만들 수 있고, 아래에 직접 물어봐도 됩니다. 답변에는 근거와 상태가 함께 붙어요.
                  </div>
                </div>
              </div>
            );
          }

          const fact = factById.get(message.factId);
          if (!fact) return null;

          return (
            <ChatAnswer
              confirmed={decisions[fact.id]?.state === "confirmed"}
              expanded={Boolean(expandedAnswers[message.id])}
              fact={fact}
              key={message.id}
              messageId={message.id}
              onStageFact={onStageFact}
              onToggleEvidence={onToggleEvidence}
            />
          );
        })}
      </div>
      <div className="composer">
        <textarea
          aria-label="이번 여행 자료에 질문"
          placeholder="이번 여행 자료에 대해 물어보세요 (예: 호텔에 늦게 도착하면?)"
          value={question}
          onChange={(event) => onQuestionChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              onAsk();
            }
          }}
        />
        <button className="btn primary" onClick={() => onAsk()}>
          <Send size={16} />
          물어보기
        </button>
      </div>
    </section>
  );
}

function ChatAnswer({
  confirmed,
  expanded,
  fact,
  messageId,
  onStageFact,
  onToggleEvidence,
}: {
  confirmed: boolean;
  expanded: boolean;
  fact: TripFact;
  messageId: string;
  onStageFact: (factId: string) => void;
  onToggleEvidence: (messageId: string) => void;
}) {
  const meta = metaForFact(fact.id);
  const stageLabel = fact.evidenceState === "supported" ? "카드 초안으로" : "직접 채워 카드 초안";

  return (
    <div className="msg msg-ai">
      <AiWho />
      <div className="answer">
        <div className="answer-top">
          <EvidencePill state={fact.evidenceState} />
          <span className="pill">
            <span style={{ color: categoryColors[meta.category] }}>●</span>
            {meta.category} · {fact.label}
          </span>
        </div>
        <div className="answer-body">{answerText(fact)}</div>
        <button className={`ev-toggle ${expanded ? "open" : ""}`} onClick={() => onToggleEvidence(messageId)}>
          <span className="caret">▸</span>
          근거 {fact.evidence.length}개 {expanded ? "접기" : "펼치기"}
        </button>
        {expanded ? <EvidenceList fact={fact} /> : null}
        <div className="answer-actions">
          <button
            className={`btn sm ${fact.evidenceState === "supported" ? "primary" : "ghost"}`}
            disabled={confirmed}
            onClick={() => onStageFact(fact.id)}
          >
            {confirmed ? "대시보드에 있음" : stageLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

function DraftPanel({
  draft,
  fact,
  onClose,
  onConfirm,
  onDraftChange,
}: {
  draft: DraftCard | null;
  fact: TripFact | null;
  onClose: () => void;
  onConfirm: () => void;
  onDraftChange: <K extends keyof DraftCard>(key: K, value: DraftCard[K]) => void;
}) {
  if (!draft || !fact) {
    return (
      <section className="card-box draft-box" id="draft-panel">
        <div className="box-head">
          <div>
            <h2>카드 초안</h2>
            <span className="sub">답변·후보를 고르면 여기서 확인하고 올립니다</span>
          </div>
          <span className="pill info">대기</span>
        </div>
        <div className="box-body">
          <div className="empty">
            <strong>아직 선택한 답변이 없습니다</strong>
            <p>채팅 답변의 '카드 초안으로' 또는 오른쪽 추천 후보의 '카드 초안'을 누르세요.</p>
          </div>
        </div>
      </section>
    );
  }

  const meta = metaForFact(draft.factId);
  const caution = draftCaution(fact);

  return (
    <section className="card-box draft-box active-draft" id="draft-panel">
      <div className="box-head">
        <div>
          <h2>카드 초안</h2>
          <span className="sub">{meta.note}</span>
        </div>
        <EvidencePill state={fact.evidenceState} />
      </div>
      <div className="box-body draft-body">
        {caution ? <div className={`draft-caution ${fact.sensitive ? "danger" : ""}`}>{caution}</div> : null}
        <div className="draft-grid">
          <label className="field">
            <span>카테고리</span>
            <select value={draft.category} onChange={(event) => onDraftChange("category", event.target.value as Category)}>
              {Object.keys(categoryColors).map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>일정</span>
            <select value={draft.phase} onChange={(event) => onDraftChange("phase", event.target.value as PhaseKey)}>
              {phases.map((phase) => (
                <option key={phase.key} value={phase.key}>
                  {phase.label} · {phase.when}
                </option>
              ))}
            </select>
          </label>
          <label className={`field ${fact.evidenceState === "supported" ? "" : "edit"}`}>
            <span>카드 이름</span>
            <input value={draft.title} onChange={(event) => onDraftChange("title", event.target.value)} />
          </label>
          <label className={`field ${fact.evidenceState === "supported" ? "" : "edit"}`}>
            <span>값</span>
            <input
              placeholder={fact.evidenceState === "supported" ? "" : "직접 확인한 값 입력"}
              value={draft.value}
              onChange={(event) => onDraftChange("value", event.target.value)}
            />
          </label>
        </div>
        <div className="field evidence-field">
          <span>근거</span>
          <strong>{sourceNames(fact)}</strong>
        </div>
        <div className="answer-actions">
          <button className="btn primary" onClick={onConfirm}>
            <Save size={16} />
            대시보드에 올리기
          </button>
          <button className="btn ghost" onClick={onClose}>
            <X size={16} />
            초안 닫기
          </button>
        </div>
      </div>
    </section>
  );
}

function CandidateRail({
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
    <section className="card-box">
      <div className="box-head">
        <div>
          <h2>AI 추천 후보</h2>
          <span className="sub">채팅으로 보내거나 바로 초안</span>
        </div>
        <span className="pill warn">{candidateMeta.length}</span>
      </div>
      <div className="box-body">
        <div className="cand-list">
          {candidateMeta.map((candidate) => {
            const fact = factById.get(candidate.factId);
            if (!fact) return null;
            const confirmed = decisions[fact.id]?.state === "confirmed";
            const expanded = Boolean(expandedCandidates[fact.id]);
            return (
              <article className="cand-card" key={candidate.factId}>
                <div className="cc-title">
                  <span className="cat" style={{ color: categoryColors[candidate.category] }}>
                    {candidate.category}
                  </span>
                  {" · "}
                  {fact.label}
                </div>
                <div className="cc-value">{fact.value ?? "값 미정 · 직접 확인"}</div>
                <div className="answer-top">
                  <EvidencePill state={fact.evidenceState} />
                </div>
                {expanded ? <EvidenceList fact={fact} compact /> : null}
                <div className="cc-actions">
                  <button className="btn sm ghost" onClick={() => onToggleEvidence(fact.id)}>
                    <Eye size={14} />
                    {expanded ? "근거 접기" : "근거"}
                  </button>
                  <button className="btn sm ghost" onClick={() => onAskCandidate(fact.id)}>
                    <MessageSquare size={14} />
                    채팅으로
                  </button>
                  <button
                    className={`btn sm ${fact.evidenceState === "supported" ? "primary" : "ghost"}`}
                    disabled={confirmed}
                    onClick={() => onStageFact(fact.id)}
                  >
                    {confirmed ? "대시보드에 있음" : "카드 초안"}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function DashboardView({
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
    <section className="card-box">
      <div className="box-head">
        <div>
          <h2>최종 대시보드</h2>
          <span className="sub">사람이 올린 카드만 · 일정 순서로</span>
        </div>
        <span className="pill good">{decisions.length}</span>
      </div>
      <div className="box-body">
        {decisions.length === 0 ? (
          <div className="empty">
            <strong>아직 올린 카드가 없습니다</strong>
            <p>초안을 확정하면 일정 순서로 쌓입니다.</p>
          </div>
        ) : (
          <div className="phase-stack">
            {phases
              .filter((phase) => decisions.some((decision) => decision.phase === phase.key))
              .map((phase, index, usedPhases) => {
                const phaseCards = decisions.filter((decision) => decision.phase === phase.key);
                const categories = Array.from(new Set(phaseCards.map((decision) => decision.category)));
                return (
                  <div className="phase-rail" key={phase.key}>
                    <div className="phase-line">
                      <span className="knob" />
                      {index === usedPhases.length - 1 ? null : <span className="stem" />}
                    </div>
                    <div className="phase-block">
                      <div className="phase-head">
                        <h3>{phase.label}</h3>
                        <span className="when">{phase.when}</span>
                      </div>
                      {categories.map((category) => (
                        <div className="cat-group" key={category}>
                          <div className="cat-label">
                            <span style={{ color: categoryColors[category] }}>●</span>
                            {category}
                          </div>
                          <div className="cat-cards">
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
                      ))}
                    </div>
                  </div>
                );
              })}
          </div>
        )}
      </div>
    </section>
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
    <article className={`board-card ${decision.fieldSaved ? "saved-card" : ""}`}>
      <div className="bc-top">
        <h4>{decision.titleOverride || fact.label}</h4>
        <span className="bc-pills">
          <span className={`pill ${sourceTone[decision.source]}`}>{sourceLabels[decision.source]}</span>
          {decision.fieldSaved ? <span className="pill saved">현장 저장</span> : null}
        </span>
      </div>
      <div className="bc-value">{decision.valueOverride || fact.value || "—"}</div>
      <div className="bc-actions">
        <button className="btn sm ghost" disabled={fact.evidence.length === 0} onClick={() => onShowEvidence(fact.id)}>
          <Eye size={14} />
          {fact.evidence.length ? "근거" : "근거 없음"}
        </button>
        <button className={`btn sm ${decision.fieldSaved ? "ghost" : "primary"}`} onClick={() => onToggleFieldSave(fact.id)}>
          <MapPin size={14} />
          {decision.fieldSaved ? "저장됨" : "현장 저장"}
        </button>
      </div>
    </article>
  );
}

function FieldView({
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
      <section className="field-view">
        <div className="field-head">
          <div>
            <h3>현장 카드</h3>
            <p>대시보드에서 저장한 것만 · 현장에서 빠르게 보기</p>
          </div>
          <button className="btn" onClick={onOpenBoard}>
            <Library size={16} />
            대시보드
          </button>
        </div>
        <div className="empty field-empty">
          <strong>현장 카드가 비어 있습니다</strong>
          <p>대시보드에서 '현장 저장'을 누른 카드만 여기에 모입니다.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="field-view">
      <div className="field-head">
        <div>
          <h3>현장 카드</h3>
          <p>대시보드에서 저장한 것만 · 현장에서 빠르게 보기</p>
        </div>
        <span className="pill saved">{decisions.length}</span>
      </div>
      <div className="field-stack">
        {phases
          .filter((phase) => decisions.some((decision) => decision.phase === phase.key))
          .map((phase) => (
            <div className="field-phase" key={phase.key}>
              <h4>
                {phase.label} · {phase.when}
              </h4>
              <div className="field-grid">
                {decisions
                  .filter((decision) => decision.phase === phase.key)
                  .map((decision) => {
                    const fact = factById.get(decision.factId);
                    if (!fact) return null;
                    return (
                      <article className="field-card" key={decision.factId}>
                        <div className="fc-row">
                          <span className="fc-cat" style={{ color: categoryColors[decision.category] }}>
                            ● {decision.category}
                          </span>
                          <span className={`pill ${sourceTone[decision.source]}`}>{sourceLabels[decision.source]}</span>
                        </div>
                        <span className="fc-title">{decision.titleOverride || fact.label}</span>
                        <span className="fc-value">{decision.valueOverride || fact.value || "—"}</span>
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

function AiWho() {
  return (
    <div className="who">
      <span className="ai-dot">TP</span>
      TripProof
    </div>
  );
}

function EvidencePill({ state }: { state: EvidenceState }) {
  const Icon = state === "supported" ? Check : state === "missing" || state === "conflict" ? AlertTriangle : ShieldAlert;
  return (
    <span className={`pill ${evidenceTone[state]}`}>
      <Icon size={14} />
      {evidenceLabels[state]}
    </span>
  );
}

function EvidenceList({ compact = false, fact }: { compact?: boolean; fact: TripFact }) {
  if (fact.evidence.length === 0) {
    return (
      <div className="ev-none">
        이 답변에는 자료 근거가 없습니다. AI가 못 찾았을 수 있으니 직접 확인이 필요해요.
      </div>
    );
  }

  return (
    <div className={`ev-list ${compact ? "compact" : ""}`}>
      {fact.evidence.map((ref) => {
        const artifact = demoTrip.artifacts.find((item) => item.id === ref.artifactId);
        return (
          <div className="ev-item" key={`${ref.artifactId}-${ref.locator}`}>
            <div className="ev-head">
              <span className="file-badge small">{artifact ? kindLabel(artifact) : "DOC"}</span>
              <div>
                <strong>{artifact?.name ?? ref.label}</strong>
                <div className="ev-loc">{ref.locator}</div>
              </div>
            </div>
            <div className="ev-snippet">{ref.snippet}</div>
          </div>
        );
      })}
    </div>
  );
}

function metaForFact(factId: string) {
  return (
    candidateMeta.find((candidate) => candidate.factId === factId) ?? {
      factId,
      category: "숙소" as const,
      phase: "day1" as const,
      question: "체크인 몇 시부터야?",
      note: "예약 요약에 명시.",
    }
  );
}

function sourceNames(fact: TripFact, artifacts = new Map(demoTrip.artifacts.map((artifact) => [artifact.id, artifact]))) {
  return (
    fact.evidence
      .map((evidence) => artifacts.get(evidence.artifactId)?.name ?? evidence.label)
      .filter(Boolean)
      .join(" + ") || "근거 없음"
  );
}

function kindLabel(artifact: TravelArtifact) {
  if (artifact.kind === "image") return "IMG";
  if (artifact.kind === "pdf") return "PDF";
  if (artifact.kind === "receipt") return "JPG";
  if (artifact.kind === "message") return "MSG";
  return "DOC";
}

function draftCaution(fact: TripFact) {
  if (fact.sensitive) {
    return (
      <>
        <AlertTriangle size={16} />
        <span>
          <strong>민감 정보.</strong> 원문에서 직접 확인한 값만 입력하세요. 올리면 <strong>직접 확인</strong> 카드가 됩니다.
        </span>
      </>
    );
  }
  if (fact.evidenceState === "missing") {
    return (
      <>
        <AlertTriangle size={16} />
        <span>
          <strong>근거 부족.</strong> AI가 자료에서 못 찾았을 뿐일 수 있어요. 직접 확인한 값을 넣으면 <strong>직접 확인</strong> 카드로 올라갑니다.
        </span>
      </>
    );
  }
  return null;
}

function answerText(fact: TripFact) {
  if (fact.id === "late-arrival") {
    return "22:00 이후 도착하면 숙소에 미리 연락해야 합니다. 호텔 예약 화면과 호스트 메시지가 같은 조건을 말하고 있어요.";
  }
  if (fact.id === "mobile-voucher") {
    return "프린트 없이 화면 제시로 됩니다. 바우처에 '모바일 바우처 가능'이라고 적혀 있어요.";
  }
  if (fact.id === "fuel-policy") {
    return "네, 만탱크 반납 조건입니다(full-to-full). 반납 시 가득 채우지 않으면 차액과 수수료가 붙어요.";
  }
  if (fact.id === "city-tax") {
    return "호텔 도시세 JPY 1,200 결제 영수증입니다. 체크인 때 낸 추가 결제예요.";
  }
  if (fact.id === "door-code") {
    return "출입 코드는 민감 정보예요. 호스트 메시지 원문에서 직접 확인한 뒤, 필요하면 직접 채워서 카드로 올릴 수 있어요.";
  }
  if (fact.id === "checkin-time") {
    return "체크인은 15:00부터입니다. 호텔 예약 화면 예약 요약에 적혀 있어요.";
  }
  return "현재 자료에서는 지각 시 환불 규정을 찾지 못했습니다. 다만 AI가 못 찾았을 수도 있으니, 직접 확인한 내용이 있으면 채워서 올릴 수 있어요.";
}
