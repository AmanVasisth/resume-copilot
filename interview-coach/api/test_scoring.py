import unittest

from api.scoring import SCORE_FIELDS, WEIGHTS, apply_rubric_result


def valid_payload(**overrides):
    payload = {
        "score": 999,  # Provider overall scores are intentionally ignored.
        "relevance": 70,
        "technical_correctness": 80,
        "ownership": 50,
        "reasoning": 60,
        "validation": 40,
        "depth": 70,
        "specificity": 50,
        "communication": 90,
        "strengths": ["Names the correct service roles."],
        "weaknesses": ["No verified result."],
        "follow_up_question": "What did you personally implement?",
        "next_focus": "ownership",
    }
    payload.update(overrides)
    return payload


class RubricScoringTests(unittest.TestCase):
    def test_overall_score_is_weighted_from_dimensions_not_provider_score(self):
        payload = valid_payload()
        expected = round(sum(payload[name] * weight for name, weight in WEIGHTS.items()))
        result = apply_rubric_result(payload, "gemini")
        self.assertEqual(result.score, expected)
        self.assertNotEqual(result.score, payload["score"])

    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(WEIGHTS.values()), 1.0)

    def test_score_dimensions_are_clamped_to_zero_and_one_hundred(self):
        payload = valid_payload(relevance=-20, technical_correctness=140)
        result = apply_rubric_result(payload, "openrouter")
        self.assertEqual(result.relevance, 0)
        self.assertEqual(result.technical_correctness, 100)

    def test_boolean_score_is_not_treated_as_one(self):
        result = apply_rubric_result(valid_payload(relevance=True), "gemini")
        self.assertEqual(result.relevance, 0)

    def test_missing_dimension_is_rejected_instead_of_guessed(self):
        payload = valid_payload()
        del payload["ownership"]
        with self.assertRaisesRegex(ValueError, "missing required score fields"):
            apply_rubric_result(payload, "gemini")

    def test_all_zero_dimensions_are_rejected(self):
        payload = valid_payload(**{field: 0 for field in SCORE_FIELDS})
        with self.assertRaisesRegex(ValueError, "zero for every dimension"):
            apply_rubric_result(payload, "openrouter")

    def test_text_fields_accept_string_and_list_provider_shapes(self):
        payload = valid_payload(
            strengths="Clear architecture\\n- Mentions validation",
            weaknesses=["No baseline metric", "Ownership unclear"],
        )
        result = apply_rubric_result(payload, "gemini")
        self.assertEqual(result.strengths, ["Clear architecture", "Mentions validation"])
        self.assertEqual(result.weaknesses, ["No baseline metric", "Ownership unclear"])

    def test_unknown_provider_is_normalized_safely(self):
        result = apply_rubric_result(valid_payload(), "unknown-provider")
        self.assertEqual(result.evaluation_provider, "heuristic")


if __name__ == "__main__":
    unittest.main()
