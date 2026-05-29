import type { TripProofResult, TravelArtifact } from "../../shared/tripFacts";
import {
  normalizeTripFacts,
  type RawTripFactCandidate,
} from "./normalizeTripFacts";

export type ExtractTripFactsInput = {
  artifacts: TravelArtifact[];
  userQuestion?: string;
};

export async function extractTripFacts(input: ExtractTripFactsInput): Promise<TripProofResult> {
  const candidates = await extractCandidateFacts(input.artifacts);
  return normalizeTripFacts({
    artifacts: input.artifacts,
    candidates,
  });
}

async function extractCandidateFacts(
  artifacts: TravelArtifact[],
): Promise<RawTripFactCandidate[]> {
  const hotelArtifact = artifacts[0];
  if (!hotelArtifact) return [];

  return [
    {
      id: "checkin",
      artifactId: hotelArtifact.id,
      schedule: "숙소 체크인",
      label: "체크인",
      value: "15:00",
      confidence: 0.96,
      locator: "예약 요약 영역",
      snippet: "체크인 15:00. 22:00 이후 도착 시 숙소 연락 필요.",
    },
    {
      id: "late-arrival",
      artifactId: hotelArtifact.id,
      schedule: "숙소 체크인",
      label: "늦은 도착",
      value: "22:00 이후 숙소 연락 필요",
      confidence: 0.88,
      locator: "늦은 도착 안내",
      snippet: "22:00 이후 도착 시 숙소 연락 필요.",
    },
    {
      id: "booking-number",
      artifactId: hotelArtifact.id,
      schedule: "숙소 체크인",
      label: "예약번호",
      value: "****1234",
      confidence: 0.84,
      locator: "예약번호 영역",
      snippet: "예약번호 ****1234",
      sensitive: true,
    },
  ];
}
