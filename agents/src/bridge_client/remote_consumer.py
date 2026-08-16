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
from google.adk.agents.remote_a2a_agent import A2A_METADATA_PREFIX, RemoteA2aAgent

from contract import CollectRequest

from .wire import request_to_message

DEFAULT_CONSUMER_NAME = "document_bridge"

EXCHANGE_CONTEXT_STATE_KEY = "bridge_exchange_context_id"
"""Session-state key under which the durable A2A exchange ``context_id`` is threaded.

Bridge-owned (``bridge_client`` imports nothing from ``agents.*``). In the durable
``Workflow`` graph the gate node writes the collected turn's ``context_id`` here after
each round; the send-path interceptor below reads it to keep the whole Collect loop on
one exchange rather than opening a fresh one per round.
"""

_A2A_TASK_ID_META = A2A_METADATA_PREFIX + "task_id"
_A2A_CONTEXT_ID_META = A2A_METADATA_PREFIX + "context_id"


def _pending_resume_target(events, consumer_name: str) -> tuple[str, str | None] | None:
    """Detect a pending park/resume and return the parked ``(task_id, context_id)``.

    ``RemoteA2aAgent`` detects a resume with ``ctx.session.events[-1].author ==
    "user"`` (``_create_a2a_request_for_user_function_response``): the resolved
    ``FunctionResponse`` must be the *last* session event. That holds in a plain
    agent / ``LoopAgent`` run, but **not inside a ``Workflow``** — the graph
    orchestrator appends a workflow-start event (author = the graph name) after
    the user ``FunctionResponse`` and before the collect node re-runs, so the
    remote agent never sets the parked ``task_id`` and re-sends a *fresh*
    ``CollectRequest`` (the peer opens a new task and parks again). This helper is
    the Workflow-ordering-independent equivalent (docs/lessons-learned A12).

    A resume is pending when the most-recent user ``FunctionResponse`` has **no
    event authored by the collect node after it** — i.e. the collect node has not
    run since the resolved response was appended (the intervening events are the
    workflow's own orchestration events, not the consumer's). Once the resumed
    send completes, the collect node emits its own (``consumer_name``-authored)
    response events, so on any later fresh round the guard sees a consumer event
    after the response and correctly does *not* re-fire. The parked identifiers
    come from the matching function-call event's ``custom_metadata`` — the same
    ``a2a:task_id`` / ``a2a:context_id`` the SDK reads on the happy path.

    Returns ``(task_id, context_id)`` for the pending resume, or ``None``.
    """
    events = list(events)
    # Most-recent user FunctionResponse and its position.
    fr_index = None
    fr_id = None
    for i in range(len(events) - 1, -1, -1):
        responses = events[i].get_function_responses()
        if responses:
            fr_index = i
            fr_id = responses[0].id
            break
    if fr_index is None or fr_id is None:
        return None

    # Guard against double-fire: if the collect node already ran since that
    # response (emitted its own event), this is a later fresh round, not a resume.
    for later in events[fr_index + 1 :]:
        if later.author == consumer_name:
            return None

    # Find the parked function-call event carrying the peer's A2A task id.
    for event in reversed(events[:fr_index]):
        if any(fc.id == fr_id for fc in event.get_function_calls()):
            metadata = event.custom_metadata or {}
            task_id = metadata.get(_A2A_TASK_ID_META)
            if isinstance(task_id, str) and task_id:
                context_id = metadata.get(_A2A_CONTEXT_ID_META)
                return task_id, context_id if isinstance(context_id, str) else None
            return None
    return None


