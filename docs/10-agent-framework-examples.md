# 10 - Agent Framework Examples

Date: February 16, 2026

Goal: show concrete implementation differences between LangGraph, PydanticAI, and OpenHands before Phase 2.

## Quick decision view

### Pick LangGraph when

- You want explicit loop control and branching logic.
- You want durable graph state with `thread_id` checkpointing.
- You want a backend runtime designed for long-running multi-step workflows.

### Pick PydanticAI when

- You want typed inputs and outputs fast.
- You want simple tool definitions with strong validation and retries.
- You want to ship a smaller runtime surface first and grow later.

### Pick OpenHands when

- You want a ready-to-run coding agent environment now.
- You are okay operating a heavier runtime service.
- You want a full UI and headless mode out of the box.

## Example problem for all three

"Read project files, propose a patch, and run tests in a controlled loop."

---

## A. LangGraph example (workflow-first)

```python
from typing import Annotated, TypedDict

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


@tool
def list_repo_files(glob: str = "**/*.py") -> str:
    """List files in the repo matching a pattern."""
    # replace with real safe implementation
    return f"Listed files for {glob}"


@tool
def run_backend_tests() -> str:
    """Run backend tests and return summary."""
    # replace with real safe implementation
    return "52 passed"


tools = [list_repo_files, run_backend_tests]
model = ChatOpenAI(model="gpt-5-mini").bind_tools(tools)


def call_model(state: AgentState):
    response = model.invoke(state["messages"])
    return {"messages": [response]}


builder = StateGraph(AgentState)
builder.add_node("agent", call_model)
builder.add_node("tools", ToolNode(tools))

builder.add_edge(START, "agent")
builder.add_conditional_edges(
    "agent",
    tools_condition,
    {"tools": "tools", "__end__": END},
)
builder.add_edge("tools", "agent")

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "dev-session-1"}}
result = graph.invoke(
    {"messages": [{"role": "user", "content": "Plan and run test checks for my patch."}]},
    config=config,
)
print(result)
```

Why it feels different:

- You explicitly define nodes, edges, and loop exits.
- You get durable thread state with checkpointing.
- Great when you need deterministic control over iterative behavior.

Permissions model notes:

- You control permissions by controlling what each tool can do.
- Best practice is allowlisted file paths and commands only.
- Add per-tool approval gates before write or exec actions.

---

## B. PydanticAI example (typed agent-first)

```python
from dataclasses import dataclass

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext, UsageLimits, capture_run_messages


@dataclass
class DevDeps:
    repo_root: str


class PatchPlan(BaseModel):
    summary: str
    files_to_change: list[str]
    should_run_tests: bool


agent = Agent(
    "openrouter:anthropic/claude-sonnet-4-5",
    deps_type=DevDeps,
    output_type=PatchPlan,
    instructions=(
        "You are a coding assistant. Make minimal safe changes. "
        "Only use tools that are provided."
    ),
)


@agent.tool
async def list_repo_files(ctx: RunContext[DevDeps], pattern: str = "**/*.py") -> list[str]:
    """Return files from repo. Restrict to repo_root."""
    # replace with real safe implementation
    return ["backend/api/views.py", "frontend/src/app.tsx"]


@agent.tool
async def run_backend_tests(ctx: RunContext[DevDeps]) -> str:
    """Run backend tests and return summary."""
    # replace with real safe implementation
    return "52 passed"


deps = DevDeps(repo_root="/workspace")

with capture_run_messages() as messages:
    result = agent.run_sync(
        "Plan a safe patch and decide if tests are needed.",
        deps=deps,
        usage_limits=UsageLimits(request_limit=20, tool_calls_limit=40),
    )

print(result.output)
print(result.new_messages())
```

Why it feels different:

- Fast setup with strong typing and validation.
- Built-in retry and usage limit controls are straightforward.
- Easier to get a typed MVP running quickly.

Permissions model notes:

- Same core principle as LangGraph: permissions are in your tools.
- Use dependency injection (`RunContext`) to pass safe runtime handles.
- Enforce write and shell controls in the tool implementation layer.

---

## C. OpenHands example (full coding-agent runtime)

OpenHands is typically used as a runtime system, not just a Python library call.

### Docker runtime setup

```bash
export SANDBOX_VOLUMES=/absolute/path/to/repo:/workspace:rw
export LLM_MODEL="openrouter/anthropic/claude-3.5-sonnet"
export LLM_API_KEY="$OPENROUTER_API_KEY"

docker run -it --rm --pull=always \
  -e SANDBOX_RUNTIME_CONTAINER_IMAGE=docker.all-hands.dev/all-hands-ai/runtime:0.59-nikolaik \
  -e SANDBOX_VOLUMES="$SANDBOX_VOLUMES" \
  -e LLM_MODEL="$LLM_MODEL" \
  -e LLM_API_KEY="$LLM_API_KEY" \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ~/.openhands:/.openhands \
  -p 127.0.0.1:3000:3000 \
  --add-host host.docker.internal:host-gateway \
  docker.all-hands.dev/all-hands-ai/openhands:0.59
```

### Headless task mode

```bash
# inside OpenHands environment
poetry run python -m openhands.core.main \
  -t "Inspect failing tests, propose a patch, apply minimal edits, and re-run tests" \
  --selected-repo /workspace
```

Why it feels different:

- More out-of-the-box coding-agent product surface.
- Includes UI, session handling, and runtime orchestration.
- Great if you want an immediately usable coding-agent system.

Permissions model notes:

- Docker runtime is safer default than local runtime.
- Local runtime has no sandbox isolation and should be treated as high risk.
- Restrict mounted volumes and network scope in production-like environments.

---

## Recommendation for DjangoStarter

If your priority is open-source, modular, and deeply controllable integration:

1. Start with **LangGraph** for runtime orchestration.
2. Add **PydanticAI-style typed validation patterns** in tool inputs and outputs where useful.
3. Keep OpenHands as an optional external integration path, not core embedded runtime.

This keeps the starter lightweight and flexible while preserving advanced control.

## Questions to answer before Phase 2

1. Do you want graph-first control as a platform feature, or fastest typed MVP first?
2. Do you need durable resumable sessions on day one?
3. Should code-edit tools be admin-only in dev mode, or available to trusted team users?
4. Do you want self-hosted only, or optional managed runtime support?

## Sources

- LangGraph docs and references:
  - [How to create a ReAct agent from scratch](https://langchain-ai.github.io/langgraph/how-tos/react-agent-from-scratch/)
  - [How to add thread-level persistence](https://langchain-ai.github.io/langgraph/how-tos/persistence-functional/)
  - [LangGraph reference](https://langchain-ai.github.io/langgraph/reference/)
- PydanticAI docs:
  - [Models overview](https://ai.pydantic.dev/models/)
  - [OpenRouter provider](https://ai.pydantic.dev/models/openrouter/)
  - [Messages and chat history](https://ai.pydantic.dev/message-history/)
  - [Tools API](https://ai.pydantic.dev/api/tools/)
  - [Usage limits API](https://ai.pydantic.dev/api/usage/)
- OpenHands docs:
  - [Local setup](https://docs.all-hands.dev/usage/local-setup)
  - [Docker runtime](https://docs.all-hands.dev/openhands/usage/runtimes/docker)
  - [Local runtime warning](https://docs.all-hands.dev/modules/usage/runtimes/local)
  - [Configuration options](https://docs.all-hands.dev/openhands/usage/configuration-options)
  - [Headless mode](https://docs.all-hands.dev/openhands/usage/run-openhands/headless-mode)
  - [OpenRouter configuration](https://docs.all-hands.dev/usage/llms/openrouter)
