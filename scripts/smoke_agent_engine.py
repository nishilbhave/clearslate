"""Query a deployed Agent Engine agent: uv run python scripts/smoke_agent_engine.py <id-or-resource-name> [message]"""
import os
import sys

import vertexai
from dotenv import load_dotenv

load_dotenv()
project = os.environ["GOOGLE_CLOUD_PROJECT"]
location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
name = sys.argv[1]
message = sys.argv[2] if len(sys.argv) > 2 else "ping"
if not name.startswith("projects/"):
    name = f"projects/{project}/locations/{location}/reasoningEngines/{name}"
client = vertexai.Client(project=project, location=location)
agent = client.agent_engines.get(name=name)
for chunk in agent.stream_query(message=message, user_id="smoke"):
    print(chunk)
