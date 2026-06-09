import type { CardDraft, ChatAnswerItem } from "./types";

export function draftActionLabel(item: ChatAnswerItem) {
  if (item.evidenceState === "supported") return "초안으로 올리기";
  return "직접 확인으로 남기기";
}

export function createDraftFromAnswerItem({
  id,
  item,
}: {
  id: string;
  item: ChatAnswerItem;
}): CardDraft {
  const isGrounded = item.evidenceState === "supported" && item.evidence.length > 0;

  return {
    id,
    answerItemId: item.id,
    schedule: "이번 여행",
    title: item.label,
    value: isGrounded ? item.value ?? item.body : "",
    sourceKind: isGrounded ? "evidence" : "manual",
    evidenceState: item.evidenceState,
    evidence: isGrounded ? item.evidence : [],
  };
}

export function markDraftAsManual(draft: CardDraft): CardDraft {
  if (draft.sourceKind === "manual") return draft;
  return {
    ...draft,
    sourceKind: "manual",
    evidence: [],
  };
}
