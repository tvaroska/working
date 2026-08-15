"""Call-and-return Bridge consumer that surfaces the structured ``ExchangeTurn``.

S1-2 switches the address agent from a transfer *sub-agent* to an ``AgentTool`` so
control **returns** to the caller with the collected ``ExchangeTurn`` available as
the tool result (needed by the ``is_satisfied`` gate in S1-3 and the Collect loop
in S1-4).

A *vanilla* ``AgentTool`` is insufficient here: its ``run_async`` builds the return
value from ``_part_to_text`` over the **last** event's content parts only, and
``_part_to_text`` ignores ``inline_data``. The Bridge's completed ``ExchangeTurn``
arrives as an ``inline_data`` DataPart, so a plain ``AgentTool(RemoteA2aAgent)``
would return an empty string — the payload is lost. :class:`BridgeAgentTool`
therefore keeps the native ``RemoteA2aAgent`` underneath (streaming/pause machinery
intact) but overrides ``run_async`` to scan **all** yielded events and return the
typed ``ExchangeTurn`` dict.

Coupling note (adr-0001 SDK-risk): this copies ``AgentTool.run_async``'s
Runner-setup boilerplate, which is coupled to ADK internals; the seam suite is what
catches drift on an SDK bump.

S1-4/S1-5 concern (not solved here): ``AgentTool`` runs the wrapped agent in a
fresh ``InMemorySessionService`` + new session per call, so native
``LongRunningFunctionTool`` park/resume that relies on the peer ``task_id`` /
``context_id`` persisting on the caller session does not survive across tool
invocations. Irrelevant in S1-2 (single call-and-return, ``park=False``).
"""

from typing import Any

from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.tool_context import ToolContext
from typing_extensions import override

from contract import ExchangeTurn

from .wire import extract_exchange_turn

# Content value is irrelevant — the send-path interceptor overwrites the outbound
# parts with the CollectRequest DataPart — but it must be non-empty text, or
# RemoteA2aAgent early-returns before the interceptor runs (empty-parts guard).
_KICKOFF_TEXT = "Collect the requested proof."


class BridgeAgentTool(AgentTool):
    """An ``AgentTool`` over the Bridge that returns the ``ExchangeTurn`` dict.

    Behaves like ``AgentTool`` except that after running the wrapped
    ``RemoteA2aAgent`` it recovers the completed ``ExchangeTurn`` from the event
    stream's ``inline_data`` DataPart and returns it as a JSON-serializable dict.
    Falls back to the parent's text/error behavior when no ``ExchangeTurn`` is
    present.
    """

    def __init__(self, agent, *, skip_summarization: bool = True, **kwargs):
        # The structured dict is the answer; skip LLM re-narration of the ledger
        # by default (the caller post-processes the dict, not prose).
        super().__init__(agent, skip_summarization=skip_summarization, **kwargs)

    @override
    async def run_async(
        self,
        *,
        args: dict[str, Any],
        tool_context: ToolContext,
    ) -> Any:
        from google.adk.memory.in_memory_memory_service import (
            InMemoryMemoryService,
        )
        from google.adk.runners import Runner
        from google.adk.sessions.in_memory_session_service import (
            InMemorySessionService,
        )
        from google.adk.tools._forwarding_artifact_service import (
            ForwardingArtifactService,
        )
        from google.adk.utils.context_utils import Aclosing
        from google.genai import types

        if self.skip_summarization:
            tool_context.actions.skip_summarization = True

        # Non-empty kickoff text so RemoteA2aAgent does not early-return; the
        # send-path interceptor replaces these parts with the CollectRequest.
        content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=_KICKOFF_TEXT)],
        )

        invocation_context = tool_context._invocation_context
        parent_app_name = (
            invocation_context.app_name if invocation_context else None
        )
        child_app_name = parent_app_name or self.agent.name
        plugins = (
            invocation_context.plugin_manager.plugins
            if self.include_plugins
            else None
        )
        runner = Runner(
            app_name=child_app_name,
            agent=self.agent,
            artifact_service=ForwardingArtifactService(tool_context),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
            credential_service=invocation_context.credential_service,
            plugins=plugins,
        )
        if self.include_plugins:
            runner.plugin_manager.set_skip_closing_plugins(True)

        state_dict = {
            k: v
            for k, v in tool_context.state.to_dict().items()
            if not k.startswith("_adk")  # Filter out adk internal states
        }
        session = await runner.session_service.create_session(
            app_name=child_app_name,
            user_id=invocation_context.user_id,
            state=state_dict,
        )

        events: list = []
        last_content = None
        last_error_message = None
        try:
            async with Aclosing(
                runner.run_async(
                    user_id=session.user_id,
                    session_id=session.id,
                    new_message=content,
                )
            ) as agen:
                async for event in agen:
                    events.append(event)
                    # Forward state delta to the parent session (as AgentTool does).
                    if event.actions.state_delta:
                        tool_context.state.update(event.actions.state_delta)
                    if event.error_message:
                        last_error_message = event.error_message
                    if event.content:
                        last_content = event.content
        finally:
            await runner.close()

        # Primary path: return the structured ExchangeTurn dict.
        turn = extract_exchange_turn(events)
        if turn is not None:
            # Validate + re-serialize for a guaranteed-clean, JSON-safe shape.
            return ExchangeTurn.model_validate(turn).model_dump(mode="json")

        # Fallback: mirror AgentTool's text/error behavior.
        if last_content is None or last_content.parts is None:
            return last_error_message or ""
        merged_text = "\n".join(
            p.text for p in last_content.parts if getattr(p, "text", None)
        )
        if not merged_text and last_error_message:
            return last_error_message
        return merged_text
