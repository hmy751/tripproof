import type { EvidenceState, TravelArtifact, TripFact } from "../../shared/tripFacts";
import { candidateCards, extraQuestionMatches, tripSession } from "../data/tripSession";
import type { CardDecision, Category, PhaseKey } from "../data/tripSession";

export const evidenceLabels: Record<EvidenceState, string> = {
  supported: "근거 있음",
  needs_review: "확인 필요",
  missing: "근거 부족",
  conflict: "자료 충돌",
};

export const evidencePillClasses: Record<EvidenceState, string> = {
  supported: "border-emerald-200 bg-emerald-50 text-emerald-700",
  needs_review: "border-amber-200 bg-amber-50 text-amber-800",
  missing: "border-rose-200 bg-rose-50 text-rose-700",
  conflict: "border-orange-200 bg-orange-50 text-orange-800",
};

export const sourceLabels: Record<CardDecision["source"], string> = {
  ai_supported: "근거 있음",
  manual: "직접 확인",
};

export const sourcePillClasses: Record<CardDecision["source"], string> = {
  ai_supported: "border-emerald-200 bg-emerald-50 text-emerald-700",
  manual: "border-slate-300 bg-slate-100 text-slate-700",
};

export function metaForFact(factId: string): {
  factId: string;
  category: Category;
  phase: PhaseKey;
  question: string;
  note: string;
} {
  return (
    candidateCards.find((candidate) => candidate.factId === factId) ?? {
      factId,
      category: "숙소",
      phase: "day1",
      question: "체크인 몇 시부터야?",
      note: "예약 요약에 명시.",
    }
  );
}

export function findQuestionFactId(rawQuestion: string) {
  const trimmed = rawQuestion.trim();
  if (extraQuestionMatches[trimmed]) return extraQuestionMatches[trimmed];

  const exact = candidateCards.find((candidate) => candidate.question === trimmed);
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

export function sourceNames(
  fact: TripFact,
  artifacts = new Map(tripSession.artifacts.map((artifact) => [artifact.id, artifact])),
) {
  return (
    fact.evidence
      .map((evidence) => artifacts.get(evidence.artifactId)?.name ?? evidence.label)
      .filter(Boolean)
      .join(" + ") || "근거 없음"
  );
}

export function kindLabel(artifact: TravelArtifact) {
  if (artifact.kind === "image") return "IMG";
  if (artifact.kind === "pdf") return "PDF";
  if (artifact.kind === "receipt") return "JPG";
  if (artifact.kind === "message") return "MSG";
  return "DOC";
}

export function draftCaution(fact: TripFact) {
  if (fact.sensitive) {
    return {
      tone: "danger" as const,
      title: "민감 정보.",
      body: "원문에서 직접 확인한 값만 입력하세요. 올리면 직접 확인 카드가 됩니다.",
    };
  }

  if (fact.evidenceState === "missing") {
    return {
      tone: "warning" as const,
      title: "근거 부족.",
      body: "AI가 자료에서 못 찾았을 뿐일 수 있어요. 직접 확인한 값을 넣으면 직접 확인 카드로 올라갑니다.",
    };
  }

  return null;
}

export function answerText(fact: TripFact) {
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
