"""Test double for driving the real ``LlmAgent`` offline (no Gemini call).

:class:`ScriptedToolCallModel` drives the S1-2 call-and-return flow: call #1 emits
a ``function_call`` to the ``document_bridge`` **tool** (args are ignored — the
send-path interceptor supplies the ``CollectRequest``); any later call emits a
fixed final text part (a safety net — with ``skip_summarization=True`` the model is
usually not re-invoked after the tool returns). This lets the real ``google-adk``
``LlmAgent`` + ``Runner`` run the true native ``RemoteA2aAgent`` path with no API
key.
"""

from collections.abc import AsyncGenerator

from google.adk.models import BaseLlm, LlmResponse
from google.genai import types
from pydantic import PrivateAttr


class ScriptedToolCallModel(BaseLlm):
    """A ``BaseLlm`` stub that scripts one ``document_bridge`` tool call."""

    model: str = "scripted-stub"
    tool_name: str = "document_bridge"
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
                            name=self.tool_name,
                            args={"request": "Collect the address proof."},
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
