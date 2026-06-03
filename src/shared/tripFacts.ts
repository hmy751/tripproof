export type EvidenceState = "supported" | "needs_review" | "missing" | "conflict";

export type TravelArtifact = {
  id: string;
  name: string;
  fileName: string;
  kind: "image" | "pdf" | "message" | "receipt" | "unknown";
};

export type EvidenceRef = {
  artifactId: string;
  label: string;
  locator: string;
  snippet: string;
};

export type TripFact = {
  id: string;
  schedule: string;
  label: string;
  value: string | null;
  confidence: number;
  evidenceState: EvidenceState;
  evidence: EvidenceRef[];
  sensitive?: boolean;
};

export type TripProofResult = {
  artifacts: TravelArtifact[];
  facts: TripFact[];
  openIssues: {
    id: string;
    label: string;
    reason: string;
    evidenceState: EvidenceState;
  }[];
};
