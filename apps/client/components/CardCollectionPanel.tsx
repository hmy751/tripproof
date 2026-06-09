import {
  BookmarkCheck,
  BookmarkPlus,
  CalendarDays,
  ClipboardList,
  FileCheck2,
  PencilLine,
} from "lucide-react";
import type { DashboardCard, EvidenceRef } from "../types";
import { Button, Panel, PanelHeader, Pill } from "./ui";

type CardCollectionView = "board" | "field";

export function CardCollectionPanel({
  cards,
  onSaveForField,
  view,
}: {
  cards: DashboardCard[];
  onSaveForField?: (id: string) => void;
  view: CardCollectionView;
}) {
  const groups = groupCards(cards);
  const copy = viewCopy(view);

  return (
    <Panel>
      <PanelHeader aside={<Pill className="border-slate-200 bg-slate-50 text-slate-600">{cards.length}</Pill>}>
        <h1 className="text-sm font-bold text-slate-950">{copy.title}</h1>
        <p className="mt-0.5 text-xs text-slate-500">{copy.subtitle}</p>
      </PanelHeader>
      <div className="p-4">
        {cards.length === 0 ? (
          <EmptyCards description={copy.emptyDescription} title={copy.emptyTitle} />
        ) : (
          <div className="grid gap-5">
            {groups.map((scheduleGroup) => (
              <section className="grid gap-3" key={scheduleGroup.schedule}>
                <div className="flex items-center gap-2 text-xs font-bold text-slate-500">
                  <CalendarDays size={15} />
                  {scheduleGroup.schedule}
                </div>
                {scheduleGroup.categories.map((categoryGroup) => (
                  <div className="grid gap-2" key={`${scheduleGroup.schedule}-${categoryGroup.category}`}>
                    <div className="text-xs font-semibold text-slate-400">{categoryGroup.category}</div>
                    <div className="grid gap-3 xl:grid-cols-2">
                      {categoryGroup.cards.map((card) => (
                        <DashboardCardItem
                          card={card}
                          key={card.id}
                          onSaveForField={view === "board" ? onSaveForField : undefined}
                          view={view}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </section>
            ))}
          </div>
        )}
      </div>
    </Panel>
  );
}

function DashboardCardItem({
  card,
  onSaveForField,
  view,
}: {
  card: DashboardCard;
  onSaveForField?: (id: string) => void;
  view: CardCollectionView;
}) {
  const isSaved = Boolean(card.fieldSavedAt);

  return (
    <article className="grid gap-3 rounded-md border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <SourcePill card={card} />
          {isSaved ? (
            <Pill className="border-blue-200 bg-blue-50 text-blue-700">
              <BookmarkCheck size={13} />
              현장 저장
            </Pill>
          ) : null}
        </div>
        <Pill className="border-slate-200 bg-slate-50 text-slate-600">{card.category}</Pill>
      </div>

      <div>
        <h2 className="text-base font-bold text-slate-950">{card.title}</h2>
        <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{card.value}</p>
      </div>

      <CardSource card={card} />

      {view === "board" && onSaveForField ? (
        <div className="flex justify-end">
          <Button disabled={isSaved} onClick={() => onSaveForField(card.id)} size="sm" variant={isSaved ? "secondary" : "primary"}>
            {isSaved ? <BookmarkCheck size={15} /> : <BookmarkPlus size={15} />}
            {isSaved ? "저장됨" : "현장 저장"}
          </Button>
        </div>
      ) : null}
    </article>
  );
}

function SourcePill({ card }: { card: DashboardCard }) {
  if (card.sourceKind === "manual") {
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

function CardSource({ card }: { card: DashboardCard }) {
  if (card.sourceKind === "manual") {
    return <div className="rounded-md bg-slate-50 px-3 py-2 text-xs font-medium text-slate-600">사용자 입력</div>;
  }

  return (
    <div className="grid gap-2">
      {card.evidence.map((evidence) => (
        <EvidenceSource evidence={evidence} key={`${card.id}-${evidence.sourceUnitId}-${evidence.locator}`} />
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

function EmptyCards({
  description,
  title,
}: {
  description: string;
  title: string;
}) {
  return (
    <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-4 py-12 text-center">
      <ClipboardList className="mx-auto text-slate-400" size={36} />
      <strong className="mt-4 block text-base text-slate-950">{title}</strong>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">{description}</p>
    </div>
  );
}

function groupCards(cards: DashboardCard[]) {
  return cards.reduce<Array<{ schedule: string; categories: Array<{ category: string; cards: DashboardCard[] }> }>>(
    (scheduleGroups, card) => {
      let scheduleGroup = scheduleGroups.find((group) => group.schedule === card.schedule);
      if (!scheduleGroup) {
        scheduleGroup = { schedule: card.schedule, categories: [] };
        scheduleGroups.push(scheduleGroup);
      }

      let categoryGroup = scheduleGroup.categories.find((group) => group.category === card.category);
      if (!categoryGroup) {
        categoryGroup = { category: card.category, cards: [] };
        scheduleGroup.categories.push(categoryGroup);
      }

      categoryGroup.cards.push(card);
      return scheduleGroups;
    },
    [],
  );
}

function viewCopy(view: CardCollectionView) {
  if (view === "field") {
    return {
      title: "현장 카드",
      subtitle: "현장 저장한 카드만 모입니다",
      emptyTitle: "현장 카드가 비어 있습니다",
      emptyDescription: "대시보드 카드에서 현장 저장을 누른 정보만 여기에 모입니다.",
    };
  }

  return {
    title: "대시보드",
    subtitle: "확정한 카드만 일정과 카테고리로 정리됩니다",
    emptyTitle: "대시보드가 비어 있습니다",
    emptyDescription: "카드 초안을 대시보드에 올리면 원문 근거 카드와 직접 확인 카드가 여기에 모입니다.",
  };
}
