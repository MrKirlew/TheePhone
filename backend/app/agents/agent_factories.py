from google.adk.agents import LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from typing import Dict, Any


def build_intent_agent(model_name: str) -> LlmAgent:
    """Builds a lightweight intent classification agent."""
    return LlmAgent(
        name="IntentAgent",
        model=model_name,
        instruction="""
        Classify the intent of the user query. Choose from:

        1. general_conversation - for casual talk, greetings, or non-specific queries
        2. question_answering - for factual questions seeking information
        3. task_completion - for requests to do something (set reminder, send email)
        4. perception_request - when user wants analysis of an image
        5. memory_recall - when user references past personal context
        6. document_search - when user asks about specific documents/information
        7. workspace_request - when user asks about Google Workspace tools (Docs, Sheets, Drive, Gmail, Calendar, Contacts)

        Output should be ONLY a JSON with single "intent" key, e.g.:
        {"intent": "general_conversation"}
        """,
        input_schema=None,
        output_key="intent_result"
    )


def build_planning_agent(model_name: str) -> LlmAgent:
    """Builds a planning agent that creates a step-by-step plan."""
    return LlmAgent(
        name="PlanningAgent",
        model=model_name,
        instruction="""
        Based on the intent and user query, create a step-by-step execution plan.
        Available actions:
        - perception: Use when images need analysis
        - memory_summarize: Use when memory context is available
        - workspace_tools: Use when Google Workspace tools are needed (Docs, Sheets, Drive, Gmail, Calendar, Contacts)
        - call_tool: Use when a tool/API is needed
        - retrieve_docs: Use when document search is needed
        - compose_response: Always include this as final step
        - reflect: Include if complex reasoning is needed

        Your plan should be in strict JSON format with no markdown:
        {
          "plan": [
            {"step": 1, "action": "perception/memory_summarize/workspace_tools/call_tool/retrieve_docs/compose_response/reflect"},
            {"step": 2, "action": "..."}
          ]
        }

        Example for a query about Google Docs:
        {
          "plan": [
            {"step": 1, "action": "workspace_tools"},
            {"step": 2, "action": "compose_response"}
          ]
        }
        """,
        input_schema=None,
        output_key="plan_json"
    )


def build_reflection_agent(model_name: str) -> LlmAgent:
    """Builds a reflection agent for quality checking."""
    return LlmAgent(
        name="ReflectionAgent",
        model=model_name,
        instruction="""
        Review the response quality for appropriateness, safety, coherence.

        Check for:
        - Did response fully address the intent?
        - Is tone appropriate and non-repetitive?
        - Are there any safety concerns?
        - Should we ask followup (flag as "needs_followup")?

        Output your analysis in a concise JSON with NO markdown:
        {
          "quality": "good/fair/poor",
          "issues": "specific concerns or 'none'",
          "needs_followup": true/false,
          "suggestion": "improvement suggestions"
        }
        """,
        input_schema=None,
        output_key="reflection_result"
    )
