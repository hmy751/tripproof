import {
  AlertTriangle,
  BookOpen,
  Check,
  Eye,
  FileText,
  Library,
  MapPin,
  MessageSquare,
  Pencil,
  Save,
  Search,
  ShieldAlert,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";
import type { EvidenceState, TripFact } from "../shared/tripFacts";
import { type CardDecision, demoTrip, suggestedQuestions } from "./demoTrip";

type View = "confirm" | "dashboard" | "field";

const evidenceLabels: Record<EvidenceState, string> = {
  supported: "근거 있음",
  needs_review: "직접 확인 필요",
  missing: "근거 부족",
  conflict: "자료 충돌",
};

const evidenceTone: Record<EvidenceState, "good" | "warn" | "bad"> = {
  supported: "good",
  needs_review: "warn",
  missing: "warn",
  conflict: "bad",
};

const sourceLabels: Record<NonNullable<CardDecision["source"]>, string> = {
  ai_supported: "근거 보고 저장",
  manual: "직접 확인",
};

export function App() {
  const [activeView, setActiveView] = useState<View>("confirm");
  const [selectedFactId, setSelectedFactId] = useState("checkin-start");
  const [question, setQuestion] = useState(suggestedQuestions[0].text);
  const [decisions, setDecisions] = useState<Record<string, CardDecision>>({});
  const [toast, setToast] = useState("");

  const selectedFact = useMemo(
    () => demoTrip.facts.find((fact) => fact.id === selectedFactId) ?? demoTrip.facts[0],
    [selectedFactId],
  );

  const confirmedFacts = demoTrip.facts.filter(
    (fact) => decisions[fact.id]?.state === "confirmed",
  );
  const fieldFacts = confirmedFacts.filter((fact) => decisions[fact.id]?.fieldSaved);

  function flash(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(""), 1800);
  }

  function ask(nextQuestion = question) {
    const matched =
      suggestedQuestions.find((candidate) => candidate.text === nextQuestion) ??
      suggestedQuestions.find((candidate) => {
        const normalized = nextQuestion.replace(/\s/g, "");
        return (
          normalized.includes("체크인") && candidate.factId === "checkin-start"
        ) || (
          normalized.includes("늦") && candidate.factId === "late-arrival"
        ) || (
          normalized.includes("출입") && candidate.factId === "door-code"
        );
      });

    if (matched) {
      setSelectedFactId(matched.factId);
      setQuestion(nextQuestion);
      flash("자료 안에서 연결된 후보를 열었습니다.");
      return;
    }

    flash("현재 샘플 자료에서는 근거를 찾지 못했습니다.");
  }

  function updateDecision(fact: TripFact, decision: CardDecision) {
    setDecisions((current) => ({
      ...current,
      [fact.id]: decision,
    }));
  }

  function confirmFact(fact: TripFact, source: NonNullable<CardDecision["source"]>) {
    updateDecision(fact, {
      factId: fact.id,
      state: "confirmed",
      source,
      valueOverride: fact.value ?? "현장에서 직접 확인",
      fieldSaved: decisions[fact.id]?.fieldSaved ?? false,
    });
    flash(`${fact.label}을 카드로 올렸습니다.`);
  }

  function dismissFact(fact: TripFact) {
    updateDecision(fact, {
      factId: fact.id,
      state: "dismissed",
    });
    flash(`${fact.label} 후보를 제외했습니다.`);
  }

  function toggleFieldSave(fact: TripFact) {
    const current = decisions[fact.id];
    if (current?.state !== "confirmed") return;

    updateDecision(fact, {
      ...current,
      fieldSaved: !current.fieldSaved,
    });
    flash(current.fieldSaved ? "현장 탭에서 내렸습니다." : "현장 탭에 저장했습니다.");
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="mark">TP</div>
          <div>
            <strong>TripProof</strong>
            <span>여행 자료에서 믿을 정보와 직접 확인할 정보를 나눕니다</span>
          </div>
        </div>
        <select aria-label="여행 선택" defaultValue="osaka">
          <option value="osaka">오사카 4박 5일 · 숙소 체크인 준비</option>
        </select>
        <div className="status-strip">
          <span className="pill info">React web app</span>
          <span className="pill good">카드 {confirmedFacts.length}</span>
          <span className="pill warn">확인 필요 {demoTrip.openIssues.length}</span>
        </div>
      </header>

      <div className="workspace">
        <aside className="sidebar">
          <section className="upload-box">
            <div className="section-title">
              <span>여행 자료</span>
              <span>{demoTrip.artifacts.length}개</span>
            </div>
            <strong>샘플 자료함</strong>
            <p>예약 확인서와 호스트 안내를 기준으로 숙소 체크인 흐름을 확인합니다.</p>
            <button className="primary icon-button" onClick={() => setActiveView("confirm")}>
              <BookOpen size={16} />
              확인 탭 열기
            </button>
          </section>

          <section>
            <div className="section-title">
              <span>추가한 자료</span>
            </div>
            <div className="artifact-list">
              {demoTrip.artifacts.map((artifact) => (
                <button
                  className={`artifact-item ${selectedFact.evidence.some((ref) => ref.artifactId === artifact.id) ? "active" : ""}`}
                  key={artifact.id}
                  onClick={() => {
                    const fact = demoTrip.facts.find((item) =>
                      item.evidence.some((ref) => ref.artifactId === artifact.id),
                    );
                    if (fact) setSelectedFactId(fact.id);
                  }}
                >
                  <span className="file-badge">{artifact.kind.toUpperCase()}</span>
                  <span className="artifact-text">
                    <strong>{artifact.name}</strong>
                    <span>{artifact.fileName}</span>
                    <small>{artifact.kind}</small>
                  </span>
                </button>
              ))}
            </div>
          </section>

          <section>
            <div className="section-title">
              <span>확인 후보</span>
            </div>
            <div className="need-list">
              {demoTrip.facts.map((fact) => (
                <button
                  className={`candidate-row ${fact.id === selectedFact.id ? "active" : ""}`}
                  key={fact.id}
                  onClick={() => setSelectedFactId(fact.id)}
                >
                  <span>
                    <strong>{fact.label}</strong>
                    <small>{evidenceLabels[fact.evidenceState]}</small>
                  </span>
                  {decisions[fact.id]?.state === "confirmed" ? <Check size={16} /> : null}
                </button>
              ))}
            </div>
          </section>
        </aside>

        <main className="main">
          <nav className="tabs" aria-label="TripProof 화면">
            <TabButton active={activeView === "confirm"} onClick={() => setActiveView("confirm")}>
              <MessageSquare size={16} />
              확인
            </TabButton>
            <TabButton active={activeView === "dashboard"} onClick={() => setActiveView("dashboard")}>
              <Library size={16} />
              대시보드
            </TabButton>
            <TabButton active={activeView === "field"} onClick={() => setActiveView("field")}>
              <MapPin size={16} />
              현장
            </TabButton>
          </nav>

          {activeView === "confirm" ? (
            <ConfirmView
              question={question}
              selectedFact={selectedFact}
              decisions={decisions}
              onAsk={ask}
              onConfirm={confirmFact}
              onDismiss={dismissFact}
              onQuestionChange={setQuestion}
              onSelectFact={setSelectedFactId}
            />
          ) : null}

          {activeView === "dashboard" ? (
            <DashboardView
              decisions={decisions}
              facts={confirmedFacts}
              onOpenFact={(factId) => {
                setSelectedFactId(factId);
                setActiveView("confirm");
              }}
              onToggleFieldSave={toggleFieldSave}
            />
          ) : null}

          {activeView === "field" ? (
            <FieldView
              decisions={decisions}
              facts={fieldFacts}
              onOpenDashboard={() => setActiveView("dashboard")}
            />
          ) : null}
        </main>
      </div>

      <div className={`toast ${toast ? "show" : ""}`} aria-live="polite">
        {toast}
      </div>
    </div>
  );
}

