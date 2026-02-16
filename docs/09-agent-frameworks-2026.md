# 09 Open Source Agent Frameworks (Late 2025 to 2026)

Date: February 16, 2026

## Recommendation summary

### Winner for DjangoStarter Phase 2

**LangGraph (Python backend) + lightweight React widget frontend**

Why this wins:

1. Durable state and controllable loops fit code-editing agents.
2. Strong Python ecosystem fit for Django-first teams.
3. Active release cadence into 2026.
4. Works well with model-provider abstraction and OpenAI-compatible endpoints via integrations.

### Short recommended list

1. **LangGraph**: best general-purpose fit for durable coding-agent workflows.
2. **OpenHands**: strongest coding-agent specialization, heavier runtime footprint.
3. **PydanticAI**: excellent typed agent layer with explicit OpenRouter support.

## Selection criteria

- Open source project health and release recency
- Fit for coding agent loops and tool calls
- Python-first or strong Python support
- Compatibility with self-hosted deployment
- Integration path to OpenAI-compatible providers

## Comparison matrix

| Framework | Primary Use | Latest release signal | Strength | Tradeoff | Fit for this repo |
|---|---|---|---|---|---|
| LangGraph | Stateful agent orchestration | `sdk==0.3.6` published 2026-02-14 | Durable execution, memory, human-in-loop, production graph control | More design effort than simple agent wrappers | **Best overall** |
| OpenHands | Coding agent platform | `1.3.0` published 2026-02-02 | Strong software-engineering agent focus and tooling | Heavy runtime and broader platform footprint | Strong for advanced dev mode |
| PydanticAI | Typed Python agents | `v1.59.0` published 2026-02-14 | Type-safe outputs, clean Python DX, explicit OpenRouter model support | Smaller ecosystem than LangGraph | Excellent typed layer |
| CrewAI | Multi-agent orchestration | `1.9.3` published 2026-01-30 | Easy role-based multi-agent pipelines | Can become complex fast without strong guardrails | Good for workflow-heavy teams |
| LlamaIndex | Data-aware agent framework | `v0.14.14` published 2026-02-10 | Strong RAG and knowledge workflows | More data-centric than coding-agent-centric | Good for context-heavy assistants |
| AutoGen | Multi-agent research and production patterns | `python-v0.7.5` published 2025-09-30 | Mature multi-agent conversation patterns | Recent cadence appears slower than top alternatives | Useful fallback |
| smolagents | Lightweight agent framework | `v1.24.0` published 2026-01-16 | Simple API, compact framework, good experimentation speed | Less batteries-included durability than LangGraph | Good lightweight option |
| Agno | Full agent runtime and app stack | `v2.5.2` published 2026-02-15 | Fast startup, built-in runtime patterns, MCP and A2A support | Broader framework surface can increase lock-in risk | Promising, evaluate carefully |

## Architecture call for DjangoStarter

Use a two-layer model:

1. **Frontend widget** (React): chat UI, state display, action stream, optimistic status.
2. **Backend agent runtime** (Django + LangGraph): tool execution, repo-safe actions, audit logs, model routing.

This avoids browser-only fragility and keeps critical tool actions server-side.

## Guardrails for implementation

1. Agent runtime enabled only in development by default.
2. Separate hard env gate required even when debug mode is enabled.
3. Never expose arbitrary filesystem tools to non-admin users.
4. Persist conversation and tool actions server-side for shareability and auditability.
5. Keep frontend widget as optional module that can be deleted.

## Sources

- LangGraph repository: [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph)
- LangGraph releases: [Releases page](https://github.com/langchain-ai/langgraph/releases)
- LangGraph JS docs package: [@langchain/langgraph README](https://github.com/langchain-ai/langgraphjs)
- OpenHands repository: [OpenHands/OpenHands](https://github.com/OpenHands/OpenHands)
- OpenHands releases: [Releases page](https://github.com/OpenHands/OpenHands/releases)
- PydanticAI repository: [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai)
- CrewAI repository: [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI)
- CrewAI releases: [Releases page](https://github.com/crewAIInc/crewAI/releases)
- LlamaIndex repository: [run-llama/llama_index](https://github.com/run-llama/llama_index)
- LlamaIndex releases: [Releases page](https://github.com/run-llama/llama_index/releases)
- AutoGen repository: [microsoft/autogen](https://github.com/microsoft/autogen)
- smolagents repository: [huggingface/smolagents](https://github.com/huggingface/smolagents)
- smolagents releases: [Releases page](https://github.com/huggingface/smolagents/releases)
- Agno repository: [agno-agi/agno](https://github.com/agno-agi/agno)
- Agno releases: [Releases page](https://github.com/agno-agi/agno/releases)

## Notes on interpretation

- Release dates and project activity were verified on February 16, 2026.
- OpenAI-compatible provider compatibility is inferred from each framework's model provider integrations unless explicitly documented as OpenRouter-native.
