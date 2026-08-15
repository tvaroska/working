"""The address-verification ``LlmAgent`` factory and its Bridge-port tool wiring.

This is the agent half of the M0 contract tracer bullet: a real ``google-adk``
``LlmAgent`` (day-one platform bet — ADR-0001) that, on one turn, requests the
``address-proof`` document for party ``jordan-lee`` through the injected
``BridgeClient`` port and renders the returned ``id`` + structured info.

The party and skill are hard-coded (no skills registry in M0). The agent depends
only on the ``BridgeClient`` port; the factory injects a concrete client and the
tool closes over it, so the Sprint-1 mock->real swap is a no-op for the agent.
"""

import os

from google.adk.agents import LlmAgent
from google.adk.models import BaseLlm
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.genai import types

from bridge_client import BridgeClient, BridgeClientError
from contract import CollectRequest

from .render import collection_to_dict

PARTY = "jordan-lee"
SKILL = "address-proof"
DEFAULT_MODEL = os.environ.get("ADDRESS_AGENT_MODEL", "gemini-2.0-flash")

INSTRUCTION = (
    "You are an address-verification agent. Call the `collect_address_proof` tool "
    "exactly once to request the address-proof document for the party, then present "
    "the returned document id and its structured fields."
)

APP_NAME = "address"


def build_address_agent(
    bridge_client: BridgeClient,
    *,
    model: str | BaseLlm = DEFAULT_MODEL,
) -> LlmAgent:
    """Build the address-verification ``LlmAgent`` wired to a ``BridgeClient``.

    Args:
        bridge_client: The port the tool calls to reach the Bridge. Injected so
            the concrete adapter (mock now, real Bridge in Sprint 1) can be
            swapped with no agent-code change.
        model: A model id ``str`` (prod, via ``ADDRESS_AGENT_MODEL``) or a
            ``BaseLlm`` instance (tests inject a scripted stub for a hermetic run).

    Returns:
        A real ``google-adk`` ``LlmAgent`` with exactly one ``FunctionTool``
        (``collect_address_proof``) closing over ``bridge_client``.
    """

    async def collect_address_proof() -> dict:
        """Request the address-proof document for the party.

        Returns the collected document id and structured fields.
        """
        request = CollectRequest(party=PARTY, skill=SKILL)
        try:
            turn = await bridge_client.collect(request)
        except BridgeClientError as exc:
            return {"error": str(exc)}
        return collection_to_dict(turn)

    tool = FunctionTool(collect_address_proof)

    return LlmAgent(
        name="address_agent",
        description="Address verification agent (M0 tracer bullet).",
        model=model,
        instruction=INSTRUCTION,
        tools=[tool],
        output_key="address_result",
    )


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
