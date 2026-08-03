from google.adk.agents import LlmAgent

root_agent = LlmAgent(
    name="hello_agent",
    model="gemini-2.5-flash",
    description="Deployment smoke-test agent for ClearSlate.",
    instruction="Reply with exactly this sentence and nothing else: ClearSlate Agent Engine is alive.",
)
