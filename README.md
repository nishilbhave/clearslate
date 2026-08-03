# ClearSlate

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
