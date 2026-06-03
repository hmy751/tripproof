import type {
  EvidenceRef,
  EvidenceState,
  TripFact,
  TripProofResult,
  TravelArtifact,
} from "../../shared/tripFacts";

export type RawTripFactCandidate = {
  id: string;
  artifactId?: string;
  schedule: string;
  label: string;
  value: string | null;
  confidence: number;
  locator?: string;
  snippet?: string;
  sensitive?: boolean;
  conflictWith?: string[];
};

export type NormalizeTripFactsInput = {
  artifacts: TravelArtifact[];
  candidates: RawTripFactCandidate[];
};

export function normalizeTripFacts(input: NormalizeTripFactsInput): TripProofResult {
  const artifactById = new Map(
    input.artifacts.map((artifact) => [artifact.id, artifact]),
  );
  const facts = input.candidates.map((candidate) =>
    normalizeCandidate(candidate, artifactById),
  );

  return {
    artifacts: input.artifacts,
    facts,
    openIssues: facts
      .filter((fact) => fact.evidenceState !== "supported")
      .map((fact) => ({
        id: `${fact.id}-issue`,
        label: fact.label,
        reason: issueReason(fact),
        evidenceState: fact.evidenceState,
      })),
  };
}

function normalizeCandidate(
  candidate: RawTripFactCandidate,
  artifactById: Map<string, TravelArtifact>,
): TripFact {
  const evidence = buildEvidence(candidate, artifactById);

  return {
    id: candidate.id,
    schedule: candidate.schedule,
    label: candidate.label,
    value: candidate.value,
    confidence: candidate.confidence,
    sensitive: candidate.sensitive,
    evidence,
    evidenceState: decideEvidenceState(candidate, evidence),
  };
}

function buildEvidence(
  candidate: RawTripFactCandidate,
  artifactById: Map<string, TravelArtifact>,
): EvidenceRef[] {
  if (!candidate.artifactId || !candidate.locator || !candidate.snippet) {
    return [];
  }

  const artifact = artifactById.get(candidate.artifactId);
  if (!artifact) return [];

  return [
    {
      artifactId: artifact.id,
      label: artifact.name,
      locator: candidate.locator,
      snippet: candidate.snippet,
    },
  ];
}

function decideEvidenceState(
  candidate: RawTripFactCandidate,
  evidence: EvidenceRef[],
): EvidenceState {
  if (candidate.conflictWith?.length) return "conflict";
  if (evidence.length === 0) return "missing";
  if (candidate.sensitive || candidate.confidence < 0.78) return "needs_review";
  return "supported";
}

function issueReason(fact: TripFact): string {
  if (fact.evidenceState === "missing") {
    return "원문 근거가 없어 사용자에게 사실처럼 보여주지 않는다.";
  }
  if (fact.evidenceState === "conflict") {
    return "자료끼리 값이 충돌해 자동 확정하지 않는다.";
  }
  return "민감 정보이거나 신뢰도가 낮아 직접 확인 대상으로 남긴다.";
}
