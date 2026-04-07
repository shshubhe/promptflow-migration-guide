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

# Update this import to point at your workflow module.
# from your_module import workflow

load_dotenv()

configure_azure_monitor(
    connection_string=os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"]
)


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
