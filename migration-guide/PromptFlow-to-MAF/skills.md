# Skills — PromptFlow-to-MAF Migration Guide

Instructions for AI coding agents working on the Prompt Flow → Microsoft Agent Framework migration guide.

---

## Context

Prompt Flow is being retired (feature freeze 17 Apr 2026, full retirement 17 Apr 2027). This folder contains a 5-phase, hands-on migration guide with runnable Python samples that move a Prompt Flow workload to **Microsoft Agent Framework (MAF) 1.0 GA** (released 2 Apr 2026).

Target audience: teams running Prompt Flow on Azure AI Foundry or Azure Machine Learning.

---

## Repository Layout

```
migration-guide/PromptFlow-to-MAF/
├── README.md                  # Top-level overview and setup instructions
├── TROUBLESHOOTING.md         # Common migration errors and fixes
├── requirements.txt           # Python dependencies (MAF 1.0 GA, eval SDK, etc.)
├── .env.example               # Environment variable template
├── .github/ISSUE_TEMPLATE/    # Issue template for migration problems
├── phase-1-audit/             # Export PF flow YAML; map nodes to MAF equivalents
│   ├── README.md
│   └── node-mapping.md        # Full PF → MAF concept mapping table
├── phase-2-rebuild/           # Re-implement flows using WorkflowBuilder + Executor
│   ├── README.md
│   └── 01–07_*.py             # Progressive samples (linear → multi-agent)
├── phase-3-validate/          # Side-by-side parity scoring with Azure AI Eval SDK
│   ├── README.md
│   ├── parity_check.py        # Single-row parity scorer
│   └── parity_check_batch.py  # Concurrent batch parity scorer
├── phase-4-migrate-ops/       # Tracing, deployment, CI/CD
│   ├── 4a-tracing/            # OpenTelemetry + Application Insights setup
│   ├── 4b-deployment/         # FastAPI wrapper, Dockerfile, Container Apps
│   └── 4c-cicd/               # GitHub Actions quality gate (evaluate.yml)
└── phase-5-cutover/           # Traffic switch + PF decommissioning script
    └── cutover.sh             # Automated (or dry-run) PF retirement
```

---

## Migration Phases — Quick Reference

| Phase | Goal | Key Output |
|-------|------|------------|
| **1 — Audit & Map** | Understand and document the existing PF flow | Exported `flow.dag.yaml`, completed node-mapping table |
| **2 — Rebuild** | Re-implement in MAF using `WorkflowBuilder` + `Executor` | Working `.py` files mirroring PF behaviour |
| **3 — Validate** | Confirm semantic parity with `SimilarityEvaluator` | `parity_results.csv` with mean score ≥ 3.5 |
| **4 — Migrate Ops** | Replace PF operational infra (tracing, hosting, CI/CD) | App Insights traces, Container App, GitHub Actions gate |
| **5 — Cut Over** | Route traffic to MAF; retire PF endpoints | `cutover.sh` executed; PF connections deleted |

Always work through phases in order. Do not skip ahead.

---

## Core MAF Concepts

These are the foundational abstractions agents should understand when generating or modifying code in this guide:

| Concept | Description |
|---------|-------------|
| **Executor** | A class with a `@handler` method that performs one logical step (replaces a PF "node"). |
| **WorkflowBuilder** | Fluent builder that registers executors and wires them with `.add_edge()`, `.add_fan_out_edges()`, `.add_fan_in_edges()`, then `.build()`. |
| **WorkflowContext** | Type-parameterised context passed to handlers: `WorkflowContext[SendType]` to send downstream, `WorkflowContext[Never, YieldType]` to yield final output, `WorkflowContext[SendType, YieldType]` for both. |
| **Agent** | Created via `AzureOpenAIChatClient().as_agent(name=..., instructions=...)` or `FoundryChatClient(...).as_agent(...)`. Replaces PF LLM nodes. |
| **Context Provider** | E.g. `AzureAISearchContextProvider` — injects RAG context into an agent. Replaces PF Embed Text + Vector Lookup nodes. |
| **SimilarityEvaluator** | From `azure-ai-evaluation`. Scores semantic similarity 1–5 between PF and MAF outputs. |

### Import Paths (MAF 1.0 GA)

```python
from agent_framework import Agent, Executor, WorkflowBuilder, WorkflowContext, handler
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework.foundry import FoundryChatClient
from agent_framework.azure_ai_search import AzureAISearchContextProvider
```

> **Breaking change**: `agent-framework-azure-ai` was removed in 1.0. Use `agent-framework-foundry` instead.

---

## Code Patterns

### Every sample follows this structure

1. **Define Executors** — one class per logical step, each with a `@handler` method.
2. **Build the Workflow** — connect executors via `WorkflowBuilder` and `.add_edge()`.
3. **Run** — `await workflow.run(input)`, read output from `result.get_outputs()`.

### Naming Conventions

- Executor class names: `<Purpose>Executor` (e.g. `InputExecutor`, `LLMExecutor`, `RouterExecutor`).
- Workflow names: descriptive PascalCase string (e.g. `"LinearWorkflow"`, `"RAGPipeline"`).
- Sample files: `NN_<pattern>.py` numbered by complexity (01–07).

