from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    project: str = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    location: str = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    breakdown_model: str = os.environ.get("CLEARSLATE_BREAKDOWN_MODEL", "gemini-3.6-flash")
    agent_runtime: str = os.environ.get("CLEARSLATE_AGENT_RUNTIME", "local")  # local | engine
    breakdown_engine_id: str = os.environ.get("CLEARSLATE_BREAKDOWN_ENGINE_ID", "")
    max_pages: int = 180
    chunk_pages: int = 12
    chunk_overlap: int = 2
    max_researched_elements: int = 250   # spec cost guard, enforced Phase 2
    max_task_runs: int = 40              # spec cost guard, enforced Phase 2

settings = Settings()
