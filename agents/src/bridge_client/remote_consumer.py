"""The native ``RemoteA2aAgent`` Bridge consumer (adr-0009).

The demos consume the Bridge through ADK's platform-native ``RemoteA2aAgent``
(the M0 hand-rolled ``BridgeClient`` poll loop was removed once the wire contract
was validated — see the adr-0009 amendment). The native construct gives us the two
long-running mechanisms for free:

- **progress** — a streamed ``TaskStatusUpdateEvent`` with a non-empty
  ``status.message`` surfaces as a thought event;
- **park/resume** — an ``INPUT_REQUIRED`` (or ``AUTH_REQUIRED``) task is turned
  into a mock ``LongRunningFunctionTool`` call that pauses the ADK Runner; a
  ``FunctionResponse`` re-sent on the next turn resumes the *same* A2A task.

The mock->real and local->GCP swap is therefore a **different Agent Card URL**,
not different agent code.

``RemoteA2aAgent`` is ``@a2a_experimental`` in ADK 2.7.0; see
``docs/decisions/adr-0009-native-a2a-consumer.md`` and ``docs/lessons-learned.md``
(C5) for the version-pin risk.
"""

import httpx
from google.adk.a2a.agent.config import A2aRemoteAgentConfig, RequestInterceptor
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

from contract import CollectRequest

from .wire import request_to_message

DEFAULT_CONSUMER_NAME = "document_bridge"


def build_collect_request_interceptor(
    collect_request: CollectRequest,
) -> RequestInterceptor:
    """Build a send-path interceptor that injects the structured ``CollectRequest``.

    Transfer/call-and-return through ``RemoteA2aAgent`` forwards the child
    session's *conversation content* (a text part), not the typed request. This
    interceptor **replaces** the outbound message parts with the canonical
    ``CollectRequest`` JSON DataPart (``wire.request_to_message``) so the Bridge
    receives the structured request on ``message/send``.

    The interceptor is a no-op on a **resume** request: those carry a truthy
    ``task_id`` (built by ``_create_a2a_request_for_user_function_response``) and
    must keep their resume ack, not be rewritten into a fresh ``CollectRequest``.
    This protects the S1-4 park/resume path.

    Note: ``a2a-sdk`` 1.x messages are protobuf — build/read with kwargs /
    ``.field`` (``task_id`` has no field presence, so a truthiness check is the
    right guard); never ``.model_dump()`` on A2A types.
    """

    async def _before_request(ctx, a2a_request, params):
        # Resume request (has a task_id): pass through unchanged.
        if a2a_request.task_id:
            return a2a_request, params
        # Fresh send: replace the parts with the structured CollectRequest.
        msg = request_to_message(collect_request)
        # Preserve an ongoing exchange's context id (empty on a first turn).
        if a2a_request.context_id:
            msg.context_id = a2a_request.context_id
        return msg, params

    return RequestInterceptor(before_request=_before_request)


def build_bridge_remote_agent(
    agent_card_url: str,
    *,
    name: str = DEFAULT_CONSUMER_NAME,
    use_legacy: bool = True,
    httpx_client: httpx.AsyncClient | None = None,
    collect_request: CollectRequest | None = None,
) -> RemoteA2aAgent:
    """Build a card-configured ``RemoteA2aAgent`` that consumes the Bridge.

    Args:
        agent_card_url: URL of the Bridge's Agent Card (e.g.
            ``http://127.0.0.1:8080/.well-known/agent-card.json``). This is the
            single swap point between mock/real and local/GCP.
        name: Unique agent name; also the ADK event author for relayed responses.
        use_legacy: Pin the A2A<->ADK integration mode. Held at ``True`` (the ADK
            default) until the new integration-extension path is validated
            (adr-0009); flipping it is a deliberate, recorded change.
        httpx_client: Optional shared client; the agent creates its own if omitted.
        collect_request: When provided, a send-path interceptor injects this
            structured ``CollectRequest`` as the outbound JSON DataPart (S1-2).
            When ``None`` the agent is built without a config — behavior is
            unchanged (used by S1-1's raw-contract coverage).

    Returns:
        A configured :class:`RemoteA2aAgent` usable as a root agent or a sub-agent.
    """
    config = None
    if collect_request is not None:
        config = A2aRemoteAgentConfig(
            request_interceptors=[
                build_collect_request_interceptor(collect_request)
            ]
        )

    return RemoteA2aAgent(
        name=name,
        agent_card=agent_card_url,
        httpx_client=httpx_client,
        use_legacy=use_legacy,
        config=config,
    )
