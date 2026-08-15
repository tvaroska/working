"""Test doubles for driving the real ``LlmAgent`` offline (no sockets, no API key).

- :class:`ScriptedToolCallModel` is a ``BaseLlm`` that keys off a call counter to
  drive ADK's function-calling loop deterministically: call #1 emits the tool
  ``function_call``; later calls emit a fixed final text part. This lets the real
  ``LlmAgent`` + ``Runner`` run the true tool->port path with no Gemini call.
- :class:`FakeBridgeClient` is a ``BridgeClient`` port double returning a canned
  ``gov-id-clean`` turn and recording the request it received.

Importing ``agents.mock_bridge`` from *test* code is fine (the agent itself must
never import it — that discipline is enforced in ``agents.address``).
"""

from collections.abc import AsyncGenerator

from google.adk.models import BaseLlm, LlmResponse
from google.genai import types
from pydantic import PrivateAttr

from agents.mock_bridge import build_exchange_turn, load_gov_id_clean_entry
from bridge_client import BridgeClient
from contract import CollectRequest, ExchangeTurn


class ScriptedToolCallModel(BaseLlm):
    """A ``BaseLlm`` stub that scripts one function call then a final text part."""

    model: str = "scripted-stub"
    tool_name: str = "collect_address_proof"
    final_text: str = "Collected the address proof."

    _call_count: int = PrivateAttr(default=0)

    async def generate_content_async(
        self,
        llm_request,
        stream: bool = False,
    ) -> AsyncGenerator[LlmResponse, None]:
        self._call_count += 1
        if self._call_count == 1:
            content = types.Content(
                role="model",
                parts=[
                    types.Part(
                        function_call=types.FunctionCall(name=self.tool_name, args={})
                    )
                ],
            )
        else:
            content = types.Content(
                role="model",
                parts=[types.Part(text=self.final_text)],
            )
        yield LlmResponse(content=content)


class FakeBridgeClient(BridgeClient):
    """A ``BridgeClient`` port double returning a canned ``gov-id-clean`` turn."""

    def __init__(self, *, context_id: str = "fake-ctx-001") -> None:
        self._context_id = context_id
        self.requests: list[CollectRequest] = []

    async def collect(self, request: CollectRequest) -> ExchangeTurn:
        self.requests.append(request)
        entry = load_gov_id_clean_entry()
        return build_exchange_turn(self._context_id, entry)
