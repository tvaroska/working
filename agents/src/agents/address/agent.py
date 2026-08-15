"""The address-verification ``LlmAgent`` and its native Bridge tool wiring.

The address agent is a real ``google-adk`` ``LlmAgent`` (day-one platform bet —
ADR-0001) that consumes the Document Bridge through ADK's platform-native
``RemoteA2aAgent`` (adr-0009), wired as an **``AgentTool``** (call-and-return) so
control **returns** to the address agent with the collected ``ExchangeTurn`` (S1-2).
On a turn the model calls the ``document_bridge`` tool; the Bridge collects the
``address-proof`` document for the party and the structured ``ExchangeTurn`` comes
back as the tool result for the agent to post-process (the ``is_satisfied`` gate in
S1-3, the Collect loop in S1-4).

The structured ``CollectRequest`` (``{party, skill}``) is injected on the send path
by a request interceptor baked into the consumer (S1-2), independent of the model's
conversation content.

The party and skill are hard-coded (no skills registry in M0). The Bridge is
configured only by its **Agent Card URL** — the single mock->real / local->GCP
swap point, a no-op for the agent code.
"""

import os

from google.adk.agents import LlmAgent
from google.adk.models import BaseLlm
from google.adk.runners import InMemoryRunner
from google.genai import types

from bridge_client import BridgeAgentTool, build_bridge_remote_agent
from contract import CollectRequest

PARTY = "jordan-lee"
SKILL = "address-proof"
DEFAULT_MODEL = os.environ.get("ADDRESS_AGENT_MODEL", "gemini-3.7-flash")
BRIDGE_TOOL_NAME = "document_bridge"

INSTRUCTION = (
    "You are an address-verification agent. To collect the address-proof document "
    f"for party {PARTY}, call the `{BRIDGE_TOOL_NAME}` tool. When it returns the "
    "collected `ExchangeTurn`, present the document id and its structured fields."
)

APP_NAME = "address"


def _default_card_url() -> str:
    """Resolve the Bridge Agent Card URL from the environment.

    ``BRIDGE_CARD_URL`` wins; otherwise it is derived from ``BRIDGE_BASE_URL``
    (default ``http://127.0.0.1:8080``) + the well-known agent-card path.
    """
    explicit = os.environ.get("BRIDGE_CARD_URL")
    if explicit:
        return explicit
    base = os.environ.get("BRIDGE_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
    return f"{base}/.well-known/agent-card.json"


def build_address_agent(
    bridge_card_url: str | None = None,
    *,
    model: str | BaseLlm = DEFAULT_MODEL,
) -> LlmAgent:
    """Build the address-verification ``LlmAgent`` with the Bridge as a tool.

    Args:
        bridge_card_url: URL of the Bridge's Agent Card. This is the single swap
            point between mock/real and local/GCP; defaults to the environment
            (``BRIDGE_CARD_URL`` / ``BRIDGE_BASE_URL``).
        model: A model id ``str`` (prod, via ``ADDRESS_AGENT_MODEL``) or a
            ``BaseLlm`` instance (tests inject a scripted stub for a hermetic run).

    Returns:
        A real ``google-adk`` ``LlmAgent`` whose sole tool is a
        ``BridgeAgentTool`` wrapping a ``RemoteA2aAgent`` (``document_bridge``)
        consuming the Bridge over A2A (call-and-return).
    """
    card_url = bridge_card_url or _default_card_url()
    bridge = build_bridge_remote_agent(
        card_url,
        name=BRIDGE_TOOL_NAME,
        collect_request=CollectRequest(party=PARTY, skill=SKILL),
    )

    return LlmAgent(
        name="address_agent",
        description="Address verification agent (M0 tracer bullet).",
        model=model,
        instruction=INSTRUCTION,
        tools=[BridgeAgentTool(bridge)],
        output_key="address_result",
    )


root_agent = build_address_agent()
"""Module-level agent for the ADK dev UI (``adk web``) and ADK deploy tooling.

ADK's agent loader discovers a package by importing it and reading a module-level
``root_agent``. Building it here is side-effect-free — ``RemoteA2aAgent`` only
stores the card URL (resolved from ``BRIDGE_CARD_URL`` / ``BRIDGE_BASE_URL``); no
network call happens until a turn runs. Vertex AI credentials/region come from the
agent's ``.env`` (loaded by ``adk web``) or the ambient environment.
"""


async def run_once(
    agent: LlmAgent,
    *,
    user_message: str = "Collect the address proof.",
) -> str:
    """Drive the agent for one turn and return the final response text.

    Builds an ``InMemoryRunner``, creates a session, and iterates the event
    stream, returning the text of the final response. Reusable by ``__main__``
    and by tests.
    """
    runner = InMemoryRunner(agent, app_name=APP_NAME)
    user_id = PARTY
    session_id = "m0-tracer"
    await runner.session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    new_message = types.Content(role="user", parts=[types.Part(text=user_message)])
    final_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=new_message,
    ):
        if event.content and event.content.parts:
            text = "".join(part.text or "" for part in event.content.parts)
            if text:
                final_text = text
    return final_text
