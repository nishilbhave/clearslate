# ClearSlate

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

Upload a screenplay, get a cited E&O-style clearance report in minutes.

## The problem

Entertainment & Errors (E&O) insurance requires script clearance research before production—verifying that character names, locations, and plot elements don't infringe on existing works or public figures. Incumbents charge $10–15 per page with days-to-weeks turnaround. The process is manual, slow, and inaccessible to independent producers.

## What ClearSlate does

ClearSlate automates script clearance. Upload a screenplay. Get back an itemized, page-referenced, citation-backed clearance report in minutes. Each flagged item links to the research that triggered it—sources, dates, and confidence scores included.

## Architecture

- **Web + Worker**: Cloud Run services (async task queue via Firestore)
- **ADK Agents on Vertex AI Agent Engine**: Breakdown, research, and synthesis agents
- **Vertex AI Search**: "Rulebook" data store for industry guidelines
- **Parallel Search + Task APIs**: Cited web research with real-time sources
- **Firestore / GCS / Secret Manager**: State, report storage, credentials

## Local setup

1. Install: `uv sync`
2. Configure: Copy `.env.example` to `.env` and fill in `PARALLEL_API_KEY`
3. Run: `uv run uvicorn clearslate.api.app:app --port 8000`

## Agent runtime modes

`CLEARSLATE_AGENT_RUNTIME` selects how agents run, defaulting to `local`:

- `local` — agents execute in-process via ADK's `Runner` + `InMemorySessionService` (`LocalAdkInvoker`). No deploy needed; this is the default for development.
- `engine` — agents run on a deployed Vertex AI Agent Engine instance, queried over `vertexai.Client().agent_engines` (`AgentEngineInvoker`). Requires `CLEARSLATE_BREAKDOWN_ENGINE_ID` (set after `adk deploy agent_engine ... clearslate/agents/breakdown`) plus `GOOGLE_CLOUD_PROJECT`/`GOOGLE_CLOUD_LOCATION` in `.env`.

Both modes speak the same `AgentInvoker` protocol, so the API/worker code is identical either way — only the env vars change.

## GCP bootstrap

After Task 0.1 (see `.superpowers/sdd/2026-08-02-clearslate-hackathon-spec.md`):

```bash
PROJECT_ID=your-gcp-project-id \
BILLING_ACCOUNT_ID=your-billing-account-id \
scripts/bootstrap_gcp.sh
```

## Disclaimer

ClearSlate produces a research report, not legal advice or a legal opinion.

---

Licensed under [Apache License 2.0](LICENSE).