def build_collect_request_interceptor(
    collect_request: CollectRequest,
    *,
    context_state_key: str = EXCHANGE_CONTEXT_STATE_KEY,
    consumer_name: str = DEFAULT_CONSUMER_NAME,
) -> RequestInterceptor:
    """Build a send-path interceptor that injects the structured ``CollectRequest``.

    Transfer/call-and-return through ``RemoteA2aAgent`` forwards the child
    session's *conversation content* (a text part), not the typed request. This
    interceptor **replaces** the outbound message parts with the canonical
    ``CollectRequest`` JSON DataPart (``wire.request_to_message``) so the Bridge
    receives the structured request on ``message/send``.

    Durable exchange context: the multi-turn Collect loop threads the exchange
    ``context_id`` through **session state** (the gate writes it under
    ``context_state_key`` after each round).
    On a fresh send this interceptor stamps the threaded context id on the outbound
    ``message/send`` so every round continues the **same** A2A exchange — no fresh
    context per round. Precedence: threaded state > the request's own context id.

    Park/resume inside a ``Workflow`` (S1-6): ``RemoteA2aAgent`` builds its own
    resume request (truthy ``task_id``) only when the resolved ``FunctionResponse``
    is the *last* session event — which the graph orchestrator breaks by appending
    a workflow event after it (see :func:`_pending_resume_target`). So this
    interceptor also detects the pending resume itself and stamps the parked
    ``task_id`` / ``context_id`` on the outbound message instead of rewriting it
    into a fresh ``CollectRequest``; that keeps the resume on the **same** A2A task
    rather than opening (and re-parking) a new one. A request that already carries
    a ``task_id`` (the SDK did detect the resume) is passed through unchanged.

    Note: ``a2a-sdk`` 1.x messages are protobuf — build/read with kwargs /
    ``.field`` (``task_id`` has no field presence, so a truthiness check is the
    right guard); never ``.model_dump()`` on A2A types.
    """

    async def _before_request(ctx, a2a_request, params):
        # Resume request the SDK already recognised (truthy task_id): pass through.
        if a2a_request.task_id:
            return a2a_request, params

        # Resume the SDK missed under Workflow event ordering: stamp the parked
        # task/context onto this message so the peer resumes the same A2A task.
        # ``events`` is absent in hermetic interceptor unit tests (ctx may be None).
        events = getattr(ctx.session, "events", None) if ctx and ctx.session else None
        if events:
            resume = _pending_resume_target(events, consumer_name)
            if resume is not None:
                task_id, context_id = resume
                a2a_request.task_id = task_id
                if context_id:
                    a2a_request.context_id = context_id
                return a2a_request, params

        # Fresh send: replace the parts with the structured CollectRequest.
        msg = request_to_message(collect_request)
        # Thread the exchange context from session state (the only cross-round
        # channel) so the loop stays on one exchange; fall back to the request's
        # own context id (empty on a first turn). ``ctx`` may be None in hermetic
        # interceptor unit tests.
        threaded = ctx.session.state.get(context_state_key) if ctx and ctx.session else None
        context_id = threaded or a2a_request.context_id
        if context_id:
            # a2a-sdk proto string field: assign only a non-empty value (setting
            # it to None raises); leaving it unset == a fresh exchange.
            msg.context_id = context_id
        return msg, params

    return RequestInterceptor(before_request=_before_request)


def build_bridge_remote_agent(
    agent_card_url: str,
    *,
    name: str = DEFAULT_CONSUMER_NAME,
    use_legacy: bool = True,
    httpx_client: httpx.AsyncClient | None = None,
    collect_request: CollectRequest | None = None,
    context_state_key: str = EXCHANGE_CONTEXT_STATE_KEY,
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
            structured ``CollectRequest`` as the outbound JSON DataPart (S1-2) and
            threads the durable exchange context across rounds (S1-4). When ``None``
            the agent is built without a config — behavior is unchanged (used by
            S1-1's raw-contract coverage).
        context_state_key: Session-state key the interceptor reads to thread the
            A2A exchange ``context_id`` across the Collect loop's rounds (S1-4).

    Returns:
        A configured :class:`RemoteA2aAgent` usable as a root agent or a sub-agent.
    """
    config = None
    if collect_request is not None:
        config = A2aRemoteAgentConfig(
            request_interceptors=[
                build_collect_request_interceptor(
                    collect_request,
                    context_state_key=context_state_key,
                    consumer_name=name,
                )
            ]
        )

    return RemoteA2aAgent(
        name=name,
        agent_card=agent_card_url,
        httpx_client=httpx_client,
        use_legacy=use_legacy,
        config=config,
    )
