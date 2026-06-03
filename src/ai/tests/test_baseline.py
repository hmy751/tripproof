import unittest

from tripproof_ai import CandidateEnvelope, extract_candidates


class BaselineExtractionTest(unittest.TestCase):
    def test_extracts_checkin_and_review_candidates(self) -> None:
        envelope = CandidateEnvelope.from_dict(
            {
                "artifacts": [
                    {
                        "id": "hotel-booking",
                        "name": "호텔 예약 확인서",
                        "fileName": "hotel-booking-confirmation.png",
                        "kind": "image",
                    },
                    {
                        "id": "host-message",
                        "name": "호스트 체크인 안내",
                        "fileName": "host-checkin-message.txt",
                        "kind": "message",
                    },
                ],
                "materialTexts": {
                    "hotel-booking": "체크인 15:00. 체크아웃 11:00.",
                    "host-message": "22:00 이후 도착하면 메시지로 알려주세요. 출입 코드는 도착 당일 전달합니다.",
                },
            }
        )

        candidates = extract_candidates(envelope)
        ids = {candidate.id for candidate in candidates}

        self.assertIn("checkin-start", ids)
        self.assertIn("late-arrival", ids)
        self.assertIn("door-code", ids)

        door_code = next(candidate for candidate in candidates if candidate.id == "door-code")
        self.assertIsNone(door_code.value)
        self.assertTrue(door_code.sensitive)


if __name__ == "__main__":
    unittest.main()
