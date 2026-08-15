"""Test doubles for driving the real ``LlmAgent`` offline (no Gemini call).

:class:`ScriptedToolCallModel` drives the S1-2 call-and-return flow: call #1 emits
a ``function_call`` to the ``document_bridge`` **tool** (args are ignored — the
send-path interceptor supplies the ``CollectRequest``); any later call emits a
fixed final text part (a safety net — with ``skip_summarization=True`` the model is
usually not re-invoked after the tool returns). This lets the real ``google-adk``
``LlmAgent`` + ``Runner`` run the true native ``RemoteA2aAgent`` path with no API
key.

:class:`ScriptedLoopModel` drives the S1-4 Collect loop and genuinely **routes on
the authoritative gate verdict** (not a fixed script): it inspects the most recent
``function_response`` in the request and picks the next action — collect, check the
gate, chase again, or finish — so the loop length is data-driven by
``check_completeness``'s ``done`` flag, exactly the "LLM routes, code decides" split.
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


def _latest_function_response(llm_request):
    """Return the most recent ``FunctionResponse`` in the request, or ``None``.

    Scans ``llm_request.contents`` back-to-front for a part carrying a
    ``function_response`` (what the loop model routes on).
    """
    for content in reversed(llm_request.contents or []):
        for part in reversed(content.parts or []):
            fr = getattr(part, "function_response", None)
            if fr is not None:
                return fr
    return None


class ScriptedLoopModel(BaseLlm):
    """A ``BaseLlm`` stub that routes the S1-4 Collect loop on the gate verdict.

    Routing rules (data-driven by the authoritative ``check_completeness`` gate):

    - no prior tool response yet -> call ``document_bridge`` (collect);
    - last response was ``document_bridge`` -> call ``check_completeness`` (route
      on the gate);
    - last response was ``check_completeness``:
        - gate ``done`` is truthy -> emit the final text (terminate);
        - otherwise -> call ``document_bridge`` again (chase the outstanding proof).
    """

    model: str = "scripted-loop-stub"
    bridge_tool_name: str = "document_bridge"
    gate_tool_name: str = "check_completeness"
    final_text: str = "Address proof collected."

    def _call(self, name: str) -> types.Content:
        return types.Content(
            role="model",
            parts=[
                types.Part(
                    function_call=types.FunctionCall(name=name, args={})
                )
            ],
        )

    async def generate_content_async(
        self,
        llm_request,
        stream: bool = False,
    ) -> AsyncGenerator[LlmResponse, None]:
        fr = _latest_function_response(llm_request)

        if fr is None:
            # Nothing collected yet -> kick off the Bridge collect.
            content = self._call(self.bridge_tool_name)
        elif fr.name == self.bridge_tool_name:
            # Just collected -> ask the authoritative gate.
            content = self._call(self.gate_tool_name)
        elif fr.name == self.gate_tool_name:
            response = dict(fr.response or {})
            # ADK may wrap a non-dict tool result under a 'result' key.
            if "done" not in response and isinstance(response.get("result"), dict):
                response = response["result"]
            if response.get("done"):
                content = types.Content(
                    role="model", parts=[types.Part(text=self.final_text)]
                )
            else:
                # Not done -> chase the outstanding proof.
                content = self._call(self.bridge_tool_name)
        else:
            # Unknown tool -> terminate rather than spin.
            content = types.Content(
                role="model", parts=[types.Part(text=self.final_text)]
            )

        yield LlmResponse(content=content)