### Message Construction

```python
# Correct (MAF 1.0 GA):
message = Message(role="user", contents=["Hello"])

# Incorrect (removed in 1.0):
message = Message(role="user", text="Hello")  # TypeError
```

### Workflow Output

Terminal executors must call `ctx.yield_output()`, not just `ctx.send_message()`:

```python
# Correct — yields a workflow output:
async def handle(self, text: str, ctx: WorkflowContext[Never, str]) -> None:
    await ctx.yield_output(text)
```

### Environment Variables

All credentials are read from `.env` via `load_dotenv()`. Never hard-code secrets. See `.env.example` for the full list:

- `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME`
- `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_MODEL` (for Foundry project endpoints)
- `AZURE_AI_SEARCH_ENDPOINT`, `AZURE_AI_SEARCH_INDEX_NAME`, `AZURE_AI_SEARCH_API_KEY`
- `APPLICATIONINSIGHTS_CONNECTION_STRING` (tracing, Phase 4+)

---

## Modifying or Adding Samples

When adding a new sample to `phase-2-rebuild/`:

1. Number it sequentially after the last file (e.g. `08_<pattern>.py`).
2. Start with a docstring that names the Prompt Flow pattern being replaced.
3. Follow the three-step structure (Executors → Builder → Run).
4. Add the sample to the table in `phase-2-rebuild/README.md`.
5. If it introduces a new PF concept, add a row to `phase-1-audit/node-mapping.md`.

When editing existing samples:

- Keep the `load_dotenv()` call at the top, before any client instantiation.
- Preserve the `if __name__ == "__main__"` block so samples stay independently runnable.
- Use `asyncio.run(main())` as the entry point.

---

## Validation & Parity Checks

- **Single-row**: `python phase-3-validate/parity_check.py`
- **Batch (concurrent)**: `python phase-3-validate/parity_check_batch.py`
- Parity threshold: mean similarity ≥ **3.5** before proceeding to Phase 4.
- `SimilarityEvaluator` requires `model_config` with `azure_endpoint`, `api_key`, and `azure_deployment`.
- Correct kwargs: `evaluator(query=question, response=maf_answer, ground_truth=pf_answer)`.

---

## Deployment

- **FastAPI wrapper**: `phase-4-migrate-ops/4b-deployment/app.py`
- **Dockerfile**: `phase-4-migrate-ops/4b-deployment/Dockerfile`
- **Deploy script**: `phase-4-migrate-ops/4b-deployment/deploy.sh` (Azure Container Apps)
- **CI/CD quality gate**: `phase-4-migrate-ops/4c-cicd/evaluate.yml` (GitHub Actions)
- **Tracing**: `configure_azure_monitor()` must be called **before** any `workflow.run()`.

---

## Troubleshooting Quick Reference

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `ModuleNotFoundError: agent_framework` | Package not installed or RC conflict | `pip uninstall ... -y && pip install agent-framework>=1.0.0` |
| `401 Unauthorized` on Azure OpenAI | Missing/wrong API key or endpoint | Check `.env`; ensure endpoint ends with `/` |
| `workflow.run()` returns empty outputs | Terminal executor not calling `ctx.yield_output()` | Use `WorkflowContext[Never, T]` and call `ctx.yield_output()` |
| `TypeError` on `Message(text=...)` | Removed in 1.0 | Use `Message(role=..., contents=[...])` |
| Workflow hangs | Circular edge definition | Check `add_edge()` calls for cycles; set `max_iterations` |
| Low parity scores (< 2.0) | Wrong evaluator kwargs | Use `query=`, `response=`, `ground_truth=` |
| No traces in App Insights | `configure_azure_monitor()` called too late | Call at application startup, before `workflow.run()` |

For the full list, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).

---

## Common Pitfalls

1. **Mixing `--pre` and non-`--pre` installs** — Core MAF packages are GA; preview connectors (e.g. `agent-framework-copilotstudio`) still need `--pre` on a separate `pip install`.
2. **Using `AzureOpenAIChatClient` with a Foundry endpoint** — Foundry project endpoints (`*.services.ai.azure.com`) require `FoundryChatClient`, not `AzureOpenAIChatClient`.
3. **Fan-in missing a branch** — Every executor in `add_fan_out_edges()` must also appear in `add_fan_in_edges()`, or the aggregator fires early.
4. **Condition functions receiving unexpected types** — Conditions receive the exact value passed to `ctx.send_message()`. Match on that value, not a transformed version.
5. **Skipping Phase 3** — Always validate parity before migrating ops. Low-scoring outputs indicate unmigrated logic.

---

## External References

- [MAF 1.0 GA announcement](https://devblogs.microsoft.com/agent-framework/microsoft-agent-framework-version-1-0/)
- [MAF Python API docs](https://learn.microsoft.com/en-us/agent-framework/)
- [MAF Workflows documentation](https://learn.microsoft.com/en-us/agent-framework/workflows/executors)
- [Azure AI Evaluation SDK](https://learn.microsoft.com/en-us/python/api/overview/azure/ai-evaluation-readme)
- [MAF GitHub repository](https://github.com/microsoft/agent-framework)
- [MAF Discord community](https://discord.gg/b5zjErwbQM)
