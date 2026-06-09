import { ClipboardList, FileCheck2, LayoutDashboard, PencilLine, Trash2 } from "lucide-react";
import { canConfirmDraft } from "../cards";
import type { CardDraft, EvidenceRef } from "../types";
import { Button, Panel, PanelHeader, Pill } from "./ui";

export function DraftListPanel({
  drafts,
  onClearDrafts,
  onConfirmDraft,
  onRemoveDraft,
  onUpdateDraft,
}: {
  drafts: CardDraft[];
  onClearDrafts: () => void;
  onConfirmDraft: (id: string) => void;
  onRemoveDraft: (id: string) => void;
  onUpdateDraft: (id: string, field: "schedule" | "title" | "value", value: string) => void;
}) {
  return (
    <Panel>
      <PanelHeader aside={<Pill className="border-slate-200 bg-slate-50 text-slate-600">{drafts.length}</Pill>}>
        <h2 className="text-sm font-bold text-slate-950">카드 초안</h2>
        <p className="mt-0.5 text-xs text-slate-500">확인한 답변을 카드로 올리기 전 검토합니다</p>
      </PanelHeader>
      <div className="p-4">
        {drafts.length === 0 ? (
          <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center">
            <ClipboardList className="mx-auto text-slate-400" size={32} />
            <strong className="mt-3 block text-sm text-slate-900">아직 초안이 없습니다</strong>
            <p className="mx-auto mt-1 max-w-md text-sm leading-6 text-slate-500">
              채팅 답변에서 남길 항목을 고르면 이곳에 초안이 쌓입니다.
            </p>
            <div className="mt-4 flex justify-center">
              <Button disabled size="sm" variant="ghost">
                초안 비우기
              </Button>
            </div>
          </div>
        ) : (
          <div className="grid gap-3">
            {drafts.map((draft) => (
              <DraftCard
                draft={draft}
                key={draft.id}
                onConfirm={() => onConfirmDraft(draft.id)}
                onRemove={() => onRemoveDraft(draft.id)}
                onUpdate={(field, value) => onUpdateDraft(draft.id, field, value)}
              />
            ))}
            <div className="flex justify-end">
              <Button onClick={onClearDrafts} size="sm" variant="ghost">
                초안 비우기
              </Button>
            </div>
          </div>
        )}
      </div>
    </Panel>
  );
}

function DraftCard({
  draft,
  onConfirm,
  onRemove,
  onUpdate,
}: {
  draft: CardDraft;
  onConfirm: () => void;
  onRemove: () => void;
  onUpdate: (field: "schedule" | "title" | "value", value: string) => void;
}) {
  const canConfirm = canConfirmDraft(draft);

  return (
    <article className="rounded-md border border-slate-200 bg-white p-3">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <SourcePill draft={draft} />
        <div className="flex flex-wrap justify-end gap-2">
          <Button
            disabled={!canConfirm}
            onClick={onConfirm}
            size="sm"
            title={canConfirm ? undefined : "이름과 값을 입력하면 대시보드에 올릴 수 있습니다"}
            variant="primary"
          >
            <LayoutDashboard size={15} />
            대시보드에 올리기
          </Button>
          <Button aria-label="초안 삭제" onClick={onRemove} size="sm" variant="ghost">
            <Trash2 size={15} />
            삭제
          </Button>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-[minmax(0,0.75fr)_minmax(0,0.9fr)_minmax(0,1.2fr)]">
        <label className="grid gap-1.5">
          <span className="text-xs font-semibold text-slate-500">일정</span>
          <input
            className="min-h-10 rounded-md border border-slate-300 px-3 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            value={draft.schedule}
            onChange={(event) => onUpdate("schedule", event.target.value)}
          />
        </label>
        <label className="grid gap-1.5">
          <span className="text-xs font-semibold text-slate-500">이름</span>
          <input
            className="min-h-10 rounded-md border border-slate-300 px-3 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            value={draft.title}
            onChange={(event) => onUpdate("title", event.target.value)}
          />
        </label>
        <label className="grid gap-1.5">
          <span className="text-xs font-semibold text-slate-500">값</span>
          <textarea
            className="min-h-10 resize-y rounded-md border border-slate-300 px-3 py-2 text-sm leading-6 text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            placeholder="확인한 값을 입력"
            value={draft.value}
            onChange={(event) => onUpdate("value", event.target.value)}
          />
        </label>
      </div>

      <DraftSource draft={draft} />
    </article>
  );
}

function SourcePill({ draft }: { draft: CardDraft }) {
  if (draft.sourceKind === "manual") {
    return (
      <Pill className="border-slate-200 bg-slate-50 text-slate-700">
        <PencilLine size={13} />
        직접 확인
      </Pill>
    );
  }

  return (
    <Pill className="border-emerald-200 bg-emerald-50 text-emerald-700">
      <FileCheck2 size={13} />
      근거 있음
    </Pill>
  );
}

function DraftSource({ draft }: { draft: CardDraft }) {
  if (draft.sourceKind === "manual") {
    return <div className="mt-3 rounded-md bg-slate-50 px-3 py-2 text-xs font-medium text-slate-600">사용자 입력</div>;
  }

  return (
    <div className="mt-3 grid gap-2">
      {draft.evidence.map((evidence) => (
        <EvidenceSource evidence={evidence} key={`${draft.id}-${evidence.sourceUnitId}-${evidence.locator}`} />
      ))}
    </div>
  );
}

function EvidenceSource({ evidence }: { evidence: EvidenceRef }) {
  return (
    <blockquote className="border-l-2 border-blue-200 bg-blue-50/60 px-3 py-2 text-xs leading-5 text-slate-700">
      <div className="mb-1 font-semibold text-blue-800">{evidence.locator || evidence.label}</div>
      <p>{evidence.snippet.replace(/\s+/g, " ").trim()}</p>
    </blockquote>
  );
}
