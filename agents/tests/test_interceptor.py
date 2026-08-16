"""Send-path ``RequestInterceptor`` unit tests (hermetic — no sockets, no ADK Runner).

The interceptor (``bridge_client.build_collect_request_interceptor``) is the surviving
piece that injects the structured ``CollectRequest`` DataPart on a fresh send and
threads the durable exchange ``context_id`` across the Collect loop's rounds. It is
used by the collect node of the durable ``Workflow`` graph (ADR-0010); these tests
were carried over from the retired ``AgentTool`` wiring's suites (S1-2 / S1-4), which
first locked this contract.
"""

import asyncio
from types import SimpleNamespace

from a2a.helpers.proto_helpers import (
    get_data_parts,
    get_message_text,
    new_text_message,
)

from agents.address.config import PARTY, SKILL
from bridge_client import EXCHANGE_CONTEXT_STATE_KEY, build_collect_request_interceptor
from contract import CollectRequest

EXPECTED_DATA = CollectRequest(party=PARTY, skill=SKILL).model_dump(mode="json")


def _fake_ctx(state: dict) -> SimpleNamespace:
    """A minimal ctx exposing ``ctx.session.state`` (the only field read here)."""
    return SimpleNamespace(session=SimpleNamespace(state=state))


def test_interceptor_injects_collect_request_datapart():
    """A fresh send (no task_id) is rewritten to the CollectRequest DataPart."""
    interceptor = build_collect_request_interceptor(CollectRequest(party=PARTY, skill=SKILL))
    fresh = new_text_message("whatever the model happened to say")

    sentinel = object()
    msg, params = asyncio.run(interceptor.before_request(None, fresh, sentinel))

    assert params is sentinel  # params passed through untouched
    datas = get_data_parts(msg.parts)
    assert len(datas) == 1, "expected exactly one JSON DataPart"
    assert datas[0] == EXPECTED_DATA


def test_interceptor_threads_context_from_state():
    """A fresh send stamps the exchange context id threaded through session state."""
    interceptor = build_collect_request_interceptor(CollectRequest(party=PARTY, skill=SKILL))
    ctx = _fake_ctx({EXCHANGE_CONTEXT_STATE_KEY: "ctx-abc"})
    fresh = new_text_message("whatever the model happened to say")

    msg, _ = asyncio.run(interceptor.before_request(ctx, fresh, None))

    assert msg.context_id == "ctx-abc"
    datas = get_data_parts(msg.parts)
    assert len(datas) == 1
    assert datas[0] == EXPECTED_DATA


def test_interceptor_no_state_leaves_context_empty():
    """No threaded state -> fresh send falls back to an empty context id."""
    interceptor = build_collect_request_interceptor(CollectRequest(party=PARTY, skill=SKILL))
    ctx = _fake_ctx({})
    fresh = new_text_message("kickoff")

    msg, _ = asyncio.run(interceptor.before_request(ctx, fresh, None))

    assert not msg.context_id  # empty / unset -> a fresh exchange
    assert get_data_parts(msg.parts)[0] == EXPECTED_DATA


def test_interceptor_passthrough_on_resume():
    """A resume request the SDK recognises (task_id set) is passed through unchanged."""
    interceptor = build_collect_request_interceptor(CollectRequest(party=PARTY, skill=SKILL))
    resume = new_text_message(
        "Here is the requested proof.",
        task_id="task-123",
        context_id="ctx-1",
    )

    msg, _ = asyncio.run(interceptor.before_request(None, resume, None))

    assert msg is resume, "resume request must not be rewritten"
    assert get_message_text(msg) == "Here is the requested proof."
    assert not get_data_parts(msg.parts), "resume must carry no CollectRequest"


def test_interceptor_passthrough_on_resume_with_state():
    """A resume request is passed through even when exchange context state is present."""
    interceptor = build_collect_request_interceptor(CollectRequest(party=PARTY, skill=SKILL))
    ctx = _fake_ctx({EXCHANGE_CONTEXT_STATE_KEY: "ctx-abc"})
    resume = new_text_message(
        "Here is the requested proof.", task_id="task-123", context_id="ctx-1"
    )

    msg, _ = asyncio.run(interceptor.before_request(ctx, resume, None))

    assert msg is resume  # not rewritten
    assert not get_data_parts(msg.parts)  # no CollectRequest injected
