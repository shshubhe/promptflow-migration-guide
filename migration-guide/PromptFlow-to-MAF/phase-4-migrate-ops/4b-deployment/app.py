"""
Wraps a MAF workflow in a FastAPI service.

Replaces: Prompt Flow Managed Online Endpoint.

The /ask endpoint accepts {"question": str} and returns {"answer": str}.

Run locally:
    uvicorn app:app --reload

Deploy:
    bash deploy.sh

Update the workflow import below to point at your module.
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from azure.monitor.opentelemetry import configure_azure_monitor

# ── REQUIRED: update this import to point at your workflow module. ────────────
# Example: from phase_2_rebuild.linear_flow import workflow
# from your_module import workflow
# ─────────────────────────────────────────────────────────────────────────────

load_dotenv()

# Startup guard: fail fast with a clear message if the workflow was not imported.
if "workflow" not in globals():
    raise ImportError(
        "workflow is not defined. Update the import at the top of this file to "
        "point at your MAF workflow module.\n"
        "Example: from phase_2_rebuild.linear_flow import workflow"
    )

# Tracing is optional — only configured when the connection string is present.
# Set APPLICATIONINSIGHTS_CONNECTION_STRING in .env to enable Application Insights.
_appinsights_conn = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
if _appinsights_conn:
    configure_azure_monitor(connection_string=_appinsights_conn)


class QuestionRequest(BaseModel):
    question: str


class AnswerResponse(BaseModel):
    answer: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="MAF Workflow Service", lifespan=lifespan)


@app.post("/ask", response_model=AnswerResponse)
async def ask(payload: QuestionRequest):
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    result = await workflow.run(payload.question.strip())
    outputs = result.get_outputs()

    if not outputs:
        raise HTTPException(status_code=500, detail="Workflow produced no output.")

    return AnswerResponse(answer=outputs[0])
