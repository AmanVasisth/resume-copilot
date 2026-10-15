import unittest

from api.models import CandidateProfile, Question
from api.scoring import apply_rubric_result
from api.engine import evaluate_answer


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.candidate = CandidateProfile(
            target_role="Senior Azure AI Engineer",
            years_experience=8,
            skills=["Azure", "GenAI"],
            required_skills=["Azure"],
        )
        self.question = Question(
            id="azure-project",
            category="technical",
            skill="Azure",
            difficulty="senior",
            question="Describe an Azure project, your contribution, design trade-off, validation and measurable result.",
            rationale="Tests evidence and ownership.",
            source="role_map",
        )

    def test_weighted_score_is_canonical_not_provider_supplied(self):
        payload = {
            "score": 99,
            "relevance": 80,
            "technical_correctness": 70,
            "ownership": 60,
            "reasoning": 50,
            "validation": 40,
            "depth": 30,
            "specificity": 20,
            "communication": 10,
            "strengths": ["Names the problem"],
            "weaknesses": ["Needs validation evidence"],
            "follow_up_question": "How did you validate it?",
            "next_focus": "validation",
        }
        result = apply_rubric_result(payload, "gemini")
        expected = round(0.20*80 + 0.20*70 + 0.15*60 + 0.15*50 + 0.10*40 + 0.10*30 + 0.05*20 + 0.05*10)
        self.assertEqual(result.score, expected)
        self.assertNotEqual(result.score, payload["score"])
        self.assertEqual(result.evaluation_provider, "gemini")
        self.assertEqual(result.evaluation_method, "llm_rubric")

    def test_all_maximum_dimensions_score_100(self):
        payload = {
            "score": 100,
            "relevance": 100, "technical_correctness": 100, "ownership": 100,
            "reasoning": 100, "validation": 100, "depth": 100,
            "specificity": 100, "communication": 100,
            "strengths": [], "weaknesses": [], "follow_up_question": "",
            "next_focus": "maintain quality",
        }
        self.assertEqual(apply_rubric_result(payload, "openrouter").score, 100)

    def test_short_generic_answer_is_not_scored_as_midrange(self):
        result = evaluate_answer(
            self.question,
            "I worked on Azure and improved things.",
            self.candidate,
        )
        self.assertLessEqual(result.score, 15)
        self.assertTrue(result.weaknesses)
        self.assertIsNotNone(result.follow_up_question)

    def test_empty_answer_is_not_rewarded(self):
        result = evaluate_answer(self.question, "", self.candidate)
        self.assertLessEqual(result.score, 5)
        self.assertEqual(result.technical_correctness, 0)


if __name__ == "__main__":
    unittest.main()
