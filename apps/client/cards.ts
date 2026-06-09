import type { CardDraft, DashboardCard } from "./types";

const DEFAULT_CATEGORY = "숙소";

export function canConfirmDraft(draft: CardDraft) {
  return draft.title.trim().length > 0 && draft.value.trim().length > 0;
}

export function createDashboardCardFromDraft({
  draft,
  id,
}: {
  draft: CardDraft;
  id: string;
}): DashboardCard {
  return {
    id,
    draftId: draft.id,
    answerItemId: draft.answerItemId,
    schedule: normalizedText(draft.schedule, "이번 여행"),
    category: DEFAULT_CATEGORY,
    title: normalizedText(draft.title, "확인 카드"),
    value: normalizedText(draft.value, "확인한 값 없음"),
    sourceKind: draft.sourceKind,
    evidenceState: draft.evidenceState,
    evidence: draft.evidence,
    fieldSavedAt: null,
  };
}

export function markCardForField(card: DashboardCard, savedAt = new Date().toISOString()): DashboardCard {
  if (card.fieldSavedAt) return card;
  return {
    ...card,
    fieldSavedAt: savedAt,
  };
}

function normalizedText(value: string, fallback: string) {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : fallback;
}
