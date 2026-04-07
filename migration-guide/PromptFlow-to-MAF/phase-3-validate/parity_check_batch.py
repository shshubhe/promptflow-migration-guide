"""
Batched version of parity_check.py.

Runs all evaluations concurrently using asyncio.gather() instead of
sequentially. Significantly faster for test suites with 20+ rows.

Prerequisites:
    pip install azure-ai-evaluation pandas
    CSV format: columns 'question' and 'pf_output' (see test_inputs.csv.example)
    Update the workflow import below to point at your module.
"""

import asyncio
import os

import pandas as pd
from dotenv import load_dotenv
from azure.ai.evaluation import SimilarityEvaluator

# Update this import to point at your workflow module.
# from your_module import workflow

load_dotenv()

model_config = {
    "azure_endpoint": os.environ["AZURE_OPENAI_ENDPOINT"],
    "api_key": os.environ["AZURE_OPENAI_API_KEY"],
    "azure_deployment": os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"],
}

SIMILARITY_THRESHOLD = 3.5  # Scale: 1–5. Rows below this are flagged for review.

evaluator = SimilarityEvaluator(model_config=model_config, threshold=3)
test_data = pd.read_csv("test_inputs.csv")


async def evaluate_row(question: str, pf_answer: str) -> dict:
    """Runs one MAF workflow call and scores it against the PF baseline."""
    maf_result = await workflow.run(question)
    maf_answer = maf_result.get_outputs()[0]

    # evaluator() returns {"similarity": float, "gpt_similarity": float}.
    # Use "similarity" — "gpt_similarity" is deprecated in GA.
    score_dict = evaluator(
        query=question,
        response=maf_answer,
        ground_truth=pf_answer,
    )
    return {
        "question": question,
        "pf_output": pf_answer,
        "maf_output": maf_answer,
        "similarity": score_dict["similarity"],
    }


async def run_parity_check():
    tasks = [
        evaluate_row(row["question"], row["pf_output"])
        for _, row in test_data.iterrows()
    ]

    # Run all rows concurrently — much faster than sequential for large test suites.
    results = await asyncio.gather(*tasks)

    df = pd.DataFrame(results)
    mean_score = df["similarity"].mean()
    print(f"\nMean similarity: {mean_score:.2f} / 5.0")

    regressions = df[df["similarity"] < SIMILARITY_THRESHOLD]
    if regressions.empty:
        print("All outputs meet the quality threshold. Ready for Phase 4.")
    else:
        print(f"\n{len(regressions)} answer(s) to review:")
        print(regressions[["question", "similarity"]].to_string(index=False))

    df.to_csv("parity_results.csv", index=False)
    print("\nFull results saved to parity_results.csv")


if __name__ == "__main__":
    asyncio.run(run_parity_check())
