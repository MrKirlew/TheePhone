from google.adk.agents import LlmAgent
# Multimodal usage: For Gemini, if using google-generativeai you may adapt.
# Here we conceptualize perception as another LlmAgent with instruction referencing image.
# The backend main will pass image content into session state as 'latest_image_bytes' or 'latest_image_desc'.

def build_perception_agent(model: str) -> LlmAgent:
    return LlmAgent(
        name="PerceptionAgent",
        model=model,
        instruction=(
            "You are a perceptive visual analyst. Given an image (already processed / described in state "
            "as 'image_context'), extract key objects, text (if any), and potential user-relevant insights. "
            "Be concise, natural, and friendly."
        ),
        input_schema=None,
        output_key="perception_summary",
    )