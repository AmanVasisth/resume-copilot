"""Opt-in live model benchmark. Run from interview-coach with the API venv active:
python -m api.tests.run_live_benchmarks

This calls the configured LLM provider and may consume free-tier quota.
The cases are synthetic evaluation fixtures, not claims about a real project.
"""
import os
import sys

from api.models import CandidateProfile, Question
from api.llm import evaluate_with_llm
from api.scoring import apply_rubric_result


CANDIDATE = CandidateProfile(
    target_role="Senior Azure AI Engineer",
    years_experience=8,
    skills=["Azure", "Azure AI Search", "Azure OpenAI", "RAG"],
    required_skills=["Azure", "Azure AI Search"],
)

QUESTION = Question(
    id="benchmark-azure-rag",
    category="technical",
    skill="Azure",
    difficulty="senior",
    question=(
        "Describe an Azure RAG project: the business problem, your personal contribution, "
        "a design decision and trade-off, how you validated it, and an actual measurable result."
    ),
    rationale="Synthetic benchmark for scoring consistency.",
    source="role_map",
)

CASES = [
    {
        "name": "weak",
        "answer": "I worked on Azure and improved things.",
    },
    {
        "name": "average",
        "answer": (
            "The goal was to help employees find information in company documents. "
            "I used Azure AI Search to index documents and Azure OpenAI to generate answers. "
            "I helped prepare the documents and tested a few sample questions. "
            "I chose retrieval because answers should use source documents, although it adds latency. "
            "The tests looked reasonable, but I did not record a baseline or numerical result."
        ),
    },
    {
        "name": "strong",
        "answer": (
            "The goal was to help employees find policy information across a large document set. "
            "I owned the ingestion workflow, split documents into overlapping chunks, attached source metadata, "
            "created embeddings, indexed them in Azure AI Search, and connected retrieval results to Azure OpenAI. "
            "I compared keyword-only retrieval with hybrid keyword and vector retrieval because exact policy terms "
            "and semantic questions both mattered. Retrieval adds latency and indexing complexity, but provides "
            "source-grounded context. I evaluated a fixed set of representative questions, checked whether expected "
            "source passages appeared in the top results, reviewed generated answers against those sources, and "
            "tracked latency separately. I would only claim a numerical improvement after recording the baseline "
            "and post-change measurements; this answer does not assert an unmeasured percentage."
        ),
    },
    {
        "name": "technically_incorrect",
        "answer": (
            "I built the RAG solution in Azure. Azure AI Search automatically trains the language model and "
            "generates all final answers itself, so Azure OpenAI or any separate language model is never needed. "
            "I did not test retrieval or compare results, but I can say accuracy was 100 percent."
        ),
    },
]


def main():
    provider = os.getenv("LLM_PROVIDER", "none").lower()
    if provider not in {"gemini", "openrouter"}:
        print("Set LLM_PROVIDER=gemini or LLM_PROVIDER=openrouter in api/.env first.")
        return 2

    results = {}
    for case in CASES:
        payload = evaluate_with_llm(QUESTION, case["answer"], CANDIDATE)
        if payload is None:
            print(f"FAIL: provider returned no evaluation for {case['name']}. Check backend logs and API quota.")
            return 2
        provider_used = payload.get("_evaluation_provider", provider)
        try:
            evaluation = apply_rubric_result(payload, provider_used)
        except Exception as exc:
            print(f"FAIL: invalid rubric output for {case['name']}: {type(exc).__name__}: {exc}")
            return 2
        results[case["name"]] = evaluation
        print(
            f"{case['name']:>22}: {evaluation.score:>3}/100 "
            f"provider={evaluation.evaluation_provider} "
            f"relevance={evaluation.relevance} technical={evaluation.technical_correctness} "
            f"ownership={evaluation.ownership} reasoning={evaluation.reasoning} "
            f"validation={evaluation.validation}"
        )
        if case["name"] == "technically_incorrect":
            print("  weaknesses:", " | ".join(evaluation.weaknesses[:3]))

    weak = results["weak"].score
    average = results["average"].score
    strong = results["strong"].score
    incorrect = results["technically_incorrect"].score
    print("\nOrdering checks:")
    print(f"  weak < strong: {weak < strong} ({weak} < {strong})")
    print(f"  technically incorrect < strong: {incorrect < strong} ({incorrect} < {strong})")
    print(f"  strong >= average: {strong >= average} ({strong} >= {average})")
    print("\nReview the feedback manually too; passing ordering checks alone does not prove model quality.")
    return 0 if weak < strong and incorrect < strong and strong >= average else 1


if __name__ == "__main__":
    raise SystemExit(main())
