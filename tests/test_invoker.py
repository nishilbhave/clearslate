"""Offline tests for clearslate.agents.invoker.

LocalAdkInvoker / AgentEngineInvoker are only exercised through import + construction
here (no live GCP/model calls). Their `invoke()` behavior is covered by Task 1.12's
gated live test.
"""
import hashlib

import pytest

from clearslate.agents.invoker import (
    AgentEngineInvoker,
    FixtureInvoker,
    LocalAdkInvoker,
    QueuedInvoker,
    RecordingInvoker,
)


async def test_queued_invoker_pops_in_order_and_records_prompts():
    invoker = QueuedInvoker(["first", "second"])

    assert await invoker.invoke("prompt-a") == "first"
    assert await invoker.invoke("prompt-b") == "second"
    assert invoker.prompts == ["prompt-a", "prompt-b"]


async def test_queued_invoker_raises_indexerror_when_exhausted():
    invoker = QueuedInvoker(["only"])

    await invoker.invoke("p1")
    with pytest.raises(IndexError, match="exhausted"):
        await invoker.invoke("p2")

    # the prompt that triggered the error is still recorded
    assert invoker.prompts == ["p1", "p2"]


async def test_recording_invoker_writes_fixtures_replayed_byte_identically(tmp_path):
    inner = QueuedInvoker(["response-one", "response-two"])
    recorder = RecordingInvoker(inner, tmp_path)

    response_a = await recorder.invoke("hello")
    response_b = await recorder.invoke("world")

    fixture_files = sorted(tmp_path.glob("*.json"))
    assert len(fixture_files) == 2

    replay = FixtureInvoker(tmp_path)
    assert await replay.invoke("hello") == response_a == "response-one"
    assert await replay.invoke("world") == response_b == "response-two"


async def test_recording_invoker_creates_missing_fixture_dir(tmp_path):
    fixture_dir = tmp_path / "nested" / "fixtures"
    recorder = RecordingInvoker(QueuedInvoker(["ok"]), fixture_dir)

    await recorder.invoke("hi")

    assert fixture_dir.is_dir()
    assert len(list(fixture_dir.glob("*.json"))) == 1


async def test_fixture_invoker_raises_keyerror_naming_hash_and_dir(tmp_path):
    replay = FixtureInvoker(tmp_path)
    expected_hash = hashlib.sha256(b"never recorded").hexdigest()[:16]

    with pytest.raises(KeyError) as exc_info:
        await replay.invoke("never recorded")

    message = str(exc_info.value)
    assert expected_hash in message
    assert str(tmp_path) in message


def test_local_adk_invoker_construction_imports_default_agent_without_live_call():
    invoker = LocalAdkInvoker()

    assert isinstance(invoker, LocalAdkInvoker)
    assert invoker._runner is not None


def test_agent_engine_invoker_construction_does_not_resolve_agent():
    invoker = AgentEngineInvoker(engine_id="12345", project="proj", location="us-central1")

    assert invoker._engine_id == "12345"
    assert invoker._project == "proj"
    assert invoker._location == "us-central1"
    # lazy: no live GCP call happened at construction time
    assert invoker._agent is None
