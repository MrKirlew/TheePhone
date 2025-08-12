from google.adk.agents import LlmAgent

def build_perception_agent(model):
    return LlmAgent(
        name="PerceptionAgent",
        model=model,
        instruction="Analyze and describe what you perceive from the input.",
        input_schema=None,
        output_key="perception_summary"
    )