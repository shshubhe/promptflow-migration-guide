"""
Compares captured Prompt Flow outputs against the new MAF workflow using
SimilarityEvaluator from the Azure AI Evaluation SDK.

Scores are 1–5 (5 = most similar). Rows below SIMILARITY_THRESHOLD are
flagged for manual review and the full results are saved to parity_results.csv.

Usage:
    python parity_check.py

Prerequisites:
    pip install azure-ai-evaluation pandas
    CSV format: columns 'question' and 'pf_output' (see test_inputs.csv.example)
    Update the workflow import below to point at your module.
"""

import asyncio
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from azure.ai.evaluation import SimilarityEvaluator

# ── REQUIRED: update this import to point at your workflow module. ────────────
# Example: from phase_2_rebuild.linear_flow import workflow
# from your_module import workflow
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_CSV_PATH = SCRIPT_DIR / "test_inputs.csv"
OUTPUT_CSV_PATH = SCRIPT_DIR / "parity_results.csv"
ENV_PATH = SCRIPT_DIR.parent / ".env"

load_dotenv(dotenv_path=ENV_PATH)

# Startup guard: fail fast with a clear message if the workflow was not imported.
if "workflow" not in globals():
    raise ImportError(
        "workflow is not defined. Update the import at the top of this file to "
        "point at your MAF workflow module.\n"
        "Example: from phase_2_rebuild.linear_flow import workflow"
    )

# SimilarityEvaluator requires model_config in GA (1.16+).
model_config = {
    "azure_endpoint": os.environ["AZURE_OPENAI_ENDPOINT"],
    "api_key": os.environ["AZURE_OPENAI_API_KEY"],
    "azure_deployment": os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"],
}

SIMILARITY_THRESHOLD = 3.5  # Scores below this are flagged for review (scale: 1–5)

evaluator = SimilarityEvaluator(model_config=model_config, threshold=3)
if not INPUT_CSV_PATH.exists():
    raise FileNotFoundError(
        f"Missing input file: {INPUT_CSV_PATH}\n"
        "Copy test_inputs.csv.example to test_inputs.csv and replace it with your "
        "captured Prompt Flow outputs before running parity_check.py."
    )

test_data = pd.read_csv(INPUT_CSV_PATH)
results = []


async def run_parity_check():
    for _, row in test_data.iterrows():
        question = row["question"]
        pf_answer = row["pf_output"]

        maf_result = await workflow.run(question)
        maf_answer = maf_result.get_outputs()[0]

        # evaluator() returns {"similarity": float, "gpt_similarity": float}.
        # Use "similarity" — "gpt_similarity" is deprecated in GA.
        score_dict = evaluator(
            query=question,
            response=maf_answer,
            ground_truth=pf_answer,
        )
        results.append({
            "question": question,
            "pf_output": pf_answer,
            "maf_output": maf_answer,
            "similarity": score_dict["similarity"],
        })

    df = pd.DataFrame(results)
    mean_score = df["similarity"].mean()
    print(f"\nMean similarity: {mean_score:.2f} / 5.0")

    regressions = df[df["similarity"] < SIMILARITY_THRESHOLD]
    if regressions.empty:
        print("All outputs meet the quality threshold. Ready for Phase 4.")
    else:
        print(f"\n{len(regressions)} answer(s) to review:")
        print(regressions[["question", "similarity"]].to_string(index=False))

    df.to_csv(OUTPUT_CSV_PATH, index=False)
    print(f"\nFull results saved to {OUTPUT_CSV_PATH}")


if __name__ == "__main__":
    asyncio.run(run_parity_check())
