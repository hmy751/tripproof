import { AlertTriangle, Save, Send, X } from "lucide-react";
import type { ReactNode } from "react";
import type { TripFact } from "../../shared/tripFacts";
import { categoryThemes, phases } from "../data/tripSession";
import type { CardDecision, Category, PhaseKey } from "../data/tripSession";
import { answerText, draftCaution, metaForFact, sourceNames } from "../lib/tripUi";
import type { ChatMessage, DraftCard } from "../types";
import { EvidenceList } from "./EvidenceList";
import { Button, EvidencePill, Panel, PanelHeader, Pill, cx } from "./ui";

export function ChatWorkspace({
  artifactCount,
  decisions,
  draft,
  expandedAnswers,
  factById,
  question,
  thread,
  onAsk,
  onCloseDraft,
  onConfirmDraft,
  onDraftChange,
  onQuestionChange,
  onStageFact,
  onToggleEvidence,
}: {
  artifactCount: number;
  decisions: Record<string, CardDecision>;
  draft: DraftCard | null;
  expandedAnswers: Record<string, boolean>;
  factById: Map<string, TripFact>;
  question: string;
  thread: ChatMessage[];
  onAsk: (question?: string) => void;
  onCloseDraft: () => void;
  onConfirmDraft: () => void;
  onDraftChange: <K extends keyof DraftCard>(key: K, value: DraftCard[K]) => void;
  onQuestionChange: (value: string) => void;
  onStageFact: (factId: string) => void;
  onToggleEvidence: (messageId: string) => void;
}) {
  const draftFact = draft ? factById.get(draft.factId) ?? null : null;

  return (
    <div className="grid gap-4">
      <ChatPanel
        artifactCount={artifactCount}
        decisions={decisions}
        expandedAnswers={expandedAnswers}
        factById={factById}
        question={question}
        thread={thread}
        onAsk={onAsk}
        onQuestionChange={onQuestionChange}
        onStageFact={onStageFact}
        onToggleEvidence={onToggleEvidence}
      />
      <DraftPanel
        draft={draft}
        fact={draftFact}
        onClose={onCloseDraft}
        onConfirm={onConfirmDraft}
        onDraftChange={onDraftChange}
      />
    </div>
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
    <Panel className="overflow-hidden">
      <div className="border-b border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
        대상: <strong className="text-slate-950">전체 자료함 ({artifactCount}개)</strong> · 자료명을 넣으면 답변 범위를 좁힐 수 있어요
      </div>
      <div className="grid max-h-[620px] gap-4 overflow-y-auto px-4 py-4">
        {thread.map((message) => {
          if (message.role === "user") {
            return (
              <div className="flex justify-end" key={message.id}>
                <div className="max-w-[78%] rounded-lg bg-slate-950 px-4 py-3 text-sm leading-6 text-white">{message.text}</div>
              </div>
            );
          }

          if (message.kind === "intro") {
            return (
              <div className="grid grid-cols-[auto_minmax(0,1fr)] gap-3" key={message.id}>
                <AiWho />
                <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm leading-6 text-slate-700">
                  자료 {artifactCount}개를 읽었어요. 오른쪽 <strong className="text-slate-950">추천 후보</strong>를 채팅으로 보내거나 바로 카드 초안으로 만들 수 있고, 아래에 직접 물어봐도 됩니다. 답변에는 근거와 상태가 함께 붙어요.
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
      <div className="border-t border-slate-200 bg-white p-3">
        <div className="grid gap-2 md:grid-cols-[minmax(0,1fr)_auto]">
          <textarea
            aria-label="이번 여행 자료에 질문"
            className="min-h-20 resize-none rounded-md border border-slate-300 px-3 py-2 text-sm leading-6 text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
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
          <Button className="md:h-full md:min-w-28" onClick={() => onAsk()} variant="primary">
            <Send size={16} />
            물어보기
          </Button>
        </div>
      </div>
    </Panel>
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
  const theme = categoryThemes[meta.category];

  return (
    <div className="grid grid-cols-[auto_minmax(0,1fr)] gap-3">
      <AiWho />
      <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
        <div className="flex flex-wrap items-center gap-2">
          <EvidencePill state={fact.evidenceState} />
          <Pill className={theme.badge}>
            <span className={cx("h-2 w-2 rounded-full", theme.dot)} />
            {meta.category} · {fact.label}
          </Pill>
        </div>
        <p className="mt-3 text-sm leading-6 text-slate-800">{answerText(fact)}</p>
        <button
          className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-slate-500 transition hover:text-slate-900"
          onClick={() => onToggleEvidence(messageId)}
        >
          <span className={cx("transition", expanded && "rotate-90")}>▸</span>
          근거 {fact.evidence.length}개 {expanded ? "접기" : "펼치기"}
        </button>
        {expanded ? <EvidenceList fact={fact} /> : null}
        <div className="mt-3 flex justify-end">
          <Button
            disabled={confirmed}
            onClick={() => onStageFact(fact.id)}
            size="sm"
            variant={fact.evidenceState === "supported" ? "primary" : "secondary"}
          >
            {confirmed ? "대시보드에 있음" : stageLabel}
          </Button>
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
      <Panel id="draft-panel">
        <PanelHeader aside={<span className="rounded-full border border-blue-200 bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700">대기</span>}>
          <h2 className="text-sm font-bold text-slate-950">카드 초안</h2>
          <p className="mt-0.5 text-xs text-slate-500">답변·후보를 고르면 여기서 확인하고 올립니다</p>
        </PanelHeader>
        <div className="p-4">
          <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center">
            <strong className="block text-sm text-slate-900">아직 선택한 답변이 없습니다</strong>
            <p className="mt-1 text-sm text-slate-500">채팅 답변이나 추천 후보에서 카드 초안을 만드세요.</p>
          </div>
        </div>
      </Panel>
    );
  }

  const meta = metaForFact(draft.factId);
  const caution = draftCaution(fact);

  return (
    <Panel className="ring-2 ring-blue-100" id="draft-panel">
      <PanelHeader aside={<EvidencePill state={fact.evidenceState} />}>
        <h2 className="text-sm font-bold text-slate-950">카드 초안</h2>
        <p className="mt-0.5 text-xs text-slate-500">{meta.note}</p>
      </PanelHeader>
      <div className="grid gap-4 p-4">
        {caution ? (
          <div
            className={cx(
              "flex gap-2 rounded-md border px-3 py-2 text-sm leading-6",
              caution.tone === "danger"
                ? "border-rose-200 bg-rose-50 text-rose-800"
                : "border-amber-200 bg-amber-50 text-amber-800",
            )}
          >
            <AlertTriangle className="mt-1 shrink-0" size={16} />
            <span>
              <strong>{caution.title}</strong> {caution.body}
            </span>
          </div>
        ) : null}

        <div className="grid gap-3 md:grid-cols-2">
          <Field label="카테고리">
            <select
              className="h-10 rounded-md border border-slate-300 bg-white px-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              value={draft.category}
              onChange={(event) => onDraftChange("category", event.target.value as Category)}
            >
              {Object.keys(categoryThemes).map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </Field>
          <Field label="일정">
            <select
              className="h-10 rounded-md border border-slate-300 bg-white px-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              value={draft.phase}
              onChange={(event) => onDraftChange("phase", event.target.value as PhaseKey)}
            >
              {phases.map((phase) => (
                <option key={phase.key} value={phase.key}>
                  {phase.label} · {phase.when}
                </option>
              ))}
            </select>
          </Field>
          <Field label="카드 이름">
            <input
              className="h-10 rounded-md border border-slate-300 px-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              value={draft.title}
              onChange={(event) => onDraftChange("title", event.target.value)}
            />
          </Field>
          <Field label="값">
            <input
              className="h-10 rounded-md border border-slate-300 px-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              placeholder={fact.evidenceState === "supported" ? "" : "직접 확인한 값 입력"}
              value={draft.value}
              onChange={(event) => onDraftChange("value", event.target.value)}
            />
          </Field>
        </div>

        <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
          <span className="block text-xs font-medium text-slate-500">근거</span>
          <strong className="mt-1 block text-sm text-slate-900">{sourceNames(fact)}</strong>
        </div>

        <div className="flex flex-wrap justify-end gap-2">
          <Button onClick={onConfirm} variant="primary">
            <Save size={16} />
            대시보드에 올리기
          </Button>
          <Button onClick={onClose} variant="ghost">
            <X size={16} />
            초안 닫기
          </Button>
        </div>
      </div>
    </Panel>
  );
}

function Field({ children, label }: { children: ReactNode; label: string }) {
  return (
    <label className="grid gap-1.5">
      <span className="text-xs font-semibold text-slate-500">{label}</span>
      {children}
    </label>
  );
}

function AiWho() {
  return (
    <div className="flex items-center gap-2 self-start text-xs font-semibold text-slate-500">
      <span className="grid h-8 w-8 place-items-center rounded-full bg-slate-950 font-mono text-[11px] text-white">TP</span>
    </div>
  );
}
