"""
Migrates a Prompt Flow conditional (If) node.

In MAF, branching is expressed by passing a condition callable to add_edge().
An edge fires only when the condition returns True for the outgoing message.

Prompt Flow equivalent:
    activate_config: ${classify.output} == "safe"
"""

import asyncio

from dotenv import load_dotenv
from typing_extensions import Never

from agent_framework import Executor, WorkflowBuilder, WorkflowContext, handler

load_dotenv()


class ClassifyExecutor(Executor):
    """Classifies input and sends a tagged payload downstream.

    Replace the body of classify() with your real classification logic
    (e.g. an LLM call, a rules engine, a model inference call).
    """

    @handler
    async def classify(self, text: str, ctx: WorkflowContext[str]) -> None:
        label = "unsafe" if "bad_word" in text.lower() else "safe"
        await ctx.send_message(f"{label}||{text}")


class SafeHandlerExecutor(Executor):
    """Handles input that passed the safety check."""

    @handler
    async def handle_safe(self, tagged: str, ctx: WorkflowContext[Never, str]) -> None:
        _, original_text = tagged.split("||", 1)
        await ctx.yield_output(f"Processed: {original_text}")


class FlaggedHandlerExecutor(Executor):
    """Handles input that failed the safety check."""

    @handler
    async def handle_flagged(self, tagged: str, ctx: WorkflowContext[Never, str]) -> None:
        _, original_text = tagged.split("||", 1)
        await ctx.yield_output(f"Flagged for review: {original_text}")


def is_safe(message: str) -> bool:
    """Condition function passed to add_edge().

    Receives the outgoing message from ClassifyExecutor.
    Returns True to fire the edge, False to suppress it.
    """
    return message.startswith("safe||")


def is_unsafe(message: str) -> bool:
    """Explicit negation of is_safe — clearer and more testable than a lambda."""
    return message.startswith("unsafe||")


# Two edges leave ClassifyExecutor — only one fires per run.
# This is the MAF equivalent of the PF If node.
workflow = (
    WorkflowBuilder(name="ConditionalWorkflow")
    .register_executor(lambda: ClassifyExecutor(id="classify"), name="Classify")
    .register_executor(lambda: SafeHandlerExecutor(id="safe"), name="SafeHandler")
    .register_executor(lambda: FlaggedHandlerExecutor(id="flagged"), name="FlaggedHandler")
    .add_edge("Classify", "SafeHandler", condition=is_safe)
    .add_edge("Classify", "FlaggedHandler", condition=is_unsafe)
    .set_start_executor("Classify")
    .build()
)


async def main():
    result_safe = await workflow.run("this is fine")
    print(result_safe.get_outputs()[0])

    result_flagged = await workflow.run("contains bad_word")
    print(result_flagged.get_outputs()[0])


if __name__ == "__main__":
    asyncio.run(main())