function TabButton({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button className={`tab icon-tab ${active ? "active" : ""}`} onClick={onClick}>
      {children}
    </button>
  );
}

function ConfirmView({
  question,
  selectedFact,
  decisions,
  onAsk,
  onConfirm,
  onDismiss,
  onQuestionChange,
  onSelectFact,
}: {
  question: string;
  selectedFact: TripFact;
  decisions: Record<string, CardDecision>;
  onAsk: (question?: string) => void;
  onConfirm: (fact: TripFact, source: NonNullable<CardDecision["source"]>) => void;
  onDismiss: (fact: TripFact) => void;
  onQuestionChange: (value: string) => void;
  onSelectFact: (factId: string) => void;
}) {
  const decision = decisions[selectedFact.id];
  const value = decision?.valueOverride ?? selectedFact.value;

  return (
    <section className="split confirm-layout">
      <article className="panel">
        <div className="panel-head">
          <div>
            <h2>자료함에 묻기</h2>
            <p>샘플 자료 안에서만 답하고, 근거 상태를 함께 보여줍니다.</p>
          </div>
          <span className="pill info">숙소 체크인</span>
        </div>

        <div className="question-list">
          {suggestedQuestions.map((candidate) => (
            <button
              className="icon-button"
              key={candidate.factId}
              onClick={() => {
                onQuestionChange(candidate.text);
                onSelectFact(candidate.factId);
              }}
            >
              <Search size={16} />
              {candidate.text}
            </button>
          ))}
        </div>

        <div className="chat-box">
          <textarea
            aria-label="자료함 질문"
            value={question}
            onChange={(event) => onQuestionChange(event.target.value)}
          />
          <button className="primary icon-button" onClick={() => onAsk()}>
            <Search size={16} />
            자료 안에서 답 찾기
          </button>
        </div>

        <div className="answer-box">
          <div className="answer-head">
            <EvidencePill state={selectedFact.evidenceState} />
            {selectedFact.sensitive ? (
              <span className="pill warn">
                <ShieldAlert size={14} />
                민감 정보
              </span>
            ) : null}
          </div>
          <h3>{selectedFact.label}</h3>
          <p>{answerText(selectedFact, value)}</p>
          <EvidenceList fact={selectedFact} />
        </div>
      </article>

      <article className="panel">
        <div className="panel-head">
          <div>
            <h2>카드 초안</h2>
            <p>AI 후보는 확정 정보가 아닙니다. 사람이 저장한 카드만 대시보드에 올라갑니다.</p>
          </div>
          <span className="pill">{decisionLabel(decision)}</span>
        </div>

        <div className="fact-card">
          <div className="fact-head">
            <div>
              <h3>{selectedFact.label}</h3>
              <div className="fact-value">{value ?? "직접 확인 후 입력"}</div>
            </div>
            <EvidencePill state={selectedFact.evidenceState} />
          </div>
          <div className="citation">
            <FileText size={16} />
            <span>{selectedFact.evidence[0]?.label ?? "자료함 전체"}</span>
            <code>{selectedFact.evidence[0]?.locator ?? "근거 위치 없음"}</code>
          </div>
          <div className="fact-actions">
            {selectedFact.evidenceState === "supported" ? (
              <button className="success icon-button" onClick={() => onConfirm(selectedFact, "ai_supported")}>
                <Save size={16} />
                근거 보고 저장
              </button>
            ) : null}
            <button className="icon-button" onClick={() => onConfirm(selectedFact, "manual")}>
              <Pencil size={16} />
              직접 확인으로 올리기
            </button>
            <button className="danger icon-button" onClick={() => onDismiss(selectedFact)}>
              <X size={16} />
              제외
            </button>
          </div>
        </div>

        <dl className="source-table">
          <div>
            <dt>근거 상태</dt>
            <dd>{evidenceLabels[selectedFact.evidenceState]}</dd>
          </div>
          <div>
            <dt>자료</dt>
            <dd>
              <strong>{selectedFact.evidence[0]?.label ?? "자료 없음"}</strong>
              <small>{selectedFact.evidence[0]?.artifactId ?? "missing"}</small>
            </dd>
          </div>
          <div>
            <dt>찾은 위치</dt>
            <dd>
              <code>{selectedFact.evidence[0]?.locator ?? "근거 위치 없음"}</code>
            </dd>
          </div>
          <div>
            <dt>원문 근거</dt>
            <dd>
              <code>{selectedFact.evidence[0]?.snippet ?? "근거가 부족해 직접 확인이 필요합니다."}</code>
            </dd>
          </div>
        </dl>
      </article>
    </section>
  );
}

