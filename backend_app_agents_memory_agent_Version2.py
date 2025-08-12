from google.adk.agents import LlmAgent

def build_memory_agent(model: str) -> LlmAgent:
    return LlmAgent(
        name="MemoryAgent",
        model=model,
        instruction=(
            "You maintain and recall user personal context and preferences. "
            "When given a user query and retrieved memory snippets (state key 'retrieved_memory'), "
            "summarize relevant memory to aid the conversation. Output only a concise synthesized context."
        ),
        input_schema=None,
        output_key="memory_context",
    )