from google.adk.agents import LlmAgent

def build_memory_agent(model):
    return LlmAgent(
        name="MemoryAgent",
        model=model,
        instruction="Manage and retrieve relevant memories from the conversation context.",
        input_schema=None,
        output_key="memory_context"
    )