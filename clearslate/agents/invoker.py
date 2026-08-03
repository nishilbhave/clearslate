"""AgentInvoker protocol: a uniform async interface over local ADK Runner execution,
deployed Agent Engine endpoints, and offline test fakes (queued/fixture/recording).

Every implementation exposes `async def invoke(self, prompt: str) -> str`, returning the
agent's final response text (JSON, for schema-constrained agents like the breakdown agent).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import pathlib
from typing import Protocol

import vertexai
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


class AgentInvoker(Protocol):
    async def invoke(self, prompt: str) -> str: ...  # agent's final text (JSON expected)


class LocalAdkInvoker:
    """Runs an ADK agent in-process via Runner + InMemorySessionService.

    A fresh session is created per `invoke` call so successive prompts never share
    conversation state. Defaults to the breakdown agent's `root_agent`, imported lazily
    inside `__init__` (only when no agent is passed) so that importing this module never
    hard-requires constructing the breakdown ADK agent.
    """

    def __init__(self, agent=None, app_name: str = "clearslate", user_id: str = "clearslate"):
        if agent is None:
            from clearslate.agents.breakdown.agent import root_agent as agent  # lazy default

        self._app_name = app_name
        self._user_id = user_id
        self._session_service = InMemorySessionService()
        self._runner = Runner(agent=agent, app_name=app_name, session_service=self._session_service)

    async def invoke(self, prompt: str) -> str:
        session = await self._session_service.create_session(
            app_name=self._app_name, user_id=self._user_id
        )
        message = types.Content(role="user", parts=[types.Part(text=prompt)])
        final_text = ""
        async for event in self._runner.run_async(
            user_id=self._user_id, session_id=session.id, new_message=message
        ):
            if event.is_final_response() and event.content and event.content.parts:
                text = event.content.parts[0].text
                if text:
                    final_text = text
        return final_text


class AgentEngineInvoker:
    """Queries a deployed Agent Engine agent via `vertexai.Client().agent_engines.stream_query`.

    `engine_id` may be a bare numeric reasoning-engine id or a full resource name
    (`projects/{project}/locations/{location}/reasoningEngines/{id}`), mirroring
    `scripts/smoke_agent_engine.py`. The client/agent handle is resolved lazily on first
    `invoke` (not at construction) so building the object never makes a live GCP call.
    """

    def __init__(self, engine_id: str, project: str, location: str, user_id: str = "clearslate"):
        self._engine_id = engine_id
        self._project = project
        self._location = location
        self._user_id = user_id
        self._agent = None

    def _resolved_name(self) -> str:
        if self._engine_id.startswith("projects/"):
            return self._engine_id
        return f"projects/{self._project}/locations/{self._location}/reasoningEngines/{self._engine_id}"

    def _get_agent(self):
        if self._agent is None:
            client = vertexai.Client(project=self._project, location=self._location)
            self._agent = client.agent_engines.get(name=self._resolved_name())
        return self._agent

    def _invoke_sync(self, prompt: str) -> str:
        agent = self._get_agent()
        final_text = ""
        for chunk in agent.stream_query(message=prompt, user_id=self._user_id):
            content = chunk.get("content") if isinstance(chunk, dict) else None
            parts = content.get("parts") if isinstance(content, dict) else None
            if parts:
                text = parts[0].get("text")
                if text:
                    final_text = text
        return final_text

    async def invoke(self, prompt: str) -> str:
        return await asyncio.to_thread(self._invoke_sync, prompt)


class QueuedInvoker:
    """Test fake: returns canned `responses` in order and records every prompt received."""

    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.prompts: list[str] = []

    async def invoke(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self._responses:
            raise IndexError(
                f"QueuedInvoker exhausted: no response queued for call #{len(self.prompts)} "
                f"(prompt={prompt!r})"
            )
        return self._responses.pop(0)


def _prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


class FixtureInvoker:
    """Replays recorded responses from `<fixture_dir>/<sha256(prompt).hexdigest[:16]>.json`.

    Each fixture file stores `{"prompt_sha": ..., "response": ...}`, written by
    `RecordingInvoker`. Raises `KeyError` naming both the missing hash and the fixture
    directory when a prompt has no matching fixture.
    """

    def __init__(self, fixture_dir: pathlib.Path):
        self._fixture_dir = pathlib.Path(fixture_dir)

    async def invoke(self, prompt: str) -> str:
        prompt_hash = _prompt_hash(prompt)
        path = self._fixture_dir / f"{prompt_hash}.json"
        try:
            raw = path.read_text()
        except FileNotFoundError:
            raise KeyError(
                f"No fixture for prompt hash {prompt_hash!r} in {self._fixture_dir}"
            ) from None
        return json.loads(raw)["response"]


class RecordingInvoker:
    """Wraps a real `inner` invoker; after each call, writes the response to
    `<fixture_dir>/<sha256(prompt).hexdigest[:16]>.json` for later `FixtureInvoker` replay.
    """

    def __init__(self, inner: AgentInvoker, fixture_dir: pathlib.Path):
        self._inner = inner
        self._fixture_dir = pathlib.Path(fixture_dir)

    async def invoke(self, prompt: str) -> str:
        response = await self._inner.invoke(prompt)
        self._fixture_dir.mkdir(parents=True, exist_ok=True)
        prompt_hash = _prompt_hash(prompt)
        path = self._fixture_dir / f"{prompt_hash}.json"
        path.write_text(json.dumps({"prompt_sha": prompt_hash, "response": response}))
        return response
