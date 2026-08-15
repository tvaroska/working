"""The native ``RemoteA2aAgent`` Bridge consumer (adr-0009).

From Sprint 1 the demos consume the Bridge through ADK's platform-native
``RemoteA2aAgent`` rather than the M0 hand-rolled :class:`~bridge_client.port.BridgeClient`
poll loop (which is kept only as a tracer-bullet double). The native construct
gives us the two long-running mechanisms for free:

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
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

DEFAULT_CONSUMER_NAME = "document_bridge"


def build_bridge_remote_agent(
    agent_card_url: str,
    *,
    name: str = DEFAULT_CONSUMER_NAME,
    use_legacy: bool = True,
    httpx_client: httpx.AsyncClient | None = None,
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

    Returns:
        A configured :class:`RemoteA2aAgent` usable as a root agent or a sub-agent.
    """
    return RemoteA2aAgent(
        name=name,
        agent_card=agent_card_url,
        httpx_client=httpx_client,
        use_legacy=use_legacy,
    )
