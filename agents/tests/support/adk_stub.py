"""Test double for driving the real ``LlmAgent`` offline (no Gemini call).

:class:`ScriptedTransferModel` is a ``BaseLlm`` that keys off a call counter to
drive ADK's agent-transfer flow deterministically: call #1 emits a
``transfer_to_agent`` ``function_call`` handing control to the Bridge sub-agent;
any later call emits a fixed final text part (a safety net — after transfer the
sub-agent normally produces the output and the parent model is not re-invoked).
This lets the real ``google-adk`` ``LlmAgent`` + ``Runner`` run the true
transfer -> native ``RemoteA2aAgent`` path with no API key.
"""

from collections.abc import AsyncGenerator

from google.adk.models import BaseLlm, LlmResponse
from google.genai import types
from pydantic import PrivateAttr


class ScriptedTransferModel(BaseLlm):
    """A ``BaseLlm`` stub that scripts one ``transfer_to_agent`` call."""

    model: str = "scripted-stub"
    target_agent: str = "document_bridge"
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
                        function_call=types.FunctionCall(
                            name="transfer_to_agent",
                            args={"agent_name": self.target_agent},
                        )
                    )
                ],
            )
        else:
            content = types.Content(
                role="model",
                parts=[types.Part(text=self.final_text)],
            )
        yield LlmResponse(content=content)