function DashboardView({
  decisions,
  facts,
  onOpenFact,
  onToggleFieldSave,
}: {
  decisions: Record<string, CardDecision>;
  facts: TripFact[];
  onOpenFact: (factId: string) => void;
  onToggleFieldSave: (fact: TripFact) => void;
}) {
  if (facts.length === 0) {
    return (
      <section className="panel">
        <div className="empty-state">확인 탭에서 근거를 보고 카드로 올리면 여기에 모입니다.</div>
      </section>
    );
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>상황별 저장 정보</h2>
          <p>사람이 카드로 올린 정보만 표시합니다.</p>
        </div>
        <span className="pill good">저장 카드 {facts.length}</span>
      </div>
      <div className="board-grid">
        {facts.map((fact) => (
          <article className="schedule-card" key={fact.id}>
            <div>
              <strong>{fact.schedule}</strong>
              <span>{sourceLabels[decisions[fact.id]?.source ?? "manual"]}</span>
            </div>
            <div className="mini-fact">
              <strong>{fact.label}</strong>
              <span>{decisions[fact.id]?.valueOverride ?? fact.value ?? "직접 확인"}</span>
            </div>
            <EvidencePill state={fact.evidenceState} />
            <div className="fact-actions">
              <button className="icon-button" onClick={() => onOpenFact(fact.id)}>
                <Eye size={16} />
                근거 보기
              </button>
              <button className="icon-button" onClick={() => onToggleFieldSave(fact)}>
                <MapPin size={16} />
                {decisions[fact.id]?.fieldSaved ? "현장에서 내리기" : "현장 저장"}
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function FieldView({
  decisions,
  facts,
  onOpenDashboard,
}: {
  decisions: Record<string, CardDecision>;
  facts: TripFact[];
  onOpenDashboard: () => void;
}) {
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>현장에서 다시 볼 카드</h2>
          <p>현장 저장한 카드만 짧게 모읍니다.</p>
        </div>
        <button className="icon-button" onClick={onOpenDashboard}>
          <Library size={16} />
          대시보드로
        </button>
      </div>
      {facts.length === 0 ? (
        <div className="empty-state">대시보드에서 현장 저장을 누르면 여기에 표시됩니다.</div>
      ) : (
        <div className="field-grid">
          {facts.map((fact) => (
            <article className="field-card" key={fact.id}>
              <span className="pill info">{fact.schedule}</span>
              <h3>{fact.label}</h3>
              <strong>{decisions[fact.id]?.valueOverride ?? fact.value ?? "직접 확인"}</strong>
              <EvidencePill state={fact.evidenceState} />
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function EvidencePill({ state }: { state: EvidenceState }) {
  const Icon = state === "supported" ? Check : state === "conflict" ? AlertTriangle : ShieldAlert;
  return (
    <span className={`pill ${evidenceTone[state]}`}>
      <Icon size={14} />
      {evidenceLabels[state]}
    </span>
  );
}

function EvidenceList({ fact }: { fact: TripFact }) {
  if (fact.evidence.length === 0) {
    return (
      <div className="citation">
        <AlertTriangle size={16} />
        <span>근거 부족</span>
        <code>자료함에서 답할 수 있는 원문을 찾지 못했습니다.</code>
      </div>
    );
  }

  return (
    <div className="evidence-list">
      {fact.evidence.map((ref) => (
        <div className="citation" key={`${ref.artifactId}-${ref.locator}`}>
          <FileText size={16} />
          <span>{ref.label}</span>
          <code>{ref.snippet}</code>
        </div>
      ))}
    </div>
  );
}

function answerText(fact: TripFact, value: string | null | undefined) {
  if (fact.sensitive) {
    return "민감한 값은 자동 저장하지 않습니다. 원문 위치만 열어 두고 현장에서 직접 확인하세요.";
  }
  if (fact.evidenceState === "supported") {
    return `${value}로 확인됩니다. 카드로 올리기 전에 아래 원문 근거를 확인하세요.`;
  }
  if (fact.evidenceState === "needs_review") {
    return `${value ?? "값을 바로 확정하지 않습니다"}. 원문 근거는 있지만 직접 확인 후 카드로 올리는 흐름입니다.`;
  }
  if (fact.evidenceState === "conflict") {
    return "자료끼리 값이 충돌합니다. 양쪽 근거를 보고 직접 확인해야 합니다.";
  }
  return "현재 자료함에서는 답할 원문 근거를 찾지 못했습니다.";
}

function decisionLabel(decision: CardDecision | undefined) {
  if (!decision || decision.state === "draft") return "초안";
  if (decision.state === "dismissed") return "제외됨";
  return decision.source ? sourceLabels[decision.source] : "저장됨";
}
